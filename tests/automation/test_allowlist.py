"""Allowlist: comparação por sufixo de domínio completo, só https e sem credenciais."""

import json
from pathlib import Path

import pytest

from triage.automation.allowlist import is_allowed, load_allowed_suffixes

SUFFIXES = frozenset({"gov.br"})


@pytest.mark.parametrize(
    "url",
    [
        "https://www.gov.br/pt-br/servicos",
        "https://gov.br",
        "https://servicos.gov.br/x",
        "https://WWW.GOV.BR/x",
        "https://www.gov.br.:443/x",
    ],
)
def test_accepts_gov_br_and_subdomains(url: str) -> None:
    assert is_allowed(url, SUFFIXES)


@pytest.mark.parametrize(
    "url",
    [
        "https://gov.br.evil.com",
        "https://evilgov.br",
        "https://evil.com/gov.br",
        "https://evil.com/?next=https://www.gov.br",
        "http://www.gov.br",
        "ftp://www.gov.br",
        "https://user@www.gov.br",
        "https://user:pass@www.gov.br",
        "https://evil.com\\@www.gov.br",
        "https://www.gov.br:abc/x",
        "https://",
        "www.gov.br",
        "",
        "https://www.gov.br/ x",
        "https://exa mple.gov.br",
    ],
)
def test_rejects_unsafe_or_malformed(url: str) -> None:
    assert not is_allowed(url, SUFFIXES)


def test_rejects_non_string() -> None:
    assert not is_allowed(None, SUFFIXES)  # type: ignore[arg-type]


def test_empty_allowlist_allows_nothing() -> None:
    assert not is_allowed("https://www.gov.br", frozenset())


def test_loads_suffixes_from_file(tmp_path: Path) -> None:
    path = tmp_path / "allowed.json"
    path.write_text(json.dumps([{"suffix": ".Gov.BR.", "reason": "teste"}, {"reason": "sem sufixo"}]), encoding="utf-8")
    assert load_allowed_suffixes(path) == frozenset({"gov.br"})


def test_missing_or_invalid_file_fails_closed(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{nao é json", encoding="utf-8")
    not_a_list = tmp_path / "dict.json"
    not_a_list.write_text("{}", encoding="utf-8")
    assert load_allowed_suffixes(tmp_path / "missing.json") == frozenset()
    assert load_allowed_suffixes(broken) == frozenset()
    assert load_allowed_suffixes(not_a_list) == frozenset()


def test_default_file_allows_gov_br() -> None:
    assert is_allowed("https://www.gov.br/pt-br/servicos")
