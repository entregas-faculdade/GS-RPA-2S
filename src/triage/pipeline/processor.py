"""Processamento de um pedido: da anonimização à resposta ou à fila de revisão.

Com `llm.enabled`, o cliente e o localizador, o texto anonimizado e as fontes aprovadas do catálogo vão ao LLM,
que redige a resposta; sem LLM (o padrão) ou em qualquer falha dele, responde o fluxo determinístico por template.

Numa conversa de chat, as mensagens anteriores (anonimizadas) entram só na recuperação das fontes e na mensagem ao LLM;
a classificação e a decisão de revisão seguem sobre a mensagem atual.
"""

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from sklearn.pipeline import Pipeline

from triage.agent import AgentError, load_agent
from triage.automation.catalog import ServiceEntry
from triage.automation.finder import ServiceFinder
from triage.automation.llm_client import LlmClient, build_llm_client
from triage.automation.messages import (
    build_emergency_message,
    build_no_information_message,
)
from triage.automation.rag import RagResult, answer_with_sources
from triage.automation.resolver import (
    REASON_LINK_UNAVAILABLE,
    CatalogLookup,
    build_default_lookup,
    resolve_service,
)
from triage.automation.response import Response, build_llm_response, build_response
from triage.automation.topics import (
    NO_TOPIC,
    OTHER_TOPIC,
    TopicChoice,
    TopicRequest,
    TopicsError,
    choose_topic,
)
from triage.classification import (
    ModelNotAvailableError,
    ReviewReason,
    classify,
    is_urgent,
    triage_decision,
)
from triage.classification.decision import ACTION_AUTO_ANSWER, Decision
from triage.classification.model import DEFAULT_MODEL_PATH
from triage.classification.model import load as load_model
from triage.common.retry import RetryPolicy, retry_with_backoff
from triage.config import Settings
from triage.ingestion import Rejection, Request
from triage.privacy import anonymize
from triage.storage import (
    InteractionRecord,
    Repository,
    RequestRecord,
    StorageError,
    request_hash,
)
from triage.storage.schema import (
    STATUS_ANSWERED,
    STATUS_QUEUED_FOR_REVIEW,
    STATUS_REJECTED,
)

STATUS_SKIPPED_DUPLICATE = "skipped_duplicate"
STATUS_ERROR = "error"
LINK_OK = "ok"
LINK_UNAVAILABLE = "unavailable"
TIER_CATALOG = "catalog"
TIER_FINDER = "finder"
DEFAULT_MAX_CANDIDATES = 5
SAFE_REVIEW_REASON = ReviewReason.LOW_CONFIDENCE.value
FINDER_REASONS = frozenset({ReviewReason.OUT_OF_CATALOG, ReviewReason.LOW_CONFIDENCE})
REJECTED_TEXT_TEMPLATE = "[pedido rejeitado na ingestão: {reason}]"
STORAGE_RETRY_POLICY = RetryPolicy(attempts=3, base_delay=0.5, max_delay=2.0, transient=(StorageError,))

logger = logging.getLogger("triage.pipeline")


@dataclass(frozen=True)
class ProcessingResult:
    """Desfecho de um pedido; nunca carrega o texto do cidadão, só o que a resposta e o relatório precisam."""

    status: str
    category: str | None = None
    confidence: float | None = None
    reason: str | None = None
    response_text: str | None = None
    link_status: str | None = None
    used_llm: bool = False
    fallback_reason: str | None = None
    tier: str | None = None
    topic: str | None = None
    topic_source: str | None = None
    needs_human: bool = False
    service: ServiceEntry | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class Conversation:
    """Conversa do chat: o identificador, o número da mensagem atual nela e as mensagens anteriores do cidadão.

    O número vem de quem mantém a conversa e conta todas as mensagens, não só as de `messages` (que é um recorte);
    com o identificador, é o que distingue a mesma pergunta repetida. Em `process_request`, `messages` já vem anonimizado.
    """

    id: str
    turn: int
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Turn:
    """A mensagem atual (anonimizada) e as anteriores da conversa, já anonimizadas."""

    text: str
    history: tuple[str, ...] = ()

    @property
    def search_text(self) -> str:
        """Texto de recuperação das fontes: a mensagem atual primeiro, depois as anteriores."""
        return "\n".join((self.text, *self.history))


@dataclass(frozen=True)
class Deps:
    """Dependências do pipeline, montadas uma vez por execução (o modelo e o catálogo não recarregam por pedido)."""

    repository: Repository
    lookup: CatalogLookup
    settings: Settings
    model: Pipeline | None = None
    llm_client: LlmClient | None = None
    retry_policy: RetryPolicy = STORAGE_RETRY_POLICY
    sleep: Callable[[float], None] = time.sleep
    finder: ServiceFinder | None = None
    max_candidates: int = DEFAULT_MAX_CANDIDATES


