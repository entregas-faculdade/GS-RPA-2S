"""Escolha, pelo LLM, de uma fonte entre candidatas aprovadas: lista fechada, JSON estrito, nunca texto livre."""

import json
import logging

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmClient, LlmInvalidResponse, LlmUnavailable

LOCATE_TASK = "locate"
NONE_ID = "none"
ID_KEY = "id"
MAX_ANSWER_LENGTH = 200
REQUEST_OPEN = "<<<PEDIDO"
REQUEST_CLOSE = "PEDIDO>>>"
CANDIDATE_LINE = "{id} | {display_name} | {agency}"

logger = logging.getLogger("triage.automation")


def build_locate_message(text: str, candidates: tuple[ServiceEntry, ...]) -> str:
    """Mensagem do usuário: o texto anonimizado entre delimitadores (dado, não ordem) e a lista de candidatas."""
    lines = [
        CANDIDATE_LINE.format(id=entry.id, display_name=entry.display_name, agency=entry.agency) for entry in candidates
    ]
    return "\n".join([REQUEST_OPEN, text, REQUEST_CLOSE, "", *lines])


def parse_choice(answer: str, candidates: tuple[ServiceEntry, ...]) -> ServiceEntry | None:
    """A candidata escolhida, ou `None` para `none` e para qualquer resposta fora do formato `{"id": "<id da lista>"}`."""
    if len(answer) > MAX_ANSWER_LENGTH:
        return None
    try:
        payload = json.loads(answer)
    except ValueError:
        return None
    if not isinstance(payload, dict) or set(payload) != {ID_KEY}:
        return None
    chosen = payload[ID_KEY]
    return next((entry for entry in candidates if isinstance(chosen, str) and entry.id == chosen), None)


def choose_entry(client: LlmClient, text: str, candidates: tuple[ServiceEntry, ...]) -> ServiceEntry | None:
    """Pede ao LLM a melhor candidata ao texto anonimizado; qualquer falha ou resposta inválida é `None`, com log.

    O log nunca traz o texto do pedido nem a resposta do LLM.
    """
    if not candidates:
        return None
    try:
        answer = client.complete(LOCATE_TASK, build_locate_message(text, candidates))
    except (LlmUnavailable, LlmInvalidResponse) as error:
        logger.warning("Assistente de localização falhou (%s); sem fonte", type(error).__name__)
        return None
    entry = parse_choice(answer, candidates)
    if entry is None:
        logger.info("Assistente de localização sem escolha válida; sem fonte")
    return entry
