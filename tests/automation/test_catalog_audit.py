"""Verificador do catálogo: esquema, allowlist, links, telefones e idade, tudo com stubs (sem rede)."""

import importlib.util
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from triage.automation import catalog_audit
from triage.automation.catalog import MAX_CONTENT_LENGTH
from triage.automation.catalog_audit import (
    AuditOptions,
    Check,
    audit_catalog,
    audit_catalog_files,
    has_errors,
)
from triage.automation.link_check import LinkStatus

SUFFIXES = frozenset({"gov.br"})
GOOD_URL = "https://www.gov.br/inss"
TODAY = date(2026, 11, 10)
SCRIPT = Path("scripts") / "verify_catalog.py"


def _checker(dead: frozenset[str] = frozenset()) -> Callable[[str], LinkStatus]:
    def check(url: str) -> LinkStatus:
        return LinkStatus(False, None, "Timeout") if url in dead else LinkStatus(True, 200, None)

    return check


def _options(pages: dict[str, str | None] | None = None, **overrides: object) -> AuditOptions:
    values: dict = {
        "link_checker": _checker(),
        "fetch_page_text": lambda url: (pages or {}).get(url),
        "today": TODAY,
    }
    return AuditOptions(**{**values, **overrides})


BLOCKED_URL = "https://www.prefeitura.gov.br/bloqueada"


def _blocked_checker(url: str) -> LinkStatus:
    return LinkStatus(False, 403, "HTTP 403") if url == BLOCKED_URL else LinkStatus(True, 200, None)


def _blocked_record(make_record: Callable[..., dict], manual_check_on: str | None, **overrides: object) -> dict:
    link: dict = {"label": "Bloqueada", "url": BLOCKED_URL}
    if manual_check_on is not None:
        link["manual_check_on"] = manual_check_on
    return make_record(links=[link], **overrides)


def _find(checks: list[Check], name: str) -> list[Check]:
    return [check for check in checks if check.name == name]


def test_valid_catalog_has_no_error(make_record: Callable[..., dict]) -> None:
    checks = audit_catalog([make_record()], SUFFIXES, _options())
    assert not has_errors(checks)
    assert {check.level for check in checks} == {"ok"}


def test_phone_found_in_page_is_confirmed(make_record: Callable[..., dict]) -> None:
    record = make_record(phones=[{"label": "Central", "number": "0800 61 61 61"}])
    pages = {GOOD_URL: "<p>Ligue 0800 61 61 61 e fale conosco</p>"}
    phone = _find(audit_catalog([record], SUFFIXES, _options(pages)), "phone")[0]
    assert (phone.level, "confirmado" in phone.detail, "não" in phone.detail) == ("ok", True, False)


def test_phone_missing_from_page_is_only_a_warning(make_record: Callable[..., dict]) -> None:
    record = make_record(phones=[{"label": "Central", "number": "135"}])
    checks = audit_catalog([record], SUFFIXES, _options({GOOD_URL: "Ligue 1350 hoje"}))
    phone = _find(checks, "phone")[0]
    assert (phone.level, "não confirmado" in phone.detail) == ("warning", True)
    assert not has_errors(checks)


def test_phone_with_unreachable_page_is_not_confirmed(make_record: Callable[..., dict]) -> None:
    record = make_record(phones=[{"label": "Central", "number": "135"}])
    checks = audit_catalog([record], SUFFIXES, _options({GOOD_URL: None}))
    assert _find(checks, "phone")[0].level == "warning"


def test_link_outside_allowlist_is_an_error(make_record: Callable[..., dict]) -> None:
    record = make_record(links=[{"label": "Falso", "url": "https://gov.br.evil.com"}])
    checks = audit_catalog([record], SUFFIXES, _options())
    assert _find(checks, "allowlist")[0].level == "error"
    assert has_errors(checks)


def test_approved_entry_without_live_link_is_an_error(make_record: Callable[..., dict]) -> None:
    checks = audit_catalog([make_record()], SUFFIXES, _options(link_checker=_checker(frozenset({GOOD_URL}))))
    assert _find(checks, "links")[0].level == "error"


def test_candidate_entry_without_live_link_is_only_a_warning(make_record: Callable[..., dict]) -> None:
    record = make_record(status="candidate")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_checker(frozenset({GOOD_URL}))))
    assert _find(checks, "links")[0].level == "warning"
    assert not has_errors(checks)


def test_some_dead_links_are_a_warning(make_record: Callable[..., dict]) -> None:
    dead = "https://www.gov.br/morto"
    record = make_record(links=[{"label": "Vivo", "url": GOOD_URL}, {"label": "Morto", "url": dead}])
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_checker(frozenset({dead}))))
    assert _find(checks, "links")[0].level == "warning"
    assert not has_errors(checks)


