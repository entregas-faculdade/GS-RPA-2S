"""Resposta em degraus: serviço, canal geral achado pelo localizador, "não tenho a informação" e emergência."""

import logging
from collections.abc import Callable

import pytest

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import Link, Phone, ServiceEntry
from triage.automation.finder import FinderMatch
from triage.automation.link_check import LinkStatus
from triage.automation.messages import (
    EMERGENCY_PRIORITY_TEXT,
    build_no_information_message,
)
from triage.automation.resolver import CatalogLookup
from triage.classification.decision import Decision, ReviewReason
from triage.ingestion import Request
from triage.pipeline import Deps, process_request

URGENT_TEXT = "Meu benefício foi cortado e preciso de ajuda urgente hoje."
RG_TEXT = "Preciso saber como emitir a segunda via do meu RG. Nunca fiz esse pedido antes."
ALVARA_TEXT = "Quero tirar o alvará de funcionamento do meu comércio."
PII_TEXT = "Meu CPF é 123.456.789-09 e quero tirar o alvará de funcionamento."
PORTAL_URL = "https://www.gov.br/portal-geral"
MakeDeps = Callable[..., Deps]


def _entry(entry_id: str, **overrides: object) -> ServiceEntry:
    values: dict = {
        "id": entry_id,
        "category": None,
        "kind": "portal",
        "scope": "municipal",
        "coverage": "Cidade de São Paulo",
        "area": "city",
        "display_name": "Atendimento da Prefeitura",
        "agency": "Prefeitura",
        "instructions": "Ligue ou acesse o portal.",
        "keywords": ("alvara",),
        "links": (Link("Portal geral", PORTAL_URL),),
        "phones": (),
        "source_note": "fonte",
        "verified_on": "2026-11-09",
        "status": "approved",
    }
    return ServiceEntry(**{**values, **overrides})


def _safety(entry_id: str, label: str, number: str, status: str = "approved") -> ServiceEntry:
    return _entry(entry_id, kind="channel", area="safety", status=status, phones=(Phone(label, number),), links=())


class FakeFinder:
    """Localizador falso: devolve a entrada combinada (ou nada) e guarda o texto que recebeu."""

    def __init__(self, entry: ServiceEntry | None = None) -> None:
        self.entry = entry
        self.texts: list[str] = []

    def find(self, text: str) -> FinderMatch | None:
        self.texts.append(text)
        return None if self.entry is None else FinderMatch(self.entry, 0.9, 0.5)


def _lookup(entries: list[ServiceEntry], link_ok: bool = True) -> CatalogLookup:
    def check(_url: str) -> LinkStatus:
        return LinkStatus(link_ok, 200 if link_ok else None, None if link_ok else "Timeout")

    return CatalogLookup(entries, load_allowed_suffixes(), check)


@pytest.fixture
def decide(monkeypatch: pytest.MonkeyPatch) -> Callable[[ReviewReason | None], None]:
    """Fixa a decisão do classificador para exercitar cada ramo do fluxo sem depender do modelo."""

    def fix(reason: ReviewReason | None) -> None:
        action = "auto_answer" if reason is None else "human_review"
        decision = Decision(action, "other" if reason else "id_card", 0.5, reason)
        monkeypatch.setattr("triage.pipeline.processor.triage_decision", lambda *_args, **_kwargs: decision)

    return fix


def _request(text: str) -> Request:
    return Request("r1", text, "r1.txt")


def _reasons(deps: Deps) -> list[str]:
    return [item.reason for item in deps.repository.pending_reviews()]


def test_urgent_request_shows_only_approved_safety_phones_and_skips_the_finder(make_deps: MakeDeps) -> None:
    entries = [
        _safety("police", "Polícia Militar", "190"),
        _safety("samu", "SAMU", "192"),
        _safety("candidate", "Candidato", "999", status="candidate"),
        _entry("city", kind="channel", phones=(Phone("Prefeitura", "156"),), links=()),
    ]
    finder = FakeFinder(_entry("nunca"))
    deps = make_deps(lookup=_lookup(entries), finder=finder)

    result = process_request(_request(URGENT_TEXT), deps)

    assert (result.status, result.reason, result.tier) == ("queued_for_review", "urgent", None)
    assert "Polícia Militar: 190" in result.response_text
    assert "SAMU: 192" in result.response_text
    assert "999" not in result.response_text
    assert "156" not in result.response_text
    assert finder.texts == []
    assert _reasons(deps) == ["urgent"]


def test_urgent_request_with_real_catalog_lists_only_catalog_numbers(make_deps: MakeDeps) -> None:
    deps = make_deps()

    result = process_request(_request(URGENT_TEXT), deps)

    approved_numbers = {
        phone.number
        for entry in deps.lookup.approved_entries()
        if entry.area == "safety" and entry.kind == "channel"
        for phone in entry.phones
    }
    listed = [line.rsplit(": ", 1)[1] for line in result.response_text.splitlines()[1:-1]]
    assert listed and set(listed) <= approved_numbers
    assert len(listed) == len(set(listed))