def _load_model_or_none() -> Pipeline | None:
    try:
        return load_model(DEFAULT_MODEL_PATH)
    except ModelNotAvailableError as error:
        logger.warning("Modelo indisponível (%s); todos os pedidos irão à revisão humana", type(error).__name__)
        return None


def _max_candidates(settings: Settings, client: LlmClient | None) -> int:
    """Quantas fontes o LLM recebe: vem do `config.json` do agente (só lido com o LLM montado)."""
    if client is None:
        return DEFAULT_MAX_CANDIDATES
    try:
        return load_agent(settings.llm_agent_id).params.max_candidates
    except AgentError as error:
        logger.warning("Agente sem max_candidates utilizável (%s); usando %d", type(error).__name__, DEFAULT_MAX_CANDIDATES)
        return DEFAULT_MAX_CANDIDATES


def build_deps(settings: Settings, db_path: str | Path) -> Deps:
    """Monta as dependências de uma execução: banco, catálogo, modelo (ausente vira `None`) e LLM opcional.

    Banco inacessível levanta `StorageError`; o chamador decide (no `run.py`, código de saída 1).
    """
    lookup = build_default_lookup()
    llm_client = build_llm_client(settings)
    return Deps(
        repository=Repository(db_path),
        lookup=lookup,
        settings=settings,
        model=_load_model_or_none(),
        llm_client=llm_client,
        finder=ServiceFinder(lookup.approved_entries(), settings),
        max_candidates=_max_candidates(settings, llm_client),
    )


def _review(
    category: str | None, confidence: float | None, reason: str | None, link_status: str | None = None
) -> ProcessingResult:
    return ProcessingResult(STATUS_QUEUED_FOR_REVIEW, category, confidence, reason, link_status=link_status)


def _answered(decision: Decision, response: Response, tier: str, service: ServiceEntry | None) -> ProcessingResult:
    return ProcessingResult(
        STATUS_ANSWERED,
        decision.category,
        decision.confidence,
        None,
        response.text,
        LINK_OK,
        response.used_llm,
        response.fallback_reason,
        tier,
        service=service,
    )


def _failed_resolution(decision: Decision, reason: str | None) -> ProcessingResult:
    link_status = LINK_UNAVAILABLE if reason == REASON_LINK_UNAVAILABLE else None
    return _review(decision.category, decision.confidence, reason, link_status)


def _llm_ready(deps: Deps) -> bool:
    """O LLM só é chamado com `llm.enabled`, cliente montado e localizador (que fornece as fontes)."""
    return deps.settings.llm_enabled and deps.llm_client is not None and deps.finder is not None


def _live_entries(entries: Sequence[ServiceEntry], deps: Deps) -> tuple[ServiceEntry, ...]:
    """As entradas com link vivo (ou só telefone), já sem os links mortos; as demais não vão ao LLM."""
    resolved = (deps.lookup.resolve_entry(entry).service for entry in entries)
    return tuple(service for service in resolved if service is not None)


def _catalog_sources(service: ServiceEntry, turn: _Turn, deps: Deps) -> tuple[ServiceEntry, ...]:
    """Degrau 1: o serviço resolvido e, depois dele, até `max_candidates - 1` candidatas do localizador (sem repetir)."""
    candidates = deps.finder.top_candidates(turn.search_text, deps.max_candidates)
    others = [entry for entry in candidates if entry.id != service.id][: deps.max_candidates - 1]
    return (service, *_live_entries(others, deps))


def _catalog_response(service: ServiceEntry, turn: _Turn, deps: Deps) -> Response:
    """Degrau 1: o LLM redige sobre as fontes; qualquer falha ou "nenhuma fonte" deixa o template do serviço responder."""
    if not _llm_ready(deps):
        return build_response(service)
    rag = answer_with_sources(deps.llm_client, turn.text, _catalog_sources(service, turn, deps), turn.history)
    if rag.text is not None:
        return build_llm_response(rag.text)
    return build_response(service, rag.fallback_reason)


def _answer_or_review(turn: _Turn, decision: Decision, deps: Deps) -> ProcessingResult:
    """Degrau 1: resolve o serviço da categoria e responde; sem serviço utilizável, revisão com a causa."""
    resolution = resolve_service(decision.category, deps.lookup)
    if resolution.service is None:
        return _failed_resolution(decision, resolution.reason)
    return _answered(decision, _catalog_response(resolution.service, turn, deps), TIER_CATALOG, resolution.service)