def test_blocked_link_with_valid_manual_check_is_a_warning_with_the_date(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, "2026-11-01")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_blocked_checker))
    link = _find(checks, "link")[0]
    assert (link.level, "2026-11-01" in link.detail, "atestado manual" in link.detail) == ("warning", True, True)
    assert not _find(checks, "links")
    assert not has_errors(checks)


def test_blocked_link_with_expired_manual_check_is_a_warning_and_leaves_an_approved_entry_without_link(
    make_record: Callable[..., dict],
) -> None:
    record = _blocked_record(make_record, "2026-01-01")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_blocked_checker))
    link = _find(checks, "link")[0]
    assert (link.level, "vencido" in link.detail) == ("warning", True)
    assert _find(checks, "links")[0].level == "error"


def test_expired_manual_check_of_a_candidate_never_errors(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, "2026-01-01", status="candidate")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_blocked_checker))
    assert _find(checks, "link")[0].level == "warning"
    assert not has_errors(checks)


def test_manual_check_uses_the_max_age_option(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, "2026-01-01")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_blocked_checker, max_age_days=365))
    assert "vencido" not in _find(checks, "link")[0].detail
    assert not has_errors(checks)


def test_blocked_link_without_manual_check_is_a_plain_warning(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, None, status="candidate")
    link = _find(audit_catalog([record], SUFFIXES, _options(link_checker=_blocked_checker)), "link")[0]
    assert (link.level, link.detail.endswith("HTTP 403")) == ("warning", True)


def test_manual_check_is_ignored_for_failures_other_than_403(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, "2026-11-01")
    checks = audit_catalog([record], SUFFIXES, _options(link_checker=_checker(frozenset({BLOCKED_URL}))))
    assert "atestado" not in _find(checks, "link")[0].detail
    assert _find(checks, "links")[0].level == "error"


def test_manually_checked_link_does_not_confirm_phones(make_record: Callable[..., dict]) -> None:
    record = _blocked_record(make_record, "2026-11-01", phones=[{"label": "Central", "number": "156"}])
    pages = {BLOCKED_URL: "Ligue 156"}
    phone = _find(audit_catalog([record], SUFFIXES, _options(pages, link_checker=_blocked_checker)), "phone")[0]
    assert (phone.level, "não confirmado" in phone.detail) == ("warning", True)


def test_fetch_page_text_sends_the_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict = {}

    def fake_get(_url: str, **kwargs: object) -> object:
        sent.update(kwargs)
        raise catalog_audit.requests.ConnectionError("fora do ar")

    monkeypatch.setattr(catalog_audit.requests, "get", fake_get)
    catalog_audit.fetch_page_text(GOOD_URL, "Robo-Teste/1.0")
    assert sent["headers"] == {"User-Agent": "Robo-Teste/1.0"}


def test_schema_error_and_duplicate_id_are_errors(make_record: Callable[..., dict]) -> None:
    records = [make_record(kind="outro"), make_record(), make_record()]
    checks = audit_catalog(records, SUFFIXES, _options())
    assert [check.level for check in _find(checks, "schema")] == ["error", "ok"]
    assert _find(checks, "id")[0].level == "error"


def test_old_verification_date_is_a_warning(make_record: Callable[..., dict]) -> None:
    record = make_record(verified_on="2026-01-01")
    checks = audit_catalog([record], SUFFIXES, _options())
    assert _find(checks, "verified_on")[0].level == "warning"
    assert _find(audit_catalog([record], SUFFIXES, _options(max_age_days=365)), "verified_on")[0].level == "ok"


def test_offline_skips_network(make_record: Callable[..., dict]) -> None:
    def forbidden(_url: str) -> object:
        raise AssertionError("rede não deveria ser usada")

    record = make_record(phones=[{"label": "Central", "number": "135"}])
    options = _options(link_checker=forbidden, fetch_page_text=forbidden, offline=True)
    checks = audit_catalog([record], SUFFIXES, options)
    assert not has_errors(checks)
    assert not _find(checks, "link") and not _find(checks, "phone")


def test_fetch_page_text_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise catalog_audit.requests.ConnectionError("fora do ar")

    monkeypatch.setattr(catalog_audit.requests, "get", boom)
    assert catalog_audit.fetch_page_text(GOOD_URL) is None


