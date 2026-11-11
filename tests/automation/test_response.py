"""Resposta final: template como padrão e o marcador de resposta redigida pelo LLM."""

import dataclasses

from triage.automation.catalog import Link, Phone, ServiceEntry
from triage.automation.response import (
    FALLBACK_LLM_OUTPUT_REJECTED,
    build_llm_response,
    build_response,
)
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


def test_build_response_is_the_template_without_llm_and_without_reason() -> None:
    response = build_response(SERVICE)
    assert (response.text, response.used_llm, response.fallback_reason) == (TEMPLATE, False, None)


def test_build_response_carries_the_reason_the_llm_did_not_answer() -> None:
    response = build_response(SERVICE, FALLBACK_LLM_OUTPUT_REJECTED)
    assert (response.text, response.used_llm, response.fallback_reason) == (TEMPLATE, False, FALLBACK_LLM_OUTPUT_REJECTED)


def test_llm_response_is_marked_as_written_by_the_llm() -> None:
    response = build_llm_response("Olá!")
    assert (response.text, response.used_llm, response.fallback_reason) == ("Olá!", True, None)
