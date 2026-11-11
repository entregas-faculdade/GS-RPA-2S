"""Processamento de um pedido: da anonimização à resposta ou à fila de revisão.

Com `llm.enabled`, o cliente e o localizador, o texto anonimizado e as fontes aprovadas do catálogo vão ao LLM,
que redige a resposta; sem LLM (o padrão) ou em qualquer falha dele, responde o fluxo determinístico por template.
"""

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
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
from triage.classification import (
    ModelNotAvailableError,
    ReviewReason,
    classify,
    triage_decision,
)
from triage.classification.decision import ACTION_AUTO_ANSWER, Decision
from triage.classification.model import DEFAULT_MODEL_PATH
from triage.classification.model import load as load_model
from triage.common.retry import RetryPolicy, retry_with_backoff
from triage.config import Settings
from triage.ingestion import Rejection, Request
from triage.privacy import anonymize
from triage.storage import Repository, RequestRecord, StorageError, request_hash
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


def _answered(decision: Decision, response: Response, tier: str) -> ProcessingResult:
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


def _catalog_sources(service: ServiceEntry, text: str, deps: Deps) -> tuple[ServiceEntry, ...]:
    """Degrau 1: o serviço resolvido e, depois dele, até `max_candidates - 1` candidatas do localizador (sem repetir)."""
    candidates = deps.finder.top_candidates(text, deps.max_candidates)
    others = [entry for entry in candidates if entry.id != service.id][: deps.max_candidates - 1]
    return (service, *_live_entries(others, deps))


def _catalog_response(service: ServiceEntry, text: str, deps: Deps) -> Response:
    """Degrau 1: o LLM redige sobre as fontes; qualquer falha ou "nenhuma fonte" deixa o template do serviço responder."""
    if not _llm_ready(deps):
        return build_response(service)
    rag = answer_with_sources(deps.llm_client, text, _catalog_sources(service, text, deps))
    if rag.text is not None:
        return build_llm_response(rag.text)
    return build_response(service, rag.fallback_reason)


def _answer_or_review(text: str, decision: Decision, deps: Deps) -> ProcessingResult:
    """Degrau 1: resolve o serviço da categoria e responde; sem serviço utilizável, revisão com a causa."""
    resolution = resolve_service(decision.category, deps.lookup)
    if resolution.service is None:
        return _failed_resolution(decision, resolution.reason)
    return _answered(decision, _catalog_response(resolution.service, text, deps), TIER_CATALOG)


def _gap_rag(text: str, deps: Deps) -> RagResult:
    """Degraus 2 e 3: o LLM redige sobre as candidatas vivas; sem nenhuma, não é chamado e o fluxo determinístico decide."""
    sources = _live_entries(deps.finder.top_candidates(text, deps.max_candidates), deps)
    if not sources:
        return RagResult()
    return answer_with_sources(deps.llm_client, text, sources)


def _no_information(decision: Decision) -> ProcessingResult:
    review = _review(decision.category, decision.confidence, decision.reason.value)
    return replace(review, response_text=build_no_information_message())


def _deterministic_find(text: str, decision: Decision, deps: Deps) -> ProcessingResult:
    """Localizador com limiar: fonte achada responde por template (degrau 2); sem fonte, "não tenho a informação"."""
    match = deps.finder.find(text) if deps.finder is not None else None
    if match is None:
        return _no_information(decision)
    resolution = deps.lookup.resolve_entry(match.entry)
    if resolution.service is None:
        return _failed_resolution(decision, resolution.reason)
    return _answered(decision, build_response(resolution.service), TIER_FINDER)


def _find_or_review(text: str, decision: Decision, deps: Deps) -> ProcessingResult:
    """Degraus 2 e 3: com LLM, ele redige sobre as candidatas; sem LLM ou em falha, decide o localizador determinístico."""
    rag = _gap_rag(text, deps) if _llm_ready(deps) else RagResult()
    if rag.text is not None:
        return _answered(decision, build_llm_response(rag.text), TIER_FINDER)
    if rag.no_source:
        return _no_information(decision)
    return replace(_deterministic_find(text, decision, deps), fallback_reason=rag.fallback_reason)


def _urgent_review(decision: Decision, deps: Deps) -> ProcessingResult:
    """Urgência: revisão com os telefones de emergência aprovados; sem localizador nem resolução."""
    review = _review(decision.category, decision.confidence, decision.reason.value)
    return replace(review, response_text=build_emergency_message(deps.lookup.approved_entries()))


def _triage(text: str, deps: Deps) -> ProcessingResult:
    if deps.model is None:
        return _review(None, 0.0, SAFE_REVIEW_REASON)
    decision = triage_decision(text, classify(text, deps.model), deps.settings)
    if decision.action == ACTION_AUTO_ANSWER:
        return _answer_or_review(text, decision, deps)
    if decision.reason is ReviewReason.URGENT:
        return _urgent_review(decision, deps)
    if decision.reason in FINDER_REASONS:
        return _find_or_review(text, decision, deps)
    return _review(decision.category, decision.confidence, decision.reason.value)


def _store(record: RequestRecord, deps: Deps) -> None:
    """Grava o pedido e, se ele não foi respondido, enfileira a revisão. Repetível: gravar o mesmo hash é ignorado."""
    deps.repository.save_request(record, anonymized=True)
    if record.status != STATUS_ANSWERED:
        deps.repository.enqueue_review(record.request_hash, record.review_reason)


def _persist(record: RequestRecord, deps: Deps) -> None:
    retry_with_backoff(lambda: _store(record, deps), deps.retry_policy, deps.sleep)


def process_request(request: Request, deps: Deps) -> ProcessingResult:
    """Anonimiza → hash → duplicado? → classifica → decide → resolve e responde (ou revisão) → grava.

    Só o texto anonimizado é classificado, gravado ou logado. Modelo ausente leva à revisão.
    """
    text = anonymize(request.text).text
    digest = request_hash(text)
    if deps.repository.already_processed(digest):
        return ProcessingResult(STATUS_SKIPPED_DUPLICATE)
    result = _triage(text, deps)
    record = RequestRecord(digest, text, result.status, result.category, result.confidence, result.reason)
    _persist(record, deps)
    return result


def process_rejection(rejection: Rejection, deps: Deps) -> ProcessingResult:
    """Registra o descarte da ingestão como `rejected` e abre a revisão `invalid_input`.

    O hash vem da origem e do motivo (não há texto aproveitável), então rodar de novo não duplica.
    """
    digest = request_hash(f"{rejection.source}|{rejection.reason}")
    if deps.repository.already_processed(digest):
        return ProcessingResult(STATUS_SKIPPED_DUPLICATE)
    reason = ReviewReason.INVALID_INPUT.value
    text = REJECTED_TEXT_TEMPLATE.format(reason=rejection.reason)
    _persist(RequestRecord(digest, text, STATUS_REJECTED, review_reason=reason), deps)
    return ProcessingResult(STATUS_REJECTED, reason=reason)


def route_to_safe_review(request: Request, deps: Deps) -> None:
    """Caminho seguro depois de uma falha inesperada: garante o pedido na fila de revisão, sem duplicá-lo."""
    text = anonymize(request.text).text
    digest = request_hash(text)
    if deps.repository.already_processed(digest):
        return
    record = RequestRecord(digest, text, STATUS_QUEUED_FOR_REVIEW, review_reason=SAFE_REVIEW_REASON)
    _persist(record, deps)
