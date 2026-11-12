"""Repositório de pedidos, fila de revisão, feedback e execuções.

Só texto anonimizado é gravado: `save_request` exige `anonymized=True`, barreira contra gravar texto bruto
([[003-seguranca-sem-autenticacao]]). Todo SQL usa parâmetros vinculados (`?`).
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from triage.storage.schema import (
    VALID_RATINGS,
    VALID_STATUSES,
    VALID_TIERS,
    VALID_TOPIC_SOURCES,
    init_db,
    session,
)


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


@dataclass(frozen=True)
class LabeledRequest:
    """Pedido com a categoria correta informada pelo revisor; o texto é sempre o anonimizado."""

    request_hash: str
    anonymized_text: str
    category: str


@dataclass(frozen=True)
class InteractionRecord:
    """Catalogação de uma interação: categoria, quem a escolheu, tag de revisão humana e a resposta dada."""

    request_hash: str
    topic_source: str
    needs_human: bool
    topic: str | None = None
    tier: str | None = None
    used_llm: bool = False
    fallback_reason: str | None = None
    response_text: str | None = None
    run_id: int | None = None


@dataclass(frozen=True)
class StoredInteraction:
    """Interação lida do banco, junto com o pedido a que pertence (texto anonimizado, status e motivo)."""

    record: InteractionRecord
    created_at: str
    status: str
    review_reason: str | None
    anonymized_text: str


@dataclass(frozen=True)
class InteractionCounts:
    """Interações contadas por categoria (`none` para as sem categoria) e pela tag `needs_human`."""

    by_topic: dict[str, int]
    needs_human: int
    automatic: int


NO_TOPIC_LABEL = "none"
INTERACTION_COLUMNS = (
    "i.request_hash, i.topic_source, i.needs_human, i.topic, i.tier, i.used_llm, i.fallback_reason, "
    "i.response_text, i.run_id, i.created_at, r.status, r.review_reason, r.anonymized_text"
)


def _validate_interaction(record: InteractionRecord) -> None:
    if record.topic_source not in VALID_TOPIC_SOURCES:
        raise ValueError(f"Origem da categoria inválida: {record.topic_source!r}.")
    if not isinstance(record.needs_human, bool):
        raise TypeError(f"needs_human deve ser booleano: {record.needs_human!r}.")
    if record.tier is not None and record.tier not in VALID_TIERS:
        raise ValueError(f"Degrau inválido: {record.tier!r}.")


def _stored_interaction(row: tuple) -> StoredInteraction:
    (digest, source, human, topic, tier, used_llm, fallback, response, run_id, created_at, status, reason, text) = row
    record = InteractionRecord(digest, source, bool(human), topic, tier, bool(used_llm), fallback, response, run_id)
    return StoredInteraction(record, created_at, status, reason, text)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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

    def set_label(self, request_hash: str, category: str) -> None:
        """Grava a categoria correta do pedido; regravar o mesmo hash substitui o rótulo."""
        if not category.strip():
            raise ValueError("A categoria do rótulo não pode ser vazia.")
        with session(self._path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO labels (request_hash, category, created_at) VALUES (?, ?, ?)",
                (request_hash, category, _now()),
            )

    def labeled_requests(self) -> list[LabeledRequest]:
        """Pedidos rotulados, do rótulo mais antigo ao mais recente, com o texto anonimizado."""
        with session(self._path) as connection:
            rows = connection.execute(
                "SELECT l.request_hash, r.anonymized_text, l.category FROM labels l "
                "JOIN requests r ON r.hash = l.request_hash ORDER BY l.created_at, l.rowid"
            ).fetchall()
        return [LabeledRequest(*row) for row in rows]

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

    def save_interaction(self, record: InteractionRecord) -> None:
        """Grava a catalogação do pedido; o mesmo hash de novo é ignorado. Hash sem pedido gravado é `StorageError`."""
        _validate_interaction(record)
        with session(self._path) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO interactions (request_hash, run_id, topic, topic_source, needs_human, tier, "
                "used_llm, fallback_reason, response_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.request_hash,
                    record.run_id,
                    record.topic,
                    record.topic_source,
                    int(record.needs_human),
                    record.tier,
                    int(record.used_llm),
                    record.fallback_reason,
                    record.response_text,
                    _now(),
                ),
            )

    def interactions(self, run_id: int | None = None) -> list[StoredInteraction]:
        """As interações por `created_at`, só as de uma execução quando `run_id` vem."""
        sql = f"SELECT {INTERACTION_COLUMNS} FROM interactions i JOIN requests r ON r.hash = i.request_hash"
        params: tuple = ()
        if run_id is not None:
            sql += " WHERE i.run_id = ?"
            params = (run_id,)
        with session(self._path) as connection:
            rows = connection.execute(sql + " ORDER BY i.created_at, i.rowid", params).fetchall()
        return [_stored_interaction(row) for row in rows]

    def interaction_counts(self) -> InteractionCounts:
        """Contagem das interações por categoria e pela tag `needs_human`."""
        with session(self._path) as connection:
            topics = connection.execute(
                "SELECT COALESCE(topic, ?), COUNT(*) FROM interactions GROUP BY 1 ORDER BY 1", (NO_TOPIC_LABEL,)
            ).fetchall()
            human = connection.execute("SELECT COUNT(*) FROM interactions WHERE needs_human = 1").fetchone()[0]
            total = connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        return InteractionCounts(dict(topics), human, total - human)
