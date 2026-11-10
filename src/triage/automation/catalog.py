"""Catálogo estático e curado de serviços públicos (uma URL oficial por categoria)."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path("data") / "catalog.json"

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class ServiceEntry:
    """Serviço oficial associado a uma categoria de pedido."""

    category: str
    display_name: str
    agency: str
    url: str
    instructions: str
    source_note: str
    verified_on: str


def _parse_entry(record: object) -> ServiceEntry | None:
    """Converte um registro do JSON em `ServiceEntry`; registro malformado vira `None` (com log)."""
    if not isinstance(record, dict):
        logger.error("Registro do catálogo inválido (esperava objeto): %r", record)
        return None
    try:
        return ServiceEntry(**{name: record[name] for name in ServiceEntry.__dataclass_fields__})
    except KeyError as error:
        logger.error("Registro do catálogo sem o campo %s: %r", error, record.get("category"))
        return None


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, ServiceEntry]:
    """Lê o catálogo indexado por categoria; falha segura: arquivo ausente ou inválido devolve `{}`."""
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.error("Catálogo indisponível (%s): %s", path, error)
        return {}
    if not isinstance(records, list):
        logger.error("Catálogo inválido (esperava uma lista): %s", path)
        return {}
    entries = (_parse_entry(record) for record in records)
    return {entry.category: entry for entry in entries if entry is not None}
