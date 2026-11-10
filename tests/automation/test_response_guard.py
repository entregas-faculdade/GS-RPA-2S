"""Guarda da saída do LLM: limites e falsos positivos da regra de URL."""

import dataclasses

import pytest

from triage.automation.catalog import Link, Phone, ServiceEntry
from triage.automation.response_guard import (
    MAX_RESPONSE_LENGTH,
    REJECT_EMPTY,
    REJECT_FOREIGN_PHONE,
    REJECT_FOREIGN_URL,
    REJECT_MISSING_URL,
    REJECT_TOO_LONG,
    validate_llm_output,
)

URL = "https://www.gov.br/inss"
OTHER_URL = "https://www.gov.br/inss/outra"
SERVICE = ServiceEntry(
    id="social_security",
    category="social_security",
    kind="service",
    scope="federal",
    coverage="Brasil",
    area="social",
    display_name="INSS",
    agency="Órgão",
    instructions="Instruções.",
    keywords=("inss",),
    links=(Link("Portal", URL), Link("Outra", OTHER_URL)),
    phones=(Phone("Central", "135"), Phone("Ouvidoria", "0800 61 61 61")),
    source_note="fonte",
    verified_on="2026-11-09",
    status="approved",
)


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
        f"Acesse {OTHER_URL}",
        f"Use {URL} ou {OTHER_URL}",
        f"Ligue 135 e acesse {URL}",
        f"Ligue 0800 61 61 61 ou {URL}",
        f"Ligue (0800) 616-161 ou {URL}",
        f"Em 3 dias úteis, peça a 2ª via em {URL}",
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
        f"{OTHER_URL}/extra",
    ],
)
def test_rejects_any_url_different_from_the_service_url(text: str) -> None:
    assert validate_llm_output(text, SERVICE) == REJECT_FOREIGN_URL


@pytest.mark.parametrize(
    "text",
    [
        f"Ligue 0800 999 9999 ou acesse {URL}",
        f"Ligue 136 e acesse {URL}",
        f"Ligue (11) 3333-4444. Acesse {URL}",
        f"Protocolo 123456 em {URL}",
        f"Ligue 0800 61 61 62 ou {URL}",
    ],
)
def test_rejects_phone_that_is_not_the_service_phone(text: str) -> None:
    assert validate_llm_output(text, SERVICE) == REJECT_FOREIGN_PHONE


def test_phones_inside_urls_and_emails_are_not_phones() -> None:
    text = f"Veja https://www.gov.br/inss e escreva a fale123456@example.org. {URL}"
    assert validate_llm_output(text, SERVICE) is None


def test_service_without_phones_rejects_any_phone() -> None:
    service = dataclasses.replace(SERVICE, phones=())
    assert validate_llm_output(f"Ligue 135 e acesse {URL}", service) == REJECT_FOREIGN_PHONE


def test_phone_only_service_accepts_its_phone_and_rejects_any_url() -> None:
    service = dataclasses.replace(SERVICE, links=(), phones=(Phone("Central 156", "156"),))
    assert validate_llm_output("Ligue 156 para falar com a central.", service) is None
    assert validate_llm_output(f"Ligue 156 ou acesse {URL}", service) == REJECT_FOREIGN_URL


def test_rejects_text_without_the_service_url() -> None:
    assert validate_llm_output("Procure o INSS no site do governo.", SERVICE) == REJECT_MISSING_URL
