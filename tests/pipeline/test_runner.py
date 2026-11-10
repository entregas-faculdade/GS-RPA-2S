"""`run_batch`: ponta a ponta, idempotência, isolamento de falha e relatório sem PII."""

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

from triage.classification import Classification
from triage.pipeline import Deps, processor, run_batch

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

PII_REQUEST = "Meu CPF é 123.456.789-09 e o e-mail é fulano@example.com. Quero a segunda via do RG, carteira de identidade."
GOOD_REQUEST = "Preciso saber como emitir a segunda via do meu RG, a carteira de identidade."
BROKEN_MARKER = "QUEBRAR"


def _write_inputs(folder: Path) -> Path:
    folder.mkdir()
    (folder / "bom.txt").write_text(GOOD_REQUEST, encoding="utf-8")
    (folder / "pii.txt").write_text(PII_REQUEST, encoding="utf-8")
    (folder / "quebrado.txt").write_text(f"{BROKEN_MARKER} pedido sobre o título de eleitor", encoding="utf-8")
    (folder / "vazio.txt").write_text("", encoding="utf-8")
    return folder


def _reports(deps: Deps) -> list[Path]:
    return sorted((Path(deps.settings.output_dir) / "reports").glob("run-*.json"))


def _runs(deps: Deps) -> list[tuple]:
    with sqlite3.connect(deps.repository._path) as connection:
        return connection.execute("SELECT id, finished_at, totals_json FROM runs").fetchall()


def test_end_to_end_over_samples_answers_rejects_and_writes_report(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    report = run_batch(SAMPLES_DIR, deps)

    assert report.totals["answered"] > 0
    assert report.totals["rejected"] > 0
    assert report.totals["error"] == 0
    json_report, markdown_report = _reports(deps)[0], _reports(deps)[0].with_suffix(".md")
    assert json.loads(json_report.read_text(encoding="utf-8"))["totals"] == report.totals
    assert markdown_report.is_file()


def test_second_run_processes_nothing_new(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()
    first = run_batch(SAMPLES_DIR, deps)

    second = run_batch(SAMPLES_DIR, deps)

    processed_first = sum(first.totals.values())
    assert second.totals["skipped_duplicate"] == processed_first
    assert second.totals["answered"] == second.totals["queued_for_review"] == second.totals["rejected"] == 0


def test_one_failing_request_does_not_stop_the_others(
    make_deps: Callable[..., Deps], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deps = make_deps()
    original = processor.classify

    def explode_on_marker(text: str, model: Pipeline) -> Classification:
        if BROKEN_MARKER.lower() in text.lower():
            raise RuntimeError("falha injetada")
        return original(text, model)

    monkeypatch.setattr(processor, "classify", explode_on_marker)

    report = run_batch(_write_inputs(tmp_path / "in"), deps)

    assert report.totals["error"] == 1
    assert report.totals["answered"] == 2
    assert report.totals["rejected"] == 1
    reasons = sorted(item.reason for item in deps.repository.pending_reviews())
    assert reasons == ["invalid_input", "low_confidence"]


def test_run_is_closed_even_when_reading_the_folder_fails(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps()

    with pytest.raises(FileNotFoundError):
        run_batch(tmp_path / "nao-existe", deps)

    ((_run_id, finished_at, totals_json),) = _runs(deps)
    assert finished_at is not None
    assert json.loads(totals_json)["answered"] == 0
    assert len(_reports(deps)) == 1


def test_missing_model_queues_every_request(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps(model=None)

    report = run_batch(_write_inputs(tmp_path / "in"), deps)

    assert report.totals["answered"] == 0
    assert report.by_review_reason == {"invalid_input": 1, "low_confidence": 3}


def test_unavailable_link_is_reported(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps(link_ok=False)

    report = run_batch(_write_inputs(tmp_path / "in"), deps)

    assert report.by_review_reason.get("link_unavailable", 0) >= 1
    assert report.links["unavailable"] >= 1


def test_report_has_no_request_text_or_pii(make_deps: Callable[..., Deps], tmp_path: Path) -> None:
    deps = make_deps()

    run_batch(_write_inputs(tmp_path / "in"), deps)

    json_path = _reports(deps)[0]
    published = json_path.read_text(encoding="utf-8") + json_path.with_suffix(".md").read_text(encoding="utf-8")
    log_text = (Path(deps.settings.output_dir) / "logs" / "run.log")
    for forbidden in ("123.456.789-09", "fulano@example.com", "segunda via", BROKEN_MARKER, "título de eleitor"):
        assert forbidden not in published
        assert not log_text.exists() or forbidden not in log_text.read_text(encoding="utf-8")
