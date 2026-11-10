"""Resolução de categoria: causas de falha e cache de verificação por execução."""

import logging

import pytest

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import ServiceEntry
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup, resolve_service

SUFFIXES = frozenset({"gov.br"})
GOOD_URL = "https://www.gov.br/inss"


def _entry(category: str, url: str = GOOD_URL) -> ServiceEntry:
    return ServiceEntry(category, "Nome", "Órgão", url, "Instruções.", "fonte", "2026-11-09")


class RecordingChecker:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.calls: list[str] = []

    def __call__(self, url: str) -> LinkStatus:
        self.calls.append(url)
        return LinkStatus(self.ok, 200 if self.ok else None, None if self.ok else "Timeout")


def _lookup(checker: RecordingChecker, *entries: ServiceEntry) -> CatalogLookup:
    return CatalogLookup({entry.category: entry for entry in entries}, SUFFIXES, checker)


def test_resolves_service_with_working_allowed_link() -> None:
    entry = _entry("social_security")
    resolution = _lookup(RecordingChecker(), entry).resolve("social_security")
    assert resolution.service == entry
    assert resolution.reason is None


@pytest.mark.parametrize("category", ["other", "unknown_category", ""])
def test_other_and_unknown_are_out_of_catalog(category: str) -> None:
    checker = RecordingChecker()
    resolution = _lookup(checker, _entry("other"), _entry("social_security")).resolve(category)
    assert (resolution.service, resolution.reason) == (None, "out_of_catalog")
    assert checker.calls == []


def test_url_outside_allowlist_is_unavailable_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    checker = RecordingChecker()
    lookup = _lookup(checker, _entry("id_card", "https://gov.br.evil.com"))
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        resolution = lookup.resolve("id_card")
    assert (resolution.service, resolution.reason) == (None, "link_unavailable")
    assert checker.calls == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_dead_link_is_unavailable_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    lookup = _lookup(RecordingChecker(ok=False), _entry("voter_id"))
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        resolution = lookup.resolve("voter_id")
    assert (resolution.service, resolution.reason) == (None, "link_unavailable")
    assert caplog.records


def test_link_is_checked_once_per_lookup() -> None:
    checker = RecordingChecker()
    lookup = _lookup(checker, _entry("social_security"), _entry("social_benefits"))
    lookup.resolve("social_security")
    lookup.resolve("social_security")
    lookup.resolve("social_benefits")
    assert checker.calls == [GOOD_URL]


def test_module_function_uses_given_lookup() -> None:
    lookup = _lookup(RecordingChecker(), _entry("cpf_registration"))
    assert resolve_service("cpf_registration", lookup).service is not None


def test_module_function_defaults_to_versioned_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("triage.automation.resolver.check_link", RecordingChecker())
    resolution = resolve_service("other")
    assert resolution.reason == "out_of_catalog"


def test_all_versioned_urls_are_allowed() -> None:
    from triage.automation.catalog import load_catalog

    assert all(is_allowed(entry.url) for entry in load_catalog().values())
