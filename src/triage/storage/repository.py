"""Repositório de pedidos, fila de revisão, feedback e execuções.

Só texto anonimizado é gravado: `save_request` exige `anonymized=True`, barreira contra gravar texto bruto
([[003-seguranca-sem-autenticacao]]). Todo SQL usa parâmetros vinculados (`?`).
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from triage.storage.schema import VALID_RATINGS, VALID_STATUSES, init_db, session


@dataclass(frozen=True)
class RequestRecord:
    """Pedido já processado, com o texto anonimizado e o resultado da triagem."""

    request_hash: str
    anonymized_text: str
    status: str
    category: str | None = None
    confidence: float | None = None
    review_reason: str | None = None


@dataclass(frozen=True)
class ReviewItem:
    """Item pendente na fila de revisão humana."""

    id: int
    request_hash: str
    reason: str
    created_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Repository:
    """Acesso ao banco SQLite; cada operação usa uma conexão curta."""

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        init_db(self._path)

    def already_processed(self, request_hash: str) -> bool:
        with session(self._path) as connection:
            row = connection.execute("SELECT 1 FROM requests WHERE hash = ?", (request_hash,)).fetchone()
        return row is not None

    def get_request(self, request_hash: str) -> RequestRecord | None:
        """Devolve o pedido gravado com esse hash, ou `None` se ele não existe."""
        with session(self._path) as connection:
            row = connection.execute(
                "SELECT hash, anonymized_text, status, category, confidence, review_reason "
                "FROM requests WHERE hash = ?",
                (request_hash,),
            ).fetchone()
        return None if row is None else RequestRecord(*row)

    def save_request(self, record: RequestRecord, *, anonymized: bool) -> None:
        """Grava o pedido; o mesmo hash gravado de novo é ignorado, nunca erro."""
        if anonymized is not True:
            raise ValueError("Só texto anonimizado pode ser gravado: passe anonymized=True.")
        if record.status not in VALID_STATUSES:
            raise ValueError(f"Status inválido: {record.status!r}.")
        with session(self._path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO requests "
                "(hash, anonymized_text, category, confidence, status, review_reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.request_hash,
                    record.anonymized_text,
                    record.category,
                    record.confidence,
                    record.status,
                    record.review_reason,
                    _now(),
                ),
            )

    def enqueue_review(self, request_hash: str, reason: str) -> int:
        """Põe o pedido na fila de revisão e devolve o id do item."""
        with session(self._path) as connection:
            cursor = connection.execute(
                "INSERT INTO review_queue (request_hash, reason, created_at) VALUES (?, ?, ?)",
                (request_hash, reason, _now()),
            )
            return int(cursor.lastrowid)

    def pending_reviews(self) -> list[ReviewItem]:
        with session(self._path) as connection:
            rows = connection.execute(
                "SELECT id, request_hash, reason, created_at FROM review_queue WHERE resolved = 0 ORDER BY id"
            ).fetchall()
        return [ReviewItem(*row) for row in rows]

    def resolve_review(self, review_id: int, note: str) -> bool:
        """Marca o item como resolvido; devolve `False` se ele não existe ou já estava resolvido."""
        with session(self._path) as connection:
            cursor = connection.execute(
                "UPDATE review_queue SET resolved = 1, resolution_note = ? WHERE id = ? AND resolved = 0",
                (note, review_id),
            )
            return cursor.rowcount > 0

    def add_feedback(self, request_hash: str, rating: str) -> None:
        if rating not in VALID_RATINGS:
            raise ValueError(f"Avaliação inválida: {rating!r}; use {' ou '.join(VALID_RATINGS)}.")
        with session(self._path) as connection:
            connection.execute(
                "INSERT INTO feedback (request_hash, rating, created_at) VALUES (?, ?, ?)",
                (request_hash, rating, _now()),
            )

    def start_run(self) -> int:
        with session(self._path) as connection:
            cursor = connection.execute("INSERT INTO runs (started_at) VALUES (?)", (_now(),))
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, totals: dict) -> None:
        with session(self._path) as connection:
            connection.execute(
                "UPDATE runs SET finished_at = ?, totals_json = ? WHERE id = ?",
                (_now(), json.dumps(totals, ensure_ascii=False), run_id),
            )
