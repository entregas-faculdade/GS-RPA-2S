"""`process_request`: ordem das etapas, caminhos de revisão e privacidade do que é gravado."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from triage.automation.llm_client import LlmUnavailable
from triage.ingestion import Rejection, Request
from triage.pipeline import Deps, process_request
from triage.pipeline.processor import process_rejection, route_to_safe_review
from triage.storage import RequestRecord, StorageError

RG_TEXT = "Preciso saber como emitir a segunda via do meu RG. Nunca fiz esse pedido antes."
PII_TEXT = "Meu CPF é 123.456.789-09, e-mail fulano@example.com. Quero a segunda via do RG, carteira de identidade."


def _request(text: str = RG_TEXT, request_id: str = "r1") -> Request:
    return Request(request_id, text, f"{request_id}.txt")


def _rows(deps: Deps, query: str) -> list[tuple]:
    with sqlite3.connect(deps.repository._path) as connection:  # leitura direta só para conferir o que foi gravado
        return connection.execute(query).fetchall()


def test_confident_request_is_answered_with_official_link(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    result = process_request(_request(), deps)

    assert result.status == "answered"
    assert result.category == "id_card"
    assert "https://" in result.response_text
    assert result.link_status == "ok"
    assert deps.repository.pending_reviews() == []


def test_second_call_with_same_text_is_skipped(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()
    process_request(_request(), deps)

    result = process_request(_request(request_id="outro-id"), deps)

    assert result.status == "skipped_duplicate"
    assert _rows(deps, "SELECT COUNT(*) FROM requests") == [(1,)]


def test_urgent_request_goes_to_review(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    result = process_request(_request("Meu benefício foi cortado e preciso de ajuda urgente hoje."), deps)

    assert result.status == "queued_for_review"
    assert result.reason == "urgent"
    assert [item.reason for item in deps.repository.pending_reviews()] == ["urgent"]


def test_missing_model_sends_everything_to_review(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps(model=None)

    result = process_request(_request(), deps)

    assert (result.status, result.reason) == ("queued_for_review", "low_confidence")


def test_unavailable_link_goes_to_review_with_that_reason(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps(link_ok=False)

    result = process_request(_request(), deps)

    assert (result.status, result.reason, result.link_status) == ("queued_for_review", "link_unavailable", "unavailable")
    assert [item.reason for item in deps.repository.pending_reviews()] == ["link_unavailable"]


def test_failing_llm_falls_back_to_template(make_deps: Callable[..., Deps]) -> None:
    class BrokenClient:
        def rewrite(self, prompt: str) -> str:
            raise LlmUnavailable("Timeout")

    deps = make_deps(llm_client=BrokenClient())

    result = process_request(_request(), deps)

    assert result.status == "answered"
    assert (result.used_llm, result.fallback_reason) == (False, "llm_unavailable")
    assert "https://" in result.response_text


def test_only_anonymized_text_is_stored(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    process_request(_request(PII_TEXT), deps)

    stored = _rows(deps, "SELECT anonymized_text FROM requests")[0][0]
    assert "123.456.789-09" not in stored
    assert "fulano@example.com" not in stored


def test_transient_storage_failure_is_retried(make_deps: Callable[..., Deps], monkeypatch: pytest.MonkeyPatch) -> None:
    deps = make_deps()
    original = deps.repository.save_request
    calls = {"count": 0}

    def flaky(record: RequestRecord, *, anonymized: bool) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise StorageError("banco ocupado")
        original(record, anonymized=anonymized)

    monkeypatch.setattr(deps.repository, "save_request", flaky)

    result = process_request(_request(), deps)

    assert result.status == "answered"
    assert calls["count"] == 2


def test_rejection_is_recorded_once_and_queued_as_invalid_input(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()
    rejection = Rejection("vazio.txt", "empty_file")

    first = process_rejection(rejection, deps)
    second = process_rejection(rejection, deps)

    assert (first.status, first.reason) == ("rejected", "invalid_input")
    assert second.status == "skipped_duplicate"
    assert [item.reason for item in deps.repository.pending_reviews()] == ["invalid_input"]


def test_safe_review_does_not_duplicate(make_deps: Callable[..., Deps]) -> None:
    deps = make_deps()

    route_to_safe_review(_request(), deps)
    route_to_safe_review(_request(), deps)

    assert [item.reason for item in deps.repository.pending_reviews()] == ["low_confidence"]


def test_database_path_is_only_touched_by_repository(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "triage" / "pipeline"
    assert not any("sqlite3" in path.read_text(encoding="utf-8") for path in source.glob("*.py"))