def _load_script() -> object:
    spec = importlib.util.spec_from_file_location("verify_catalog_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_offline_exits_zero_on_versioned_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    assert _load_script().main(["--offline", "--max-age-days", "100000"]) == 0
    assert "sem erro" in capsys.readouterr().out


def test_script_exits_one_on_error_and_does_not_touch_the_file(
    tmp_path: Path, make_record: Callable[..., dict]
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([make_record(kind="outro")]), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert _load_script().main(["--offline", "--catalog", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == before


def test_script_exits_one_when_catalog_is_missing(tmp_path: Path) -> None:
    assert _load_script().main(["--offline", "--catalog", str(tmp_path / "nada.json")]) == 1


def test_content_over_the_limit_or_blank_is_a_schema_error_pointing_at_the_file(make_record: Callable[..., dict]) -> None:
    files = [
        ("a.json", [make_record(id="long", content="a" * (MAX_CONTENT_LENGTH + 1))]),
        ("b.json", [make_record(id="blank", content="  "), make_record(id="fine", content="Trecho oficial.")]),
    ]
    checks = audit_catalog_files(files, SUFFIXES, _options())
    errors = [check for check in checks if check.level == "error"]
    assert [(check.entry_id, check.source) for check in errors] == [("long", "a.json"), ("blank", "b.json")]
    assert "content" in errors[0].detail and str(MAX_CONTENT_LENGTH) in errors[0].detail
    assert "content" in errors[1].detail
    assert {check.source for check in checks if check.entry_id == "fine"} == {"b.json"}


def test_duplicate_id_across_files_is_an_error_in_the_second_file(make_record: Callable[..., dict]) -> None:
    files = [("catalog.json", [make_record()]), ("catalog.d/a.json", [make_record(), make_record(id="novo")])]
    checks = audit_catalog_files(files, SUFFIXES, _options())
    duplicated = _find(checks, "id")
    assert [(check.level, check.source) for check in duplicated] == [("error", "catalog.d/a.json")]
    assert [check.source for check in _find(checks, "schema") if check.entry_id == "novo"] == ["catalog.d/a.json"]


def test_a_dead_approved_link_in_an_extra_file_is_an_error_with_its_file(make_record: Callable[..., dict]) -> None:
    record = make_record(id="detailed", content="Trecho.")
    options = _options(link_checker=_checker(frozenset({GOOD_URL})))
    checks = audit_catalog_files([("catalog.d/a.json", [record])], SUFFIXES, options)
    errors = [check for check in checks if check.level == "error"]
    assert [(check.name, check.source) for check in errors] == [("links", "catalog.d/a.json")]


def test_audit_catalog_without_a_file_name_keeps_the_source_empty(make_record: Callable[..., dict]) -> None:
    assert {check.source for check in audit_catalog([make_record()], SUFFIXES, _options())} == {""}


def _write_catalog(path: Path, records: list) -> Path:
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_script_reads_the_extra_dir_and_points_at_the_file_of_each_error(
    tmp_path: Path, make_record: Callable[..., dict], capsys: pytest.CaptureFixture[str]
) -> None:
    main = _write_catalog(tmp_path / "catalog.json", [make_record()])
    extra = tmp_path / "catalog.d"
    extra.mkdir()
    _write_catalog(extra / "a.json", [make_record(id="ok_extra", content="Trecho oficial.")])
    _write_catalog(extra / "b.json", [make_record(id="longo", content="a" * (MAX_CONTENT_LENGTH + 1))])
    code = _load_script().main(["--offline", "--catalog", str(main), "--catalog-dir", str(extra)])
    out = capsys.readouterr().out
    assert code == 1
    assert "ERRO  longo [schema]" in out and str(extra / "b.json") in out
    assert "3 registro(s) verificado(s); com erro." in out


def test_script_is_green_when_the_extra_dir_has_only_valid_records(
    tmp_path: Path, make_record: Callable[..., dict], capsys: pytest.CaptureFixture[str]
) -> None:
    main = _write_catalog(tmp_path / "catalog.json", [make_record()])
    extra = tmp_path / "catalog.d"
    extra.mkdir()
    _write_catalog(extra / "a.json", [make_record(id="ok_extra", content="Trecho oficial.")])
    (extra / "README.md").write_text("ignorado", encoding="utf-8")
    assert _load_script().main(["--offline", "--catalog", str(main), "--catalog-dir", str(extra)]) == 0
    assert "2 registro(s) verificado(s); sem erro." in capsys.readouterr().out


def test_script_reports_an_unreadable_extra_file_and_still_audits_the_others(
    tmp_path: Path, make_record: Callable[..., dict], capsys: pytest.CaptureFixture[str]
) -> None:
    main = _write_catalog(tmp_path / "catalog.json", [make_record()])
    extra = tmp_path / "catalog.d"
    extra.mkdir()
    (extra / "a.json").write_text("{nao é json", encoding="utf-8")
    _write_catalog(extra / "b.json", [make_record(id="ok_extra")])
    assert _load_script().main(["--offline", "--catalog", str(main), "--catalog-dir", str(extra)]) == 1
    out = capsys.readouterr().out
    assert "[file]" in out and str(extra / "a.json") in out
    assert "ok_extra [schema]" in out


def test_script_with_a_missing_extra_dir_audits_only_the_catalog(
    tmp_path: Path, make_record: Callable[..., dict], capsys: pytest.CaptureFixture[str]
) -> None:
    main = _write_catalog(tmp_path / "catalog.json", [make_record()])
    assert _load_script().main(["--offline", "--catalog", str(main), "--catalog-dir", str(tmp_path / "nada")]) == 0
    assert "1 registro(s) verificado(s); sem erro." in capsys.readouterr().out
