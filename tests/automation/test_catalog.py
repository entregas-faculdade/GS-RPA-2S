"""Catálogo v2: integridade do arquivo versionado e leitura tolerante a falhas."""

import csv
import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import CATALOG_PATH, approved_only, load_catalog

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


def _categorized_entries() -> list:
    return [entry for entry in load_catalog() if entry.category]


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
    entry = load_catalog(_write(tmp_path, [record]))[0]
    assert entry.links[0].url == "https://www.gov.br/inss"
    assert entry.phones[0].number == "135"
    assert entry.keywords == ("inss", "aposentadoria")


def test_category_may_be_null(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    assert load_catalog(_write(tmp_path, [make_record(category=None)]))[0].category is None


def test_channel_with_only_a_phone_is_valid(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    record = make_record(id="sp156", kind="channel", links=[], phones=[{"label": "156", "number": "156"}])
    assert [entry.id for entry in load_catalog(_write(tmp_path, [record]))] == ["sp156"]


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
        entries = load_catalog(path)
    assert [entry.id for entry in entries] == ["good"]
    assert caplog.records


@pytest.mark.parametrize("broken", [{"category": "incompleto"}, "texto"])
def test_incomplete_or_non_object_records_are_skipped(
    tmp_path: Path, make_record: Callable[..., dict], broken: object
) -> None:
    entries = load_catalog(_write(tmp_path, [broken, make_record(id="good")]))
    assert [entry.id for entry in entries] == ["good"]


def test_duplicate_id_keeps_the_first(tmp_path: Path, make_record: Callable[..., dict]) -> None:
    first = make_record(display_name="Primeiro")
    second = make_record(display_name="Segundo")
    entries = load_catalog(_write(tmp_path, [first, second]))
    assert [entry.display_name for entry in entries] == ["Primeiro"]


def test_missing_or_invalid_catalog_is_empty(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{nao é json", encoding="utf-8")
    not_a_list = tmp_path / "dict.json"
    not_a_list.write_text("{}", encoding="utf-8")
    assert load_catalog(tmp_path / "missing.json") == []
    assert load_catalog(broken) == []
    assert load_catalog(not_a_list) == []
