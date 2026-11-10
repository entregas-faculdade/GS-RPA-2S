"""Catálogo: integridade do arquivo versionado e leitura tolerante a falhas."""

import csv
import json
import re
from pathlib import Path

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import CATALOG_PATH, ServiceEntry, load_catalog

LABELED_CSV = Path("data") / "labeled" / "requests_labeled.csv"
OTHER_LABEL = "other"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _dataset_categories() -> set[str]:
    with LABELED_CSV.open(encoding="utf-8", newline="") as handle:
        return {row["label"] for row in csv.DictReader(handle)} - {OTHER_LABEL}


def test_catalog_covers_every_dataset_category_except_other() -> None:
    catalog = load_catalog()
    assert set(catalog) == _dataset_categories()
    assert len(catalog) == 8


def test_every_entry_is_complete_https_and_allowed() -> None:
    for entry in load_catalog().values():
        assert is_allowed(entry.url), entry.category
        assert entry.url.startswith("https://"), entry.category
        assert DATE_PATTERN.match(entry.verified_on), entry.category
        assert entry.source_note.strip() and entry.instructions.strip(), entry.category


def test_file_has_unique_categories() -> None:
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    categories = [record["category"] for record in records]
    assert len(categories) == len(set(categories))


def test_missing_or_invalid_catalog_is_empty(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{nao é json", encoding="utf-8")
    not_a_list = tmp_path / "dict.json"
    not_a_list.write_text("{}", encoding="utf-8")
    assert load_catalog(tmp_path / "missing.json") == {}
    assert load_catalog(broken) == {}
    assert load_catalog(not_a_list) == {}


def test_malformed_records_are_skipped(tmp_path: Path) -> None:
    good = {name: "x" for name in ServiceEntry.__dataclass_fields__}
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([good, {"category": "incompleto"}, "texto"]), encoding="utf-8")
    assert list(load_catalog(path)) == ["x"]
