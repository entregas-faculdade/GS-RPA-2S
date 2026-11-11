"""Mensagens fixas: "não tenho a informação", emergência só com telefones aprovados de `safety`, e o degrau 2 do template."""

import logging
from collections.abc import Callable

import pytest

from triage.automation.catalog import ServiceEntry
from triage.automation.messages import (
    EMERGENCY_HEADER,
    EMERGENCY_PRIORITY_TEXT,
    build_emergency_message,
    build_no_information_message,
)
from triage.automation.templates import render_template

POLICE = ("Polícia Militar", "190")
SAMU = ("SAMU", "192")
EntryFactory = Callable[..., ServiceEntry]


def _channel(make_entry: EntryFactory, entry_id: str, phone: tuple[str, str], **overrides: object) -> ServiceEntry:
    return make_entry(entry_id, links=(), phones=(phone,), kind="channel", area="safety", **overrides)


def test_no_information_message_says_so_and_promises_no_deadline() -> None:
    text = build_no_information_message()

    assert "não tenho essa informação" in text
    assert "atendimento humano" in text
    assert "prazo" not in text
    assert "http" not in text


def test_emergency_message_lists_one_line_per_approved_safety_channel(make_entry: EntryFactory) -> None:
    entries = [_channel(make_entry, "police", POLICE), _channel(make_entry, "samu", SAMU)]

    lines = build_emergency_message(entries).splitlines()

    assert lines[0] == EMERGENCY_HEADER
    assert lines[1:3] == ["Polícia Militar: 190", "SAMU: 192"]
    assert "atendimento humano" in lines[-1]


def test_emergency_message_ignores_candidates_other_areas_and_non_channels(make_entry: EntryFactory) -> None:
    entries = [
        _channel(make_entry, "police", POLICE),
        _channel(make_entry, "candidate", ("Candidato", "999"), status="candidate"),
        make_entry("city", links=(), phones=(("Prefeitura", "156"),), kind="channel", area="city"),
        make_entry("portal", phones=(("Portal", "888"),), kind="portal", area="safety"),
    ]

    text = build_emergency_message(entries)

    assert "190" in text
    for forbidden in ("999", "156", "888"):
        assert forbidden not in text


def test_emergency_message_does_not_repeat_the_same_phone(make_entry: EntryFactory) -> None:
    entries = [_channel(make_entry, "fire", ("Corpo de Bombeiros", "193")), _channel(make_entry, "gap", ("Corpo de Bombeiros", "193"))]

    assert build_emergency_message(entries).count("193") == 1


def test_emergency_message_without_channels_has_no_number_and_logs_warning(
    make_entry: EntryFactory, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        text = build_emergency_message([make_entry("inss")])

    assert text == EMERGENCY_PRIORITY_TEXT
    assert not any(char.isdigit() for char in text)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_general_channel_template_opens_as_suggestion_and_keeps_the_sections(make_entry: EntryFactory) -> None:
    entry = make_entry("gap", kind="portal", phones=(("Central", "156"),))

    text = render_template(entry)

    assert text.startswith("Não encontrei um serviço específico para o seu pedido.")
    assert "O canal oficial indicado é o do órgão" in text
    assert "pode atender ao seu pedido" in text
    for part in ("Aposentadoria (INSS)", "Órgão responsável: INSS", "Abrangência: Brasil", "Telefones:", "Central: 156"):
        assert part in text
    assert "Portal do INSS: https://www.gov.br/inss" in text


@pytest.mark.parametrize("kind", ["portal", "channel"])
def test_general_channel_template_does_not_promise_human_review(make_entry: EntryFactory, kind: str) -> None:
    text = render_template(make_entry("gap", kind=kind))

    assert "humano" not in text
    assert "descreva o pedido de outra forma" in text


def test_service_template_keeps_its_original_opening(make_entry: EntryFactory) -> None:
    text = render_template(make_entry("inss"))

    assert text.startswith("Para resolver o seu pedido, o serviço indicado é: Aposentadoria (INSS).")
    assert "Não encontrei" not in text