def test_urgent_request_without_safety_channel_gets_priority_text_and_warning(
    make_deps: MakeDeps, caplog: pytest.LogCaptureFixture
) -> None:
    deps = make_deps(lookup=_lookup([_entry("city")]))

    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        result = process_request(_request(URGENT_TEXT), deps)

    assert (result.status, result.reason) == ("queued_for_review", "urgent")
    assert result.response_text == EMERGENCY_PRIORITY_TEXT
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_auto_answer_is_tier_catalog_and_skips_the_finder(make_deps: MakeDeps) -> None:
    finder = FakeFinder(_entry("nunca"))
    deps = make_deps(finder=finder)

    result = process_request(_request(RG_TEXT), deps)

    assert (result.status, result.category, result.tier) == ("answered", "id_card", "catalog")
    assert "https://" in result.response_text
    assert finder.texts == []


def test_auto_answer_with_dead_link_goes_to_review_as_before(make_deps: MakeDeps) -> None:
    finder = FakeFinder(_entry("nunca"))
    deps = make_deps(link_ok=False, finder=finder)

    result = process_request(_request(RG_TEXT), deps)

    assert (result.status, result.reason, result.link_status, result.tier) == (
        "queued_for_review",
        "link_unavailable",
        "unavailable",
        None,
    )
    assert finder.texts == []


@pytest.mark.parametrize("reason", [ReviewReason.OUT_OF_CATALOG, ReviewReason.LOW_CONFIDENCE])
def test_found_source_is_answered_at_tier_finder_as_suggestion(
    make_deps: MakeDeps, decide: Callable[..., None], reason: ReviewReason
) -> None:
    decide(reason)
    deps = make_deps(lookup=_lookup([_entry("gap_city")]), finder=FakeFinder(_entry("gap_city")))

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason, result.tier, result.link_status) == ("answered", None, "finder", "ok")
    assert result.response_text.startswith("Não encontrei um serviço específico")
    assert PORTAL_URL in result.response_text
    assert deps.repository.pending_reviews() == []


def test_found_service_entry_keeps_the_service_text(make_deps: MakeDeps, decide: Callable[..., None]) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    service = _entry("alvara", kind="service")
    deps = make_deps(lookup=_lookup([service]), finder=FakeFinder(service))

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.tier) == ("answered", "finder")
    assert result.response_text.startswith("Para resolver o seu pedido")


def test_found_source_with_dead_link_goes_to_review_link_unavailable(
    make_deps: MakeDeps, decide: Callable[..., None]
) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    deps = make_deps(lookup=_lookup([_entry("gap_city")], link_ok=False), finder=FakeFinder(_entry("gap_city")))

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason, result.link_status, result.tier) == (
        "queued_for_review",
        "link_unavailable",
        "unavailable",
        None,
    )
    assert result.response_text is None
    assert _reasons(deps) == ["link_unavailable"]


def test_found_source_with_only_phones_is_answered_without_network(
    make_deps: MakeDeps, decide: Callable[..., None]
) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    channel = _entry("gap_156", kind="channel", phones=(Phone("Central 156", "156"),), links=())
    deps = make_deps(lookup=_lookup([channel], link_ok=False), finder=FakeFinder(channel))

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.tier) == ("answered", "finder")
    assert "Central 156: 156" in result.response_text


@pytest.mark.parametrize("reason", [ReviewReason.OUT_OF_CATALOG, ReviewReason.LOW_CONFIDENCE])
def test_source_not_found_says_no_information_and_keeps_the_original_reason(
    make_deps: MakeDeps, decide: Callable[..., None], reason: ReviewReason
) -> None:
    decide(reason)
    deps = make_deps(finder=FakeFinder(None))

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason, result.tier) == ("queued_for_review", reason.value, None)
    assert result.response_text == build_no_information_message()
    assert _reasons(deps) == [reason.value]


def test_without_finder_the_flow_falls_to_no_information(make_deps: MakeDeps, decide: Callable[..., None]) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    deps = make_deps()

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason) == ("queued_for_review", "out_of_catalog")
    assert result.response_text == build_no_information_message()


def test_ambiguous_request_goes_to_review_with_generic_message(make_deps: MakeDeps, decide: Callable[..., None]) -> None:
    decide(ReviewReason.AMBIGUOUS)
    finder = FakeFinder(_entry("nunca"))
    deps = make_deps(finder=finder)

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason, result.response_text, result.tier) == ("queued_for_review", "ambiguous", None, None)
    assert finder.texts == []


def test_missing_model_goes_to_review_without_calling_the_finder(make_deps: MakeDeps) -> None:
    finder = FakeFinder(_entry("nunca"))
    deps = make_deps(model=None, finder=finder)

    result = process_request(_request(ALVARA_TEXT), deps)

    assert (result.status, result.reason, result.response_text) == ("queued_for_review", "low_confidence", None)
    assert finder.texts == []


def test_finder_receives_only_the_anonymized_text(make_deps: MakeDeps, decide: Callable[..., None]) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    finder = FakeFinder(None)
    deps = make_deps(finder=finder)

    process_request(_request(PII_TEXT), deps)

    [seen] = finder.texts
    assert "123.456.789-09" not in seen
    assert "[CPF]" in seen


def test_same_request_again_is_skipped_for_every_tier(make_deps: MakeDeps, decide: Callable[..., None]) -> None:
    decide(ReviewReason.OUT_OF_CATALOG)
    finder = FakeFinder(_entry("gap_city"))
    deps = make_deps(lookup=_lookup([_entry("gap_city")]), finder=finder)
    process_request(_request(ALVARA_TEXT), deps)

    again = process_request(_request(ALVARA_TEXT), deps)

    assert again.status == "skipped_duplicate"
    assert len(finder.texts) == 1
