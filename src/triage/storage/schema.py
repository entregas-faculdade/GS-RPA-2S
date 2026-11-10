"""Esquema SQLite e acesso à conexão: único ponto do projeto que importa `sqlite3`.

Toda operação abre uma conexão curta, com chaves estrangeiras ligadas, e a fecha ao final. Falha de I/O ou do
SQLite vira `StorageError`; só o nome do erro é logado, nunca o texto do pedido.
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("triage.storage")

STATUS_ANSWERED = "answered"
STATUS_QUEUED_FOR_REVIEW = "queued_for_review"
STATUS_REJECTED = "rejected"
VALID_STATUSES = (STATUS_ANSWERED, STATUS_QUEUED_FOR_REVIEW, STATUS_REJECTED)

RATING_UP = "up"
RATING_DOWN = "down"
VALID_RATINGS = (RATING_UP, RATING_DOWN)

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    hash TEXT PRIMARY KEY,
    anonymized_text TEXT NOT NULL,
    category TEXT,
    confidence REAL,
    status TEXT NOT NULL CHECK (status IN ('answered', 'queued_for_review', 'rejected')),
    review_reason TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_hash TEXT NOT NULL REFERENCES requests(hash),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolution_note TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_hash TEXT NOT NULL REFERENCES requests(hash),
    rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    totals_json TEXT
);
"""


class StorageError(Exception):
    """Falha de I/O ou do SQLite; o pipeline decide o caminho seguro."""


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except (sqlite3.Error, OSError) as exc:
        logger.error("Falha no armazenamento SQLite: %s", type(exc).__name__)
        raise StorageError("Falha ao acessar o banco SQLite.") from exc


@contextmanager
def session(path: Path) -> Iterator[sqlite3.Connection]:
    """Abre uma conexão, confirma a transação se o bloco terminar sem erro e sempre fecha."""
    with _translate_errors():
        connection = sqlite3.connect(path)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        finally:
            connection.close()


def init_db(path: str | Path) -> None:
    """Cria o diretório e as tabelas que faltarem; pode ser chamada quantas vezes for preciso."""
    db_path = Path(path)
    with _translate_errors():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    with session(db_path) as connection:
        connection.executescript(SCHEMA)
