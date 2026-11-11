"""Resposta final: template como padrão e todo caminho de falha do LLM caindo nele."""

import dataclasses
import logging

import pytest

from triage.automation.catalog import Link, Phone, ServiceEntry
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
SERVICE = ServiceEntry(
    id="social_security",
    category="social_security",
    kind="service",
    scope="federal",
    coverage="Brasil",
    area="social",
    display_name="Aposentadoria (INSS)",
    agency="INSS",
    instructions="Entre com a conta gov.br.",
    keywords=("inss",),
    links=(Link("Portal do INSS", URL),),
    phones=(),
    source_note="fonte",
    verified_on="2026-11-09",
    status="approved",
)
TEMPLATE = render_template(SERVICE)


class StubClient:
    def __init__(self, answer: str | BaseException) -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def complete(self, task: str, user_message: str) -> str:
        self.calls.append((task, user_message))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def test_template_has_service_name_agency_coverage_instructions_and_link() -> None:
    for part in ("Aposentadoria (INSS)", "INSS", "Brasil", "Entre com a conta gov.br.", f"Portal do INSS: {URL}"):
        assert part in TEMPLATE
    assert "Telefones" not in TEMPLATE
    assert render_template(SERVICE) == TEMPLATE


def test_template_lists_every_link_and_phone_one_per_line() -> None:
    other = "https://www.gov.br/outro"
    service = dataclasses.replace(
        SERVICE,
        links=(Link("Portal do INSS", URL), Link("Outra página", other)),
        phones=(Phone("Central do INSS", "135"), Phone("Ouvidoria", "0800 61 61 61")),
    )
    lines = render_template(service).splitlines()
    assert f"Portal do INSS: {URL}" in lines
    assert f"Outra página: {other}" in lines
    assert "Telefones:" in lines
    assert "Central do INSS: 135" in lines
    assert "Ouvidoria: 0800 61 61 61" in lines


def test_template_without_links_shows_only_phones() -> None:
    service = dataclasses.replace(SERVICE, links=(), phones=(Phone("Central 156", "156"),))
    text = render_template(service)
    assert "Central 156: 156" in text
    assert "https://" not in text


def test_without_client_the_template_answers_and_no_fallback_is_reported() -> None:
    response = build_response(SERVICE)
    assert (response.text, response.used_llm, response.fallback_reason) == (TEMPLATE, False, None)


def test_valid_llm_answer_is_used() -> None:
    answer = f"Olá! Para a sua aposentadoria, acesse {URL}."
    response = build_response(SERVICE, StubClient(answer))
    assert (response.text, response.used_llm, response.fallback_reason) == (answer, True, None)


def test_client_gets_the_rewrite_task_with_only_the_template_text() -> None:
    client = StubClient(f"Acesse {URL}")
    build_response(SERVICE, client)
    assert client.calls == [("rewrite", TEMPLATE)]


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