def _gap_rag(turn: _Turn, deps: Deps) -> RagResult:
    """Degraus 2 e 3: o LLM redige sobre as candidatas vivas; sem nenhuma, não é chamado e o fluxo determinístico decide."""
    sources = _live_entries(deps.finder.top_candidates(turn.search_text, deps.max_candidates), deps)
    if not sources:
        return RagResult()
    return answer_with_sources(deps.llm_client, turn.text, sources, turn.history)


def _no_information(decision: Decision) -> ProcessingResult:
    review = _review(decision.category, decision.confidence, decision.reason.value)
    return replace(review, response_text=build_no_information_message())


def _deterministic_find(turn: _Turn, decision: Decision, deps: Deps) -> ProcessingResult:
    """Localizador com limiar: fonte achada responde por template (degrau 2); sem fonte, "não tenho a informação"."""
    match = deps.finder.find(turn.search_text) if deps.finder is not None else None
    if match is None:
        return _no_information(decision)
    resolution = deps.lookup.resolve_entry(match.entry)
    if resolution.service is None:
        return _failed_resolution(decision, resolution.reason)
    return _answered(decision, build_response(resolution.service), TIER_FINDER, resolution.service)


def _find_or_review(turn: _Turn, decision: Decision, deps: Deps) -> ProcessingResult:
    """Degraus 2 e 3: com LLM, ele redige sobre as candidatas; sem LLM ou em falha, decide o localizador determinístico."""
    rag = _gap_rag(turn, deps) if _llm_ready(deps) else RagResult()
    if rag.text is not None:
        return _answered(decision, build_llm_response(rag.text), TIER_FINDER, None)
    if rag.no_source:
        return _no_information(decision)
    return replace(_deterministic_find(turn, decision, deps), fallback_reason=rag.fallback_reason)


def _urgent_review(decision: Decision, deps: Deps) -> ProcessingResult:
    """Urgência: revisão com os telefones de emergência aprovados; sem localizador nem resolução."""
    review = _review(decision.category, decision.confidence, decision.reason.value)
    return replace(review, response_text=build_emergency_message(deps.lookup.approved_entries()))


def _triage(turn: _Turn, deps: Deps) -> ProcessingResult:
    """Classifica e decide só pela mensagem atual; a conversa anterior só serve à recuperação e ao LLM."""
    if deps.model is None:
        return _review(None, 0.0, SAFE_REVIEW_REASON)
    decision = triage_decision(turn.text, classify(turn.text, deps.model), deps.settings)
    if decision.action == ACTION_AUTO_ANSWER:
        return _answer_or_review(turn, decision, deps)
    if decision.reason is ReviewReason.URGENT:
        return _urgent_review(decision, deps)
    if decision.reason in FINDER_REASONS:
        return _find_or_review(turn, decision, deps)
    return _review(decision.category, decision.confidence, decision.reason.value)


def _requires_human(status: str) -> bool:
    """A tag `needs_human` e a fila de revisão saem desta mesma regra: o pedido não foi respondido."""
    return status != STATUS_ANSWERED


def _store(record: RequestRecord, deps: Deps) -> None:
    """Grava o pedido e, se ele não foi respondido, enfileira a revisão. Repetível: gravar o mesmo hash é ignorado."""
    deps.repository.save_request(record, anonymized=True)
    if _requires_human(record.status):
        deps.repository.enqueue_review(record.request_hash, record.review_reason)


def _persist(record: RequestRecord, deps: Deps) -> None:
    retry_with_backoff(lambda: _store(record, deps), deps.retry_policy, deps.sleep)


def _persist_interaction(interaction: InteractionRecord, deps: Deps) -> None:
    """Cataloga a interação com o mesmo retry; falha persistente é logada e não desfaz o pedido nem a fila."""
    try:
        retry_with_backoff(lambda: deps.repository.save_interaction(interaction), deps.retry_policy, deps.sleep)
    except StorageError as error:
        logger.error("Interação não catalogada (%s); o pedido segue gravado", type(error).__name__)


def _topic_client(deps: Deps) -> LlmClient | None:
    """O LLM escolhe a categoria só com `llm.enabled` e cliente montado; senão decidem as regras."""
    return deps.llm_client if deps.settings.llm_enabled else None


def _choose_topic(request: TopicRequest, client: LlmClient | None) -> TopicChoice:
    """Categoria da interação; vocabulário inválido vira `none` (logado), nunca derruba o pedido."""
    try:
        return choose_topic(request, client)
    except TopicsError as error:
        logger.error("Vocabulário de categorias inválido (%s); interação sem categoria", type(error).__name__)
        return NO_TOPIC


