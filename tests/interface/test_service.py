"""`AppService`: envio, fila de revisão, resolução e feedback, sem a camada de tela."""

import csv
import sqlite3
from pathlib import Path

import pytest

from triage.interface.service import (
    KIND_ANSWERED,
    KIND_DUPLICATE,
    KIND_HUMAN_REVIEW,
    KIND_INVALID,
    AppService,
)
from triage.storage import Repository

RG_TEXT = "Preciso saber como emitir a segunda via do meu RG. Nunca fiz esse pedido antes."
URGENT_TEXT = "Meu benefício foi cortado e preciso de ajuda urgente hoje."
PII_URGENT_TEXT = "Meu CPF é 123.456.789-09 e meu benefício foi cortado, preciso de ajuda urgente hoje."


def _count(repository: Repository, table: str) -> int:
    with sqlite3.connect(repository._path) as connection:  # leitura direta só para conferir o que foi gravado
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_answered_request_returns_response_and_hash(service: AppService) -> None:
    outcome = service.submit(RG_TEXT)

    assert outcome.kind == KIND_ANSWERED
    assert "https://" in outcome.message
    assert outcome.request_hash is not None


def test_request_for_review_hides_technical_reason(service: AppService) -> None:
    outcome = service.submit(URGENT_TEXT)

    assert outcome.kind == KIND_HUMAN_REVIEW
    assert "atendimento humano" in outcome.message
    assert "urgent" not in outcome.message
    assert outcome.request_hash is None
    assert [entry.reason for entry in service.pending_reviews()] == ["urgent"]


@pytest.mark.parametrize("text", ["", "   ", "ab", "<script>alert(1)</script>"])
def test_empty_or_invalid_input_returns_friendly_message(service: AppService, repository: Repository, text: str) -> None:
    outcome = service.submit(text)

    assert outcome.kind == KIND_INVALID
    assert _count(repository, "requests") == 0


def test_oversized_input_returns_friendly_message(service: AppService) -> None:
    assert service.submit("a" * 5000).kind == KIND_INVALID


def test_repeated_request_gets_neutral_message_without_feedback(service: AppService) -> None:
    service.submit(RG_TEXT)

    outcome = service.submit(RG_TEXT)

    assert outcome.kind == KIND_DUPLICATE
    assert outcome.message == "Este pedido já foi registrado."
    assert outcome.request_hash is None


def test_feedback_is_recorded_once_per_request(service: AppService, repository: Repository) -> None:
    request_hash = service.submit(RG_TEXT).request_hash

    assert service.send_feedback(request_hash, "up") is True
    assert service.send_feedback(request_hash, "down") is False
    assert _count(repository, "feedback") == 1


def test_invalid_rating_is_ignored(service: AppService, repository: Repository) -> None:
    request_hash = service.submit(RG_TEXT).request_hash

    assert service.send_feedback(request_hash, "talvez") is False
    assert _count(repository, "feedback") == 0


def test_feedback_for_unknown_request_is_ignored(service: AppService) -> None:
    assert service.send_feedback("hash-inexistente", "up") is False


def test_review_entry_shows_anonymized_text(service: AppService) -> None:
    service.submit(PII_URGENT_TEXT)

    [entry] = service.pending_reviews()

    assert "[CPF]" in entry.anonymized_text
    assert "123.456.789-09" not in entry.anonymized_text
    assert entry.reason == "urgent"


def test_resolve_removes_item_from_pending(service: AppService) -> None:
    service.submit(URGENT_TEXT)
    [entry] = service.pending_reviews()

    assert service.resolve(entry.id, "  encaminhado ao órgão  ") is True
    assert service.pending_reviews() == []
    assert service.resolve(entry.id, "de novo") is False


def test_pipeline_failure_becomes_error_outcome(service: AppService, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("triage.interface.service.process_request", broken)

    outcome = service.submit(RG_TEXT)

    assert outcome.kind == "error"
    assert "Tente novamente" in outcome.message


def _queue_pii_request(service: AppService) -> int:
    service.submit(PII_URGENT_TEXT)
    return service.pending_reviews()[0].id


def test_label_options_are_the_nine_categories(service: AppService) -> None:
    options = service.label_options()

    assert len(options) == 9
    assert "other" in options
    assert "id_card" in options


def test_resolve_with_valid_category_records_label(service: AppService, repository: Repository) -> None:
    review_id = _queue_pii_request(service)

    assert service.resolve(review_id, "ok", "social_benefits") is True
    assert service.pending_reviews() == []
    assert [item.category for item in repository.labeled_requests()] == ["social_benefits"]


def test_resolve_with_invalid_category_does_not_resolve(service: AppService, repository: Repository) -> None:
    review_id = _queue_pii_request(service)

    assert service.resolve(review_id, "ok", "categoria_inventada") is False
    assert len(service.pending_reviews()) == 1
    assert repository.labeled_requests() == []


def test_resolve_without_category_keeps_old_flow(service: AppService, repository: Repository) -> None:
    review_id = _queue_pii_request(service)

    assert service.resolve(review_id, "ok") is True
    assert repository.labeled_requests() == []


def test_resolve_unknown_review_with_category_returns_false(service: AppService) -> None:
    assert service.resolve(9999, "ok", "other") is False


def test_export_without_labels_returns_none(service: AppService, tmp_path: Path) -> None:
    assert service.export_labeled(tmp_path / "exports") is None


def test_export_writes_only_anonymized_text_in_labeled_format(service: AppService, tmp_path: Path) -> None:
    review_id = _queue_pii_request(service)
    service.resolve(review_id, "ok", "social_benefits")
    [labeled] = service._deps.repository.labeled_requests()

    path = service.export_labeled(tmp_path / "novo" / "exports")

    assert path is not None and path.name.startswith("labeled_") and path.suffix == ".csv"
    content = path.read_text(encoding="utf-8")
    assert "123.456.789-09" not in content
    assert labeled.request_hash not in content
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["id", "text", "label", "split", "urgent"]
    [row] = rows[1:]
    assert row[1:] == [labeled.anonymized_text, "social_benefits", "train", "1"]
    assert row[0].startswith("R") and labeled.request_hash.startswith(row[0][1:])


def test_export_header_matches_labeled_dataset() -> None:
    labeled_csv = Path(__file__).resolve().parents[2] / "data" / "labeled" / "requests_labeled.csv"
    header = labeled_csv.read_text(encoding="utf-8").splitlines()[0]

    assert header.split(",") == ["id", "text", "label", "split", "urgent"]
