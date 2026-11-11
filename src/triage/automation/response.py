"""Resposta final ao cidadão: template sempre disponível, reformulação por LLM opcional e validada."""

import logging
from dataclasses import dataclass

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmClient, LlmInvalidResponse, LlmUnavailable
from triage.automation.response_guard import validate_llm_output
from triage.automation.templates import render_template

FALLBACK_LLM_UNAVAILABLE = "llm_unavailable"
FALLBACK_LLM_INVALID_RESPONSE = "llm_invalid_response"
FALLBACK_LLM_OUTPUT_REJECTED = "llm_output_rejected"

REWRITE_TASK = "rewrite"

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class Response:
    """Texto final; `used_llm` diz se veio do LLM e `fallback_reason` por que o template o substituiu."""

    text: str
    used_llm: bool
    fallback_reason: str | None


def _template_response(text: str, reason: str | None) -> Response:
    return Response(text=text, used_llm=False, fallback_reason=reason)


def build_response(service: ServiceEntry, client: LlmClient | None = None) -> Response:
    """Devolve sempre uma resposta utilizável; qualquer falha do LLM cai no template, com log.

    A mensagem enviada leva só a resposta-template (nenhum texto do cidadão) e a saída do LLM só vale
    se `validate_llm_output` a aprovar.
    """
    template_text = render_template(service)
    if client is None:
        return _template_response(template_text, None)
    try:
        rewritten = client.complete(REWRITE_TASK, template_text)
    except LlmUnavailable as error:
        logger.warning("LLM indisponível (%s); usando o template", error)
        return _template_response(template_text, FALLBACK_LLM_UNAVAILABLE)
    except LlmInvalidResponse as error:
        logger.warning("Resposta inválida do LLM (%s); usando o template", error)
        return _template_response(template_text, FALLBACK_LLM_INVALID_RESPONSE)
    rejection = validate_llm_output(rewritten, service)
    if rejection is not None:
        logger.warning("Saída do LLM rejeitada (%s); usando o template", rejection)
        return _template_response(template_text, FALLBACK_LLM_OUTPUT_REJECTED)
    return Response(text=rewritten, used_llm=True, fallback_reason=None)
