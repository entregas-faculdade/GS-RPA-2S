"""CSV de saída da execução: as interações catalogadas naquela execução, com o texto anonimizado e a resposta dada.

O texto é o anonimizado, mas a anonimização por regras pode deixar dado pessoal residual: revise o arquivo antes de
compartilhá-lo. Células iniciadas em `=`, `+`, `-` ou `@` são neutralizadas para a planilha não as executar como fórmula.
"""

import csv
import logging
from pathlib import Path

from triage.automation.topics import TopicsError, load_topics
from triage.storage import Repository, StorageError, StoredInteraction

EXPORT_SUBDIR = "exports"
EXPORT_FILE_TEMPLATE = "interactions-run-{run_id}.csv"
EXPORT_COLUMNS = (
    "request_hash",
    "created_at",
    "topic",
    "topic_label",
    "topic_source",
    "needs_human",
    "status",
    "review_reason",
    "tier",
    "used_llm",
    "fallback_reason",
    "anonymized_text",
    "response_text",
)
FORMULA_PREFIXES = ("=", "+", "-", "@")
FORMULA_GUARD = "'"

logger = logging.getLogger("triage.pipeline")


def _safe_cell(value: object) -> str:
    """Texto da célula; o que começa como fórmula ganha um apóstrofo na frente."""
    text = "" if value is None else str(value)
    return FORMULA_GUARD + text if text.startswith(FORMULA_PREFIXES) else text


def _topic_labels() -> dict[str, str]:
    """Rótulo em português de cada categoria; vocabulário ilegível deixa a coluna vazia."""
    try:
        return {topic.id: topic.label for topic in load_topics().topics}
    except TopicsError as error:
        logger.warning("Rótulos das categorias indisponíveis (%s); coluna topic_label vazia", type(error).__name__)
        return {}


def _row(item: StoredInteraction, labels: dict[str, str]) -> list[str]:
    record = item.record
    values = (
        record.request_hash,
        item.created_at,
        record.topic,
        labels.get(record.topic, "") if record.topic else "",
        record.topic_source,
        int(record.needs_human),
        item.status,
        item.review_reason,
        record.tier,
        int(record.used_llm),
        record.fallback_reason,
        item.anonymized_text,
        record.response_text,
    )
    return [_safe_cell(value) for value in values]


def _write(path: Path, items: list[StoredInteraction]) -> None:
    labels = _topic_labels()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPORT_COLUMNS)
        writer.writerows(_row(item, labels) for item in items)


def write_interactions_csv(repository: Repository, run_id: int, output_dir: str | Path) -> Path | None:
    """Grava `<output_dir>/exports/interactions-run-<id>.csv`; `None` sem interação nova ou com falha (só logada)."""
    try:
        items = repository.interactions(run_id)
        if not items:
            return None
        path = Path(output_dir) / EXPORT_SUBDIR / EXPORT_FILE_TEMPLATE.format(run_id=run_id)
        _write(path, items)
    except (StorageError, OSError) as error:
        logger.error("Falha ao gravar o CSV de interações (%s)", type(error).__name__)
        return None
    logger.info("CSV de interações gravado em %s", path)
    return path
