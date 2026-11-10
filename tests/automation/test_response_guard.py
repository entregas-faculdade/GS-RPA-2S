"""Guarda da saída do LLM: limites e falsos positivos da regra de URL."""

import pytest

from triage.automation.catalog import ServiceEntry
from triage.automation.response_guard import (
    MAX_RESPONSE_LENGTH,
    REJECT_EMPTY,
    REJECT_FOREIGN_URL,
    REJECT_MISSING_URL,
    REJECT_TOO_LONG,
    validate_llm_output,
)

URL = "https://www.gov.br/inss"
SERVICE = ServiceEntry("social_security", "INSS", "Órgão", URL, "Instruções.", "fonte", "2026-11-09")


@pytest.mark.parametrize(
    "text",
    [
        f"Acesse {URL}",
        f"Acesse {URL}.",
        f"Veja ({URL}) para mais detalhes",
        f"Link: {URL}, ok?",
        f"{URL} e de novo {URL}",
        f"Acesse o portal gov.br: {URL}",
        f"Veja {URL} (no portal www.gov.br.)",
        f"Fale com o INSS (inss@example.org) em {URL}",
    ],
)
def test_accepts_text_that_keeps_the_service_url(text: str) -> None:
    assert validate_llm_output(text, SERVICE) is None


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_rejects_empty_text(text: str) -> None:
    assert validate_llm_output(text, SERVICE) == REJECT_EMPTY


def test_length_limit_is_inclusive() -> None:
    at_limit = f"{URL} " + "a" * (MAX_RESPONSE_LENGTH - len(URL) - 1)
    assert len(at_limit) == MAX_RESPONSE_LENGTH
    assert validate_llm_output(at_limit, SERVICE) is None
    assert validate_llm_output(at_limit + "a", SERVICE) == REJECT_TOO_LONG


@pytest.mark.parametrize(
    "text",
    [
        f"{URL} e também https://www.gov.br/outro",
        f"{URL} ou http://www.gov.br/inss",
        f"{URL} ou www.exemplo.com.br",
        f"{URL}/extra",
        "Acesse https://evil.example.com/inss",
        f"{URL}?x=1",
        f"Acesse detran-sp.com.br/pagar ou {URL}",
        f"Acesse golpe.com ou {URL}",
        f"{URL} e gov.br/outro",
        f"{URL} e gov.br.evil.com",
        f"{URL} e evilgov.br",
    ],
)
def test_rejects_any_url_different_from_the_service_url(text: str) -> None:
    assert validate_llm_output(text, SERVICE) == REJECT_FOREIGN_URL


def test_rejects_text_without_the_service_url() -> None:
    assert validate_llm_output("Procure o INSS no site do governo.", SERVICE) == REJECT_MISSING_URL