def _with_topic(result: ProcessingResult, turn: _Turn, deps: Deps) -> ProcessingResult:
    """Escolhe a categoria depois do degrau decidido e marca a tag; o serviço resolvido não segue no resultado."""
    request = TopicRequest(
        turn.text, result.category or OTHER_TOPIC, is_urgent(turn.text), result.service, turn.history
    )
    choice = _choose_topic(request, _topic_client(deps))
    return replace(
        result,
        topic=choice.topic,
        topic_source=choice.source,
        needs_human=_requires_human(result.status),
        service=None,
    )


def _interaction(digest: str, result: ProcessingResult, run_id: int | None) -> InteractionRecord:
    return InteractionRecord(
        request_hash=digest,
        topic_source=result.topic_source,
        needs_human=result.needs_human,
        topic=result.topic,
        tier=result.tier,
        used_llm=result.used_llm,
        fallback_reason=result.fallback_reason,
        response_text=result.response_text,
        run_id=run_id,
    )


def message_hash(text: str, conversation: Conversation | None = None) -> str:
    """Chave de idempotência da mensagem anonimizada: no lote, o hash do texto; no chat, também a conversa e o número.

    Com a conversa e o número no hash, repetir a mesma pergunta no chat é processado e respondido, não "já registrado".
    """
    if conversation is None:
        return request_hash(text)
    return request_hash(f"{conversation.id}|{conversation.turn}|{text}")


def process_request(
    request: Request, deps: Deps, conversation: Conversation | None = None, run_id: int | None = None
) -> ProcessingResult:
    """Anonimiza → hash → duplicado? → classifica → decide → resolve e responde (ou revisão) → categoria → grava.

    Só o texto anonimizado é classificado, gravado ou logado. Modelo ausente leva à revisão. `conversation`, quando
    há, traz as mensagens anteriores **já anonimizadas**; só a mensagem atual é gravada. `run_id` é a execução em lote
    (nulo no chat) e vai para a interação catalogada.
    """
    text = anonymize(request.text).text
    digest = message_hash(text, conversation)
    if deps.repository.already_processed(digest):
        return ProcessingResult(STATUS_SKIPPED_DUPLICATE)
    turn = _Turn(text, conversation.messages if conversation is not None else ())
    result = _with_topic(_triage(turn, deps), turn, deps)
    record = RequestRecord(digest, text, result.status, result.category, result.confidence, result.reason)
    _persist(record, deps)
    _persist_interaction(_interaction(digest, result, run_id), deps)
    return result


def process_rejection(rejection: Rejection, deps: Deps, run_id: int | None = None) -> ProcessingResult:
    """Registra o descarte da ingestão como `rejected` e abre a revisão `invalid_input`.

    O hash vem da origem e do motivo (não há texto aproveitável), então rodar de novo não duplica. A interação fica
    sem categoria (`none`) e com a tag `needs_human`; o LLM não é chamado.
    """
    digest = request_hash(f"{rejection.source}|{rejection.reason}")
    if deps.repository.already_processed(digest):
        return ProcessingResult(STATUS_SKIPPED_DUPLICATE)
    reason = ReviewReason.INVALID_INPUT.value
    text = REJECTED_TEXT_TEMPLATE.format(reason=rejection.reason)
    _persist(RequestRecord(digest, text, STATUS_REJECTED, review_reason=reason), deps)
    result = ProcessingResult(
        STATUS_REJECTED, reason=reason, topic=NO_TOPIC.topic, topic_source=NO_TOPIC.source, needs_human=True
    )
    _persist_interaction(_interaction(digest, result, run_id), deps)
    return result


def route_to_safe_review(request: Request, deps: Deps, run_id: int | None = None) -> None:
    """Caminho seguro depois de uma falha inesperada: garante o pedido na fila de revisão, sem duplicá-lo.

    A interação sai com a tag `needs_human` e a categoria determinística: o LLM nunca é chamado aqui.
    """
    text = anonymize(request.text).text
    digest = request_hash(text)
    if deps.repository.already_processed(digest):
        return
    record = RequestRecord(digest, text, STATUS_QUEUED_FOR_REVIEW, review_reason=SAFE_REVIEW_REASON)
    _persist(record, deps)
    safe = _with_topic(ProcessingResult(STATUS_QUEUED_FOR_REVIEW), _Turn(text), replace(deps, llm_client=None))
    _persist_interaction(_interaction(digest, safe, run_id), deps)
