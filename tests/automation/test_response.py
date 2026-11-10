"""Resposta final: template como padrão e todo caminho de falha do LLM caindo nele."""

import logging

import pytest

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmInvalidResponse, LlmUnavailable
from triage.automation.response import (
    FALLBACK_LLM_INVALID_RESPONSE,
    FALLBACK_LLM_OUTPUT_REJECTED,
    FALLBACK_LLM_UNAVAILABLE,
    build_response,
)
from triage.automation.response_guard import MAX_RESPONSE_LENGTH
from triage.automation.templates import render_template

URL = "https://www.gov.br/inss"
SERVICE = ServiceEntry("social_security", "Aposentadoria (INSS)", "INSS", URL, "Entre com a conta gov.br.", "fonte", "2026-11-09")
TEMPLATE = render_template(SERVICE)


class StubClient:
    def __init__(self, answer: str | BaseException) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    def rewrite(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def test_template_has_service_name_agency_instructions_and_link() -> None:
    for part in ("Aposentadoria (INSS)", "INSS", "Entre com a conta gov.br.", URL):
        assert part in TEMPLATE
    assert render_template(SERVICE) == TEMPLATE


def test_without_client_the_template_answers_and_no_fallback_is_reported() -> None:
    response = build_response(SERVICE)
    assert (response.text, response.used_llm, response.fallback_reason) == (TEMPLATE, False, None)


def test_valid_llm_answer_is_used() -> None:
    answer = f"Olá! Para a sua aposentadoria, acesse {URL}."
    response = build_response(SERVICE, StubClient(answer))
    assert (response.text, response.used_llm, response.fallback_reason) == (answer, True, None)


def test_prompt_carries_only_the_template_text() -> None:
    client = StubClient(f"Acesse {URL}")
    build_response(SERVICE, client)
    assert TEMPLATE in client.prompts[0]
    assert client.prompts[0].endswith(TEMPLATE)


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (LlmUnavailable("Timeout"), FALLBACK_LLM_UNAVAILABLE),
        (LlmInvalidResponse("sem choices"), FALLBACK_LLM_INVALID_RESPONSE),
        ("", FALLBACK_LLM_OUTPUT_REJECTED),
        ("   ", FALLBACK_LLM_OUTPUT_REJECTED),
        ("Acesse https://www.golpe.com.br/inss agora", FALLBACK_LLM_OUTPUT_REJECTED),
        (f"{URL} ou https://www.gov.br/outro", FALLBACK_LLM_OUTPUT_REJECTED),
        ("Procure o INSS no site do governo.", FALLBACK_LLM_OUTPUT_REJECTED),
        (f"{URL} " + "x" * MAX_RESPONSE_LENGTH, FALLBACK_LLM_OUTPUT_REJECTED),
    ],
)
def test_every_failure_falls_back_to_template_with_reason_and_log(
    answer: str | BaseException, reason: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        response = build_response(SERVICE, StubClient(answer))
    assert (response.text, response.used_llm, response.fallback_reason) == (TEMPLATE, False, reason)
    assert any(record.levelno == logging.WARNING for record in caplog.records)
