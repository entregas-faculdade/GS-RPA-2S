"""Catálogo v2: integridade do arquivo versionado e leitura tolerante a falhas."""

import csv
import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import (
    CATALOG_PATH,
    MAX_CONTENT_LENGTH,
    ServiceEntry,
    approved_only,
    load_catalog,
)

LABELED_CSV = Path("data") / "labeled" / "requests_labeled.csv"
OTHER_LABEL = "other"
KEYWORDS_MIN, KEYWORDS_MAX = 5, 10


def _dataset_categories() -> set[str]:
    with LABELED_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["label"] for row in csv.DictReader(handle)} - {OTHER_LABEL}


def _write(tmp_path: Path, records: list) -> Path:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def _load(path: Path = CATALOG_PATH) -> list[ServiceEntry]:
    """Só o arquivo `path`: a pasta da base enriquecida não entra nos testes do catálogo versionado."""
    return load_catalog(path, extra_dir=None)


def _categorized_entries() -> list:
    return [entry for entry in _load() if entry.category]


def test_versioned_catalog_has_the_eight_approved_service_entries() -> None:
    entries = _categorized_entries()
    assert {entry.category for entry in entries} == _dataset_categories()
    assert len(entries) == 8
    assert all(entry.status == "approved" and entry.kind == "service" for entry in entries)
    assert approved_only(entries) == entries


def test_every_versioned_entry_is_complete_https_and_allowed() -> None:
    for entry in _categorized_entries():
        assert entry.links, entry.id
        assert all(is_allowed(link.url) for link in entry.links), entry.id
        assert KEYWORDS_MIN <= len(entry.keywords) <= KEYWORDS_MAX, entry.id
        assert entry.source_note.strip() and entry.instructions.strip(), entry.id


def test_versioned_catalog_has_unique_ids() -> None:
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ids = [record["id"] for record in records]
    assert len(ids) == len(set(ids))


def test_valid_record_is_loaded_with_links_and_phones(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    record = make_record(phones=[{"label": "Central", "number": "135"}])
    entry = _load(_write(tmp_path, [record]))[0]
    assert entry.links[0].url == "https://www.gov.br/inss"
    assert entry.phones[0].number == "135"
    assert entry.keywords == ("inss", "aposentadoria")


def test_category_may_be_null(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    assert _load(_write(tmp_path, [make_record(category=None)]))[0].category is None


def test_channel_with_only_a_phone_is_valid(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    record = make_record(id="sp156", kind="channel", links=[], phones=[{"label": "156", "number": "156"}])
    assert [entry.id for entry in _load(_write(tmp_path, [record]))] == ["sp156"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "service", "links": []},
        {"kind": "portal", "links": [], "phones": []},
        {"kind": "outro"},
        {"status": "draft"},
        {"keywords": "inss"},
        {"links": [{"label": "sem url"}]},
        {"verified_on": "ontem"},
        {"id": ""},
    ],
)
def test_invalid_records_are_skipped_with_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, make_record: Callable[..., dict], overrides: dict
) -> None:
    path = _write(tmp_path, [make_record(**overrides), make_record(id="good")])
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        entries = _load(path)
    assert [entry.id for entry in entries] == ["good"]
    assert caplog.records


