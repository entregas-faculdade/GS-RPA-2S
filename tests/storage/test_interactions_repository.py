"""Tabela `interactions`: criação sobre banco antigo, gravação, validação, filtro por execução e contagens."""

import sqlite3
from pathlib import Path

import pytest

from triage.storage import (
    InteractionRecord,
    Repository,
    RequestRecord,
    StorageError,
    init_db,
    request_hash,
)

OLD_SCHEMA = """
CREATE TABLE requests (hash TEXT PRIMARY KEY, anonymized_text TEXT NOT NULL, category TEXT, confidence REAL,
    status TEXT NOT NULL CHECK (status IN ('answered', 'queued_for_review', 'rejected')),
    review_reason TEXT, created_at TEXT NOT NULL);
INSERT INTO requests VALUES ('h-old', 'texto antigo', 'id_card', 0.9, 'answered', NULL, '2026-01-01T00:00:00+00:00');
"""


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    return Repository(tmp_path / "triage.db")


def _save_request(repository: Repository, text: str = "pedido", status: str = "answered") -> str:
    digest = request_hash(text)
    repository.save_request(RequestRecord(digest, text, status, category="id_card"), anonymized=True)
    return digest


def _interaction(digest: str, **overrides: object) -> InteractionRecord:
    values: dict = {"request_hash": digest, "topic_source": "llm", "needs_human": False, "topic": "documents"}
    return InteractionRecord(**{**values, **overrides})


def _tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_the_interactions_table_is_created_and_init_db_twice_is_harmless(tmp_path: Path) -> None:
    path = tmp_path / "db" / "triage.db"
    init_db(path)
    repository = Repository(path)
    repository.save_interaction(_interaction(_save_request(repository)))

    init_db(path)

    assert "interactions" in _tables(path)
    assert len(repository.interactions()) == 1


def test_an_old_database_opens_without_loss_and_gains_the_table(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.executescript(OLD_SCHEMA)

    repository = Repository(path)

    assert "interactions" in _tables(path)
    assert repository.already_processed("h-old")
    repository.save_interaction(_interaction("h-old", topic="documents"))
    assert [item.record.request_hash for item in repository.interactions()] == ["h-old"]


def test_save_and_read_back_every_field(repository: Repository) -> None:
    digest = _save_request(repository, "texto anonimizado", "queued_for_review")
    record = _interaction(
        digest,
        topic_source="catalog",
        needs_human=True,
        tier="finder",
        used_llm=True,
        fallback_reason="llm_unavailable",
        response_text="a resposta",
        run_id=7,
    )

    repository.save_interaction(record)

    (stored,) = repository.interactions()
    assert stored.record == record
    assert stored.status == "queued_for_review"
    assert stored.anonymized_text == "texto anonimizado"
    assert stored.created_at.endswith("+00:00")


def test_the_same_hash_again_is_ignored(repository: Repository) -> None:
    digest = _save_request(repository)
    repository.save_interaction(_interaction(digest, topic="documents"))

    repository.save_interaction(_interaction(digest, topic="tax", topic_source="rule"))

    (stored,) = repository.interactions()
    assert stored.record.topic == "documents"


@pytest.mark.parametrize(
    "overrides",
    [{"topic_source": "magic"}, {"topic_source": ""}, {"tier": "x"}],
)
def test_invalid_values_are_a_value_error(repository: Repository, overrides: dict) -> None:
    digest = _save_request(repository)

    with pytest.raises(ValueError):
        repository.save_interaction(_interaction(digest, **overrides))

    assert repository.interactions() == []


def test_a_hash_without_a_request_is_a_storage_error(repository: Repository) -> None:
    with pytest.raises(StorageError):
        repository.save_interaction(_interaction("nao-existe"))


def test_the_check_constraints_back_the_python_validation(repository: Repository, tmp_path: Path) -> None:
    digest = _save_request(repository)
    with sqlite3.connect(tmp_path / "triage.db") as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO interactions (request_hash, topic_source, needs_human, created_at) VALUES (?, 'x', 0, 'now')",
            (digest,),
        )


def test_interactions_filter_by_run_and_keep_creation_order(repository: Repository) -> None:
    first, second, chat = (_save_request(repository, text) for text in ("um", "dois", "chat"))
    repository.save_interaction(_interaction(first, run_id=1))
    repository.save_interaction(_interaction(second, run_id=2))
    repository.save_interaction(_interaction(chat, run_id=None))

    assert [item.record.request_hash for item in repository.interactions()] == [first, second, chat]
    assert [item.record.request_hash for item in repository.interactions(run_id=2)] == [second]
    assert repository.interactions(run_id=99) == []


def test_counts_by_topic_and_by_the_human_tag(repository: Repository) -> None:
    rows = [("a", "tax", False), ("b", "tax", True), ("c", "health", False), ("d", None, True)]
    for text, topic, human in rows:
        source = "none" if topic is None else "llm"
        repository.save_interaction(_interaction(_save_request(repository, text), topic=topic, topic_source=source, needs_human=human))

    counts = repository.interaction_counts()

    assert counts.by_topic == {"health": 1, "none": 1, "tax": 2}
    assert (counts.needs_human, counts.automatic) == (2, 2)


def test_counts_of_an_empty_table(repository: Repository) -> None:
    counts = repository.interaction_counts()

    assert counts.by_topic == {}
    assert (counts.needs_human, counts.automatic) == (0, 0)


@pytest.mark.parametrize("needs_human", [1, 0, "yes", None])
def test_a_non_boolean_needs_human_is_a_type_error(repository: Repository, needs_human: object) -> None:
    digest = _save_request(repository)

    with pytest.raises(TypeError):
        repository.save_interaction(_interaction(digest, needs_human=needs_human))

    assert repository.interactions() == []
