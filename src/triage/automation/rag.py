"""Resposta redigida pelo LLM a partir das fontes aprovadas recuperadas do catálogo (RAG), com guarda na saída."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmClient, LlmInvalidResponse, LlmUnavailable
from triage.automation.response import (
    FALLBACK_LLM_INVALID_RESPONSE,
    FALLBACK_LLM_OUTPUT_REJECTED,
    FALLBACK_LLM_UNAVAILABLE,
)
from triage.automation.response_guard import validate_rag_output

ANSWER_TASK = "answer"
NO_SOURCE_MARKER = "NENHUMA_FONTE"
REQUEST_OPEN = "<<<PEDIDO"
REQUEST_CLOSE = "PEDIDO>>>"
SOURCE_HEADER = "FONTE {number}"
SOURCE_FIELDS = (
    "Nome: {display_name}",
    "Órgão: {agency}",
    "Abrangência: {coverage}",
    "Instruções: {instructions}",
)
LINKS_HEADER = "Links:"
PHONES_HEADER = "Telefones:"

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class RagResult:
    """Desfecho da chamada: o texto válido do LLM, `no_source` (ele disse que nenhuma fonte atende) ou o motivo de fallback."""

    text: str | None = None
    no_source: bool = False
    fallback_reason: str | None = None


def _source_block(number: int, source: ServiceEntry) -> list[str]:
    """Uma fonte exatamente como no catálogo: campos, `rótulo: url` por link e `rótulo: número` por telefone."""
    lines = [SOURCE_HEADER.format(number=number)]
    lines.extend(field.format(**vars(source)) for field in SOURCE_FIELDS)
    if source.links:
        lines.extend([LINKS_HEADER, *(f"- {link.label}: {link.url}" for link in source.links)])
    if source.phones:
        lines.extend([PHONES_HEADER, *(f"- {phone.label}: {phone.number}" for phone in source.phones)])
    return lines


def _neutralize_delimiters(text: str) -> str:
    """Tira do pedido os delimitadores da mensagem, para que ele não feche o bloco de dado e simule instrução."""
    return text.replace(REQUEST_OPEN, " ").replace(REQUEST_CLOSE, " ")


def build_rag_message(text: str, sources: Sequence[ServiceEntry]) -> str:
    """Mensagem do usuário: o pedido anonimizado entre delimitadores (dado, não ordem) e as fontes numeradas."""
    lines = [REQUEST_OPEN, _neutralize_delimiters(text), REQUEST_CLOSE]
    for number, source in enumerate(sources, start=1):
        lines.extend(["", *_source_block(number, source)])
    return "\n".join(lines)


def answer_with_sources(client: LlmClient, text: str, sources: Sequence[ServiceEntry]) -> RagResult:
    """Pede ao LLM a resposta sobre as fontes; só devolve texto que a guarda aprova.

    Sem fonte o LLM não é chamado. O log traz só o tipo do erro ou o motivo da rejeição, nunca o pedido nem a saída.
    """
    if not sources:
        return RagResult(no_source=True)
    try:
        answer = client.complete(ANSWER_TASK, build_rag_message(text, sources))
    except LlmUnavailable as error:
        logger.warning("LLM indisponível (%s); sem resposta redigida", type(error).__name__)
        return RagResult(fallback_reason=FALLBACK_LLM_UNAVAILABLE)
    except LlmInvalidResponse as error:
        logger.warning("Resposta inválida do LLM (%s); sem resposta redigida", type(error).__name__)
        return RagResult(fallback_reason=FALLBACK_LLM_INVALID_RESPONSE)
    if answer.strip() == NO_SOURCE_MARKER:
        logger.info("LLM respondeu que nenhuma fonte atende o pedido")
        return RagResult(no_source=True)
    rejection = validate_rag_output(answer, sources)
    if rejection is not None:
        logger.warning("Saída do LLM rejeitada (%s); sem resposta redigida", rejection)
        return RagResult(fallback_reason=FALLBACK_LLM_OUTPUT_REJECTED)
    return RagResult(text=answer)
