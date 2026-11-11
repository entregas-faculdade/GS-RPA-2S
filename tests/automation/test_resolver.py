"""Resolução de categoria: fontes aprovadas, links vivos e cache de verificação por execução."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date

import pytest

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import ServiceEntry, load_catalog
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup, ManualCheckPolicy, resolve_service

SUFFIXES = frozenset({"gov.br"})
GOOD_URL = "https://www.gov.br/inss"
OTHER_URL = "https://www.gov.br/outro"


class RecordingChecker:
    def __init__(self, dead: frozenset[str] = frozenset(), everything_dead: bool = False) -> None:
        self.dead = dead
        self.everything_dead = everything_dead
        self.calls: list[str] = []

    def __call__(self, url: str) -> LinkStatus:
        self.calls.append(url)
        if self.everything_dead or url in self.dead:
            return LinkStatus(False, None, "Timeout")
        return LinkStatus(True, 200, None)


def _lookup(checker: Callable[[str], LinkStatus], *entries: ServiceEntry) -> CatalogLookup:
    return CatalogLookup(entries, SUFFIXES, checker)


def test_resolves_service_with_working_allowed_link(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = make_entry()
    resolution = _lookup(RecordingChecker(), entry).resolve("social_security")
    assert resolution.service == entry
    assert resolution.reason is None


@pytest.mark.parametrize("category", ["other", "unknown_category", ""])
def test_other_and_unknown_are_out_of_catalog(category: str, make_entry: Callable[..., ServiceEntry]) -> None:
    checker = RecordingChecker()
    resolution = _lookup(checker, make_entry("other"), make_entry("social_security")).resolve(category)
    assert (resolution.service, resolution.reason) == (None, "out_of_catalog")
    assert checker.calls == []


def test_candidate_entry_is_never_used(make_entry: Callable[..., ServiceEntry]) -> None:
    checker = RecordingChecker()
    resolution = _lookup(checker, make_entry(status="candidate")).resolve("social_security")
    assert (resolution.service, resolution.reason) == (None, "out_of_catalog")
    assert checker.calls == []


def test_only_service_kind_entries_resolve_a_category(make_entry: Callable[..., ServiceEntry]) -> None:
    portal = make_entry(kind="portal")
    resolution = _lookup(RecordingChecker(), portal).resolve("social_security")
    assert resolution.reason == "out_of_catalog"


def test_first_approved_entry_of_the_category_wins(make_entry: Callable[..., ServiceEntry]) -> None:
    candidate = make_entry("a", status="candidate", category="social_security")
    first = make_entry("b", category="social_security")
    second = make_entry("c", category="social_security")
    resolution = _lookup(RecordingChecker(), candidate, first, second).resolve("social_security")
    assert resolution.service == first


def test_dead_link_keeps_the_entry_with_the_live_one(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = make_entry(links=(("Vivo", GOOD_URL), ("Morto", OTHER_URL)))
    resolution = _lookup(RecordingChecker(dead=frozenset({OTHER_URL})), entry).resolve("social_security")
    assert resolution.reason is None
    assert [link.url for link in resolution.service.links] == [GOOD_URL]
    assert entry.links[1].url == OTHER_URL


def test_no_live_link_is_unavailable_and_logged(
    caplog: pytest.LogCaptureFixture, make_entry: Callable[..., ServiceEntry]
) -> None:
    lookup = _lookup(RecordingChecker(everything_dead=True), make_entry())
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        resolution = lookup.resolve("social_security")
    assert (resolution.service, resolution.reason) == (None, "link_unavailable")
    assert caplog.records


def test_link_outside_allowlist_is_dropped_and_logged(
    caplog: pytest.LogCaptureFixture, make_entry: Callable[..., ServiceEntry]
) -> None:
    checker = RecordingChecker()
    entry = make_entry(links=(("Falso", "https://gov.br.evil.com"), ("Bom", GOOD_URL)))
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        resolution = _lookup(checker, entry).resolve("social_security")
    assert [link.url for link in resolution.service.links] == [GOOD_URL]
    assert checker.calls == [GOOD_URL]
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_only_link_outside_allowlist_is_unavailable(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = make_entry(links=(("Falso", "https://gov.br.evil.com"),))
    resolution = _lookup(RecordingChecker(), entry).resolve("social_security")
    assert (resolution.service, resolution.reason) == (None, "link_unavailable")


def test_phone_only_entry_is_accepted_without_network(make_entry: Callable[..., ServiceEntry]) -> None:
    checker = RecordingChecker(everything_dead=True)
    entry = make_entry("sp156", links=(), phones=(("Central 156", "156"),), kind="channel")
    resolution = _lookup(checker, entry).resolve_entry(entry)
    assert resolution.service == entry
    assert checker.calls == []


def test_approved_entries_lists_only_approved(make_entry: Callable[..., ServiceEntry]) -> None:
    approved = make_entry("a")
    lookup = _lookup(RecordingChecker(), approved, make_entry("b", status="candidate"))
    assert lookup.approved_entries() == [approved]


def test_link_is_checked_once_per_lookup(make_entry: Callable[..., ServiceEntry]) -> None:
    checker = RecordingChecker()
    lookup = _lookup(checker, make_entry("a", category="social_security"), make_entry("b", category="social_benefits"))
    lookup.resolve("social_security")
    lookup.resolve("social_security")
    lookup.resolve("social_benefits")
    assert checker.calls == [GOOD_URL]


def test_module_function_uses_given_lookup(make_entry: Callable[..., ServiceEntry]) -> None:
    lookup = _lookup(RecordingChecker(), make_entry("cpf_registration"))
    assert resolve_service("cpf_registration", lookup).service is not None


def test_module_function_defaults_to_versioned_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("triage.automation.resolver.check_link", RecordingChecker())
    resolution = resolve_service("other")
    assert resolution.reason == "out_of_catalog"


TODAY = date(2026, 11, 10)
POLICY = ManualCheckPolicy(max_age_days=180, today=lambda: TODAY)
BLOCKED_URL = "https://www.gov.br/bloqueado"


def _status_checker(status: LinkStatus) -> Callable[[str], LinkStatus]:
    return lambda url: status


def _attested(make_entry: Callable[..., ServiceEntry], manual_check_on: str | None) -> ServiceEntry:
    entry = make_entry()
    link = replace(entry.links[0], url=BLOCKED_URL, manual_check_on=manual_check_on)
    return replace(entry, links=(link,))


def _resolve_attested(status: LinkStatus, entry: ServiceEntry) -> tuple[object, object]:
    resolution = CatalogLookup((entry,), SUFFIXES, _status_checker(status), POLICY).resolve("social_security")
    return resolution.service, resolution.reason


def test_403_with_valid_manual_check_keeps_the_link_and_warns(
    caplog: pytest.LogCaptureFixture, make_entry: Callable[..., ServiceEntry]
) -> None:
    entry = _attested(make_entry, "2026-11-01")
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        service, reason = _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry)
    assert (service, reason) == (entry, None)
    assert any("validação manual" in record.getMessage() for record in caplog.records)


def test_manual_check_exactly_at_the_age_limit_is_valid(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = _attested(make_entry, "2026-05-14")
    assert _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry)[1] is None


def test_403_with_expired_manual_check_drops_the_link(
    caplog: pytest.LogCaptureFixture, make_entry: Callable[..., ServiceEntry]
) -> None:
    entry = _attested(make_entry, "2026-05-13")
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        assert _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry) == (None, "link_unavailable")
    assert any("vencido" in record.getMessage() for record in caplog.records)


def test_403_without_manual_check_drops_the_link(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = _attested(make_entry, None)
    assert _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry) == (None, "link_unavailable")


def test_future_manual_check_is_not_valid(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = _attested(make_entry, "2026-12-01")
    assert _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry) == (None, "link_unavailable")


@pytest.mark.parametrize(
    "status",
    [
        LinkStatus(False, 404, "HTTP 404"),
        LinkStatus(False, 503, "HTTP 503"),
        LinkStatus(False, None, "Timeout"),
        LinkStatus(False, None, "ConnectionError"),
        LinkStatus(False, None, "SSLError"),
    ],
)
def test_valid_manual_check_never_rescues_failures_other_than_403(
    status: LinkStatus, make_entry: Callable[..., ServiceEntry]
) -> None:
    entry = _attested(make_entry, "2026-11-09")
    assert _resolve_attested(status, entry) == (None, "link_unavailable")


def test_manual_check_does_not_bypass_the_allowlist(make_entry: Callable[..., ServiceEntry]) -> None:
    entry = make_entry(links=(("Falso", "https://gov.br.evil.com"),))
    entry = replace(entry, links=(replace(entry.links[0], manual_check_on="2026-11-09"),))
    assert _resolve_attested(LinkStatus(False, 403, "HTTP 403"), entry) == (None, "link_unavailable")


def test_each_versioned_category_resolves_with_live_links() -> None:
    lookup = CatalogLookup(load_catalog(extra_dir=None), load_allowed_suffixes(), RecordingChecker())
    for entry in (entry for entry in load_catalog(extra_dir=None) if entry.category):
        resolution = lookup.resolve(entry.category)
        assert resolution.reason is None, entry.id
        assert resolution.service.links == entry.links
