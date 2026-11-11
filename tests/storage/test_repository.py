import json
import logging
import sqlite3
from pathlib import Path

import pytest

from triage.storage import Repository, RequestRecord, StorageError, init_db, request_hash

TABLES = {"requests", "review_queue", "feedback", "labels", "runs"}


def _record(text: str = "meu pedido anonimizado", status: str = "answered") -> RequestRecord:
    return RequestRecord(request_hash(text), text, status, category="saude", confidence=0.9)


def _query(db_path: Path, sql: str) -> list[tuple]:
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "triage.db"


@pytest.fixture
def repository(db_path: Path) -> Repository:
    return Repository(db_path)


def test_init_db_twice_keeps_data(db_path: Path) -> None:
    init_db(db_path)
    Repository(db_path).save_request(_record(), anonymized=True)
    init_db(db_path)
    assert _query(db_path, "SELECT COUNT(*) FROM requests") == [(1,)]
    tables = {row[0] for row in _query(db_path, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= tables


def test_init_db_creates_missing_directory(db_path: Path) -> None:
    init_db(db_path)
    assert db_path.is_file()


def test_init_db_failure_raises_storage_error(tmp_path: Path) -> None:
    blocker = tmp_path / "file.txt"
    blocker.write_text("x")
    with pytest.raises(StorageError):
        init_db(blocker / "sub" / "triage.db")


def test_already_processed_before_and_after_save(repository: Repository) -> None:
    record = _record()
    assert repository.already_processed(record.request_hash) is False
    repository.save_request(record, anonymized=True)
    assert repository.already_processed(record.request_hash) is True


def test_get_request_returns_saved_record(repository: Repository) -> None:
    record = _record(status="queued_for_review")
    repository.save_request(record, anonymized=True)

    assert repository.get_request(record.request_hash) == record


def test_get_request_unknown_hash_returns_none(repository: Repository) -> None:
    assert repository.get_request(request_hash("nunca gravado")) is None


def test_get_request_with_sql_text_as_hash_is_data(repository: Repository) -> None:
    assert repository.get_request("x' OR '1'='1") is None


def test_save_same_hash_twice_does_not_duplicate(repository: Repository, db_path: Path) -> None:
    record = _record()
    repository.save_request(record, anonymized=True)
    repository.save_request(record, anonymized=True)
    assert _query(db_path, "SELECT COUNT(*) FROM requests") == [(1,)]


@pytest.mark.parametrize("flag", [False, None, 1])
def test_save_without_anonymized_true_is_refused(repository: Repository, db_path: Path, flag: object) -> None:
    with pytest.raises(ValueError):
        repository.save_request(_record(), anonymized=flag)
    assert _query(db_path, "SELECT COUNT(*) FROM requests") == [(0,)]


def test_save_requires_keyword_anonymized(repository: Repository) -> None:
    with pytest.raises(TypeError):
        repository.save_request(_record(), True)


def test_save_invalid_status_is_refused(repository: Repository) -> None:
    with pytest.raises(ValueError):
        repository.save_request(_record(status="done"), anonymized=True)


def test_review_queue_enqueue_list_resolve(repository: Repository) -> None:
    record = _record(status="queued_for_review")
    repository.save_request(record, anonymized=True)
    first = repository.enqueue_review(record.request_hash, "baixa confiança")
    second = repository.enqueue_review(record.request_hash, "ambíguo")

    pending = repository.pending_reviews()
    assert [item.id for item in pending] == [first, second]
    assert pending[0].reason == "baixa confiança"

    assert repository.resolve_review(first, "respondido manualmente") is True
    assert [item.id for item in repository.pending_reviews()] == [second]
    assert repository.resolve_review(first, "de novo") is False
    assert repository.resolve_review(9999, "inexistente") is False


def test_enqueue_unknown_hash_raises_storage_error(repository: Repository) -> None:
    with pytest.raises(StorageError):
        repository.enqueue_review("hash-inexistente", "motivo")


def test_feedback_valid_and_invalid(repository: Repository, db_path: Path) -> None:
    record = _record()
    repository.save_request(record, anonymized=True)
    repository.add_feedback(record.request_hash, "up")
    repository.add_feedback(record.request_hash, "down")
    with pytest.raises(ValueError):
        repository.add_feedback(record.request_hash, "meh")
    assert _query(db_path, "SELECT rating FROM feedback ORDER BY id") == [("up",), ("down",)]


def test_feedback_unknown_hash_raises_storage_error(repository: Repository) -> None:
    with pytest.raises(StorageError):
        repository.add_feedback("hash-inexistente", "up")


def test_sql_injection_text_is_stored_as_data(repository: Repository, db_path: Path) -> None:
    text = "'; DROP TABLE requests;--"
    record = _record(text)
    repository.save_request(record, anonymized=True)
    tables = {row[0] for row in _query(db_path, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES <= tables
    assert _query(db_path, "SELECT anonymized_text FROM requests") == [(text,)]


def test_run_start_and_finish_store_totals(repository: Repository, db_path: Path) -> None:
    run_id = repository.start_run()
    assert _query(db_path, f"SELECT finished_at FROM runs WHERE id = {run_id}") == [(None,)]
    repository.finish_run(run_id, {"answered": 3, "queued_for_review": 1})
    (finished_at, totals_json), = _query(db_path, f"SELECT finished_at, totals_json FROM runs WHERE id = {run_id}")
    assert finished_at is not None
    assert json.loads(totals_json) == {"answered": 3, "queued_for_review": 1}


def test_storage_error_is_logged_without_request_text(repository: Repository, caplog: pytest.LogCaptureFixture) -> None:
    raw_marker = "texto-que-nao-pode-vazar"
    with caplog.at_level(logging.ERROR, logger="triage.storage"):
        with pytest.raises(StorageError):
            repository.add_feedback(raw_marker, "up")
    assert caplog.records
    assert raw_marker not in caplog.text


def test_set_label_creates_and_replaces(repository: Repository, db_path: Path) -> None:
    record = _record()
    repository.save_request(record, anonymized=True)
    repository.set_label(record.request_hash, "id_card")
    repository.set_label(record.request_hash, "other")
    assert _query(db_path, "SELECT request_hash, category FROM labels") == [(record.request_hash, "other")]


@pytest.mark.parametrize("category", ["", "   "])
def test_set_label_empty_category_is_refused(repository: Repository, category: str) -> None:
    record = _record()
    repository.save_request(record, anonymized=True)
    with pytest.raises(ValueError):
        repository.set_label(record.request_hash, category)


def test_set_label_unknown_hash_raises_storage_error(repository: Repository) -> None:
    with pytest.raises(StorageError):
        repository.set_label("hash-inexistente", "other")


def test_labeled_requests_returns_anonymized_text_in_order(repository: Repository) -> None:
    first, second = _record("primeiro pedido"), _record("segundo pedido")
    repository.save_request(first, anonymized=True)
    repository.save_request(second, anonymized=True)
    repository.set_label(second.request_hash, "voter_id")
    repository.set_label(first.request_hash, "id_card")
    assert [(item.anonymized_text, item.category) for item in repository.labeled_requests()] == [
        ("segundo pedido", "voter_id"),
        ("primeiro pedido", "id_card"),
    ]


def test_labeled_requests_empty(repository: Repository) -> None:
    assert repository.labeled_requests() == []


def test_database_without_labels_table_is_upgraded_without_data_loss(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(db_path)
    connection.executescript(
        "CREATE TABLE requests (hash TEXT PRIMARY KEY, anonymized_text TEXT NOT NULL, category TEXT, "
        "confidence REAL, status TEXT NOT NULL, review_reason TEXT, created_at TEXT NOT NULL);"
        "INSERT INTO requests VALUES ('h1', 'pedido antigo', NULL, NULL, 'answered', NULL, '2026-01-01');"
    )
    connection.commit()
    connection.close()

    repository = Repository(db_path)
    repository.set_label("h1", "other")

    assert _query(db_path, "SELECT hash, anonymized_text FROM requests") == [("h1", "pedido antigo")]
    assert [item.request_hash for item in repository.labeled_requests()] == ["h1"]
