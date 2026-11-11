"""Resposta final ao cidadão: o texto do template (sempre disponível) ou o redigido pelo LLM, com o motivo de fallback."""

from dataclasses import dataclass

from triage.automation.catalog import ServiceEntry
from triage.automation.templates import render_template

FALLBACK_LLM_UNAVAILABLE = "llm_unavailable"
FALLBACK_LLM_INVALID_RESPONSE = "llm_invalid_response"
FALLBACK_LLM_OUTPUT_REJECTED = "llm_output_rejected"


@dataclass(frozen=True)
class Response:
    """Texto final; `used_llm` diz se veio do LLM e `fallback_reason` por que o template o substituiu."""

    text: str
    used_llm: bool
    fallback_reason: str | None


def build_response(service: ServiceEntry, fallback_reason: str | None = None) -> Response:
    """A resposta do template do serviço, com o motivo pelo qual o LLM não a redigiu (se ele foi tentado)."""
    return Response(text=render_template(service), used_llm=False, fallback_reason=fallback_reason)


def build_llm_response(text: str) -> Response:
    """A resposta redigida pelo LLM e já aprovada pela guarda."""
    return Response(text=text, used_llm=True, fallback_reason=None)
