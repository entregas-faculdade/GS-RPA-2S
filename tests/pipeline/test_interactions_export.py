"""CSV de saída por execução e contagens do relatório: colunas, linhas, duplicados, proteção de célula e falhas."""

import csv
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from triage.pipeline import Deps, ProcessingResult, build_report, run_batch
from triage.pipeline import export as export_module
from triage.pipeline.export import EXPORT_COLUMNS, write_interactions_csv
from triage.pipeline.report import render_markdown
from triage.storage import (
    InteractionRecord,
    Repository,
    RequestRecord,
    StorageError,
    request_hash,
)

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"
NOW = datetime(2026, 11, 12, tzinfo=UTC)
CITIZEN_TEXT = "texto do pedido do cidadao que nao pode vazar"


def _csv_files(deps: Deps) -> list[Path]:
    return sorted((Path(deps.settings.output_dir) / "exports").glob("interactions-run-*.csv"))


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_a_batch_writes_one_row_per_processed_request_valid_and_rejected(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    report = run_batch(SAMPLES_DIR, deps)

    (path,) = _csv_files(deps)
    assert path.name == f"interactions-run-{report.run_id}.csv"
    rows = _read(path)
    created = report.totals["answered"] + report.totals["queued_for_review"] + report.totals["rejected"]
    assert len(rows) == created > 0
    assert list(rows[0]) == list(EXPORT_COLUMNS)
    rejected = [row for row in rows if row["status"] == "rejected"]
    assert rejected
    assert all(row["needs_human"] == "1" and row["topic_source"] == "none" and row["topic"] == "" for row in rejected)
    assert all(row["needs_human"] == "1" for row in rows if row["status"] == "queued_for_review")
    assert all(row["needs_human"] == "0" for row in rows if row["status"] == "answered")
    answered = next(row for row in rows if row["status"] == "answered")
    assert answered["topic_label"] and answered["response_text"].startswith(("Para", "Segunda", "O ", "Serviço", "Você"))


def test_the_second_run_creates_no_file_and_no_duplicate_rows(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()
    first = run_batch(SAMPLES_DIR, deps)

    second = run_batch(SAMPLES_DIR, deps)

    assert second.run_id != first.run_id
    assert [path.name for path in _csv_files(deps)] == [f"interactions-run-{first.run_id}.csv"]
    assert len(deps.repository.interactions()) == len(_read(_csv_files(deps)[0]))


def test_an_empty_run_creates_no_file(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps()
    empty = tmp_path / "vazia"
    empty.mkdir()

    run_batch(empty, deps)

    assert _csv_files(deps) == []


def _repository_with(tmp_path: Path, response: str, text: str = CITIZEN_TEXT) -> tuple[Repository, int]:
    repository = Repository(tmp_path / "x.db")
    digest = request_hash(text)
    repository.save_request(RequestRecord(digest, text, "answered"), anonymized=True)
    run_id = repository.start_run()
    record = InteractionRecord(digest, "llm", False, topic="tax", response_text=response, run_id=run_id)
    repository.save_interaction(record)
    return repository, run_id


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_a_dangerous_cell_is_neutralized(prefix: str, tmp_path: Path) -> None:
    repository, run_id = _repository_with(tmp_path, f"{prefix}HYPERLINK(\"x\")")

    path = write_interactions_csv(repository, run_id, tmp_path / "out")

    (row,) = _read(path)
    assert row["response_text"] == f"'{prefix}HYPERLINK(\"x\")"
    assert row["topic_label"] == "Impostos e tributos"


def test_a_normal_cell_is_untouched(tmp_path: Path) -> None:
    repository, run_id = _repository_with(tmp_path, "Acesse o portal.")

    (row,) = _read(write_interactions_csv(repository, run_id, tmp_path / "out"))

    assert row["response_text"] == "Acesse o portal."


def test_the_path_is_relative_to_the_output_not_to_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, run_id = _repository_with(tmp_path, "ok")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    path = write_interactions_csv(repository, run_id, tmp_path / "out")

    assert path == tmp_path / "out" / "exports" / f"interactions-run-{run_id}.csv"
    assert list(elsewhere.iterdir()) == []


def test_a_csv_write_failure_is_logged_and_does_not_break_the_run(
    make_deps: Callable[..., Deps], monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("sem permissão")

    monkeypatch.setattr(export_module, "_write", broken)
    deps = make_deps()

    report = run_batch(SAMPLES_DIR, deps)

    assert report.totals["answered"] > 0
    assert list((Path(deps.settings.output_dir) / "reports").glob("run-*.json"))
    assert "PermissionError" in caplog.text
    assert "sem permissão" not in caplog.text


def test_a_storage_failure_while_reading_for_the_csv_is_logged_only(
    make_deps: Callable[..., Deps], monkeypatch: pytest.MonkeyPatch
) -> None:
    deps = make_deps()

    def broken(*_args: object, **_kwargs: object) -> None:
        raise StorageError("falha")

    monkeypatch.setattr(deps.repository, "interactions", broken)

    assert run_batch(SAMPLES_DIR, deps).totals["answered"] > 0
    assert _csv_files(deps) == []


def _outcomes() -> list[ProcessingResult]:
    return [
        ProcessingResult("answered", topic="documents", topic_source="catalog"),
        ProcessingResult("answered", topic="tax", topic_source="llm"),
        ProcessingResult("queued_for_review", reason="urgent", topic="safety", topic_source="rule", needs_human=True),
        ProcessingResult("queued_for_review", reason="ambiguous", topic="other", topic_source="classifier", needs_human=True),
        ProcessingResult("rejected", reason="invalid_input", topic_source="none", needs_human=True),
        ProcessingResult("skipped_duplicate"),
    ]


def test_the_report_counts_by_topic_source_and_human_tag() -> None:
    report = build_report(1, NOW, NOW, _outcomes())

    assert report.by_topic == {"documents": 1, "other": 1, "safety": 1, "tax": 1}
    assert report.by_topic_source == {"catalog": 1, "classifier": 1, "llm": 1, "none": 1, "rule": 1}
    assert report.needs_human == {"total": 3, "urgent": 1}
    assert report.to_dict()["needs_human"] == {"total": 3, "urgent": 1}


def test_the_markdown_has_the_new_sections() -> None:
    markdown = render_markdown(build_report(1, NOW, NOW, _outcomes()))

    assert "## Por categoria da interação" in markdown
    assert "## Por origem da categoria" in markdown
    assert "## Interações que precisam de atendimento humano" in markdown
    assert "| urgent | 1 |" in markdown


def test_the_written_reports_carry_the_counts_and_no_request_text(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps()
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "pedido.txt").write_text("Meu CPF é 123.456.789-09. Quero a segunda via do RG, carteira de identidade.", encoding="utf-8")

    run_batch(folder, deps)

    json_path = next((Path(deps.settings.output_dir) / "reports").glob("run-*.json"))
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["by_topic"] and data["by_topic_source"] and data["needs_human"]["total"] == 0
    for text in (json_path.read_text(encoding="utf-8"), json_path.with_suffix(".md").read_text(encoding="utf-8")):
        assert "123.456.789-09" not in text
        assert "segunda via" not in text
