"""`AppService`: envio, fila de revisão, resolução e feedback, sem a camada de tela."""

import sqlite3

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