def test_link_manual_check_date_is_loaded_and_optional(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    links = [{"label": "A", "url": "https://www.gov.br/a", "manual_check_on": "2026-11-10"}, {"label": "B", "url": "https://www.gov.br/b"}]
    entry = _load(_write(tmp_path, [make_record(links=links)]))[0]
    assert [link.manual_check_on for link in entry.links] == ["2026-11-10", None]


@pytest.mark.parametrize("bad_date", ["ontem", "2026-13-40", "", 20261110, None])
def test_invalid_manual_check_date_invalidates_the_record(
    tmp_path: Path, make_record: Callable[..., dict], bad_date: object
) -> None:
    links = [{"label": "A", "url": "https://www.gov.br/a", "manual_check_on": bad_date}]
    path = _write(tmp_path, [make_record(links=links), make_record(id="good")])
    assert [entry.id for entry in _load(path)] == ["good"]


@pytest.mark.parametrize("broken", [{"category": "incompleto"}, "texto"])
def test_incomplete_or_non_object_records_are_skipped(
    tmp_path: Path, make_record: Callable[..., dict], broken: object
) -> None:
    entries = _load(_write(tmp_path, [broken, make_record(id="good")]))
    assert [entry.id for entry in entries] == ["good"]


def test_duplicate_id_keeps_the_first(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    first = make_record(display_name="Primeiro")
    second = make_record(display_name="Segundo")
    entries = _load(_write(tmp_path, [first, second]))
    assert [entry.display_name for entry in entries] == ["Primeiro"]


def test_missing_or_invalid_catalog_is_empty(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{nao é json", encoding="utf-8")
    not_a_list = tmp_path / "dict.json"
    not_a_list.write_text("{}", encoding="utf-8")
    assert _load(tmp_path / "missing.json") == []
    assert _load(broken) == []
    assert _load(not_a_list) == []


def test_content_defaults_to_empty_and_is_loaded_when_present(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    without, with_content = _load(_write(tmp_path, [make_record(), make_record(id="b", content="Prazo de 30 dias.")]))
    assert without.content == ""
    assert with_content.content == "Prazo de 30 dias."


def test_content_at_the_limit_is_valid_and_above_it_is_rejected_with_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, make_record: Callable[..., dict]
) -> None:
    records = [make_record(id="at", content="a" * MAX_CONTENT_LENGTH), make_record(id="over", content="a" * (MAX_CONTENT_LENGTH + 1))]
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        entries = _load(_write(tmp_path, records))
    assert [entry.id for entry in entries] == ["at"]
    assert "content" in caplog.text


@pytest.mark.parametrize("content", ["", "   ", " \t ", None, 3000, ["texto"]])
def test_present_content_must_be_non_blank_text(tmp_path: Path, make_record: Callable[..., dict], content: object) -> None:
    path = _write(tmp_path, [make_record(content=content), make_record(id="good")])
    assert [entry.id for entry in _load(path)] == ["good"]


def _write_extra(directory: Path, name: str, records: list) -> None:
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(json.dumps(records), encoding="utf-8")


def test_extra_files_are_read_after_the_catalog_in_name_order(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    main = _write(tmp_path, [make_record(id="main")])
    extra = tmp_path / "catalog.d"
    _write_extra(extra, "b.json", [make_record(id="from_b")])
    _write_extra(extra, "a.json", [make_record(id="from_a1"), make_record(id="from_a2")])
    (extra / "README.md").write_text("não é json", encoding="utf-8")
    assert [entry.id for entry in load_catalog(main, extra)] == ["main", "from_a1", "from_a2", "from_b"]


def test_duplicate_id_across_files_keeps_the_first(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, make_record: Callable[..., dict]
) -> None:
    main = _write(tmp_path, [make_record(display_name="Do catálogo")])
    extra = tmp_path / "catalog.d"
    _write_extra(extra, "a.json", [make_record(display_name="Da base"), make_record(id="novo")])
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        entries = load_catalog(main, extra)
    assert [(entry.id, entry.display_name) for entry in entries] == [("social_security", "Do catálogo"), ("novo", "Aposentadoria (INSS)")]
    assert "id repetido" in caplog.text


def test_a_broken_extra_file_is_logged_and_does_not_drop_the_others(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, make_record: Callable[..., dict]
) -> None:
    main = _write(tmp_path, [make_record(id="main")])
    extra = tmp_path / "catalog.d"
    extra.mkdir()
    (extra / "a.json").write_text("{nao é json", encoding="utf-8")
    (extra / "b.json").write_text("{}", encoding="utf-8")
    _write_extra(extra, "c.json", [make_record(id="from_c")])
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        entries = load_catalog(main, extra)
    assert [entry.id for entry in entries] == ["main", "from_c"]
    assert "a.json" in caplog.text and "b.json" in caplog.text


def test_missing_or_empty_extra_dir_is_not_an_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, make_record: Callable[..., dict]
) -> None:
    main = _write(tmp_path, [make_record(id="main")])
    empty = tmp_path / "vazia"
    empty.mkdir()
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        assert [entry.id for entry in load_catalog(main, tmp_path / "ausente")] == ["main"]
        assert [entry.id for entry in load_catalog(main, empty)] == ["main"]
    assert not caplog.records


def test_extra_files_load_even_when_the_main_catalog_is_missing(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    extra = tmp_path / "catalog.d"
    _write_extra(extra, "a.json", [make_record(id="from_a")])
    assert [entry.id for entry in load_catalog(tmp_path / "missing.json", extra)] == ["from_a"]


def test_versioned_extra_dir_has_only_the_imported_spreadsheet_base() -> None:
    assert [file.name for file in Path("data", "catalog.d").glob("*.json")] == ["sp_expanded.json"]
