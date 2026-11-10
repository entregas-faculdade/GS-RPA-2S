"""Catálogo estático e curado de fontes públicas: cada registro traz vários links e telefones (formato v2)."""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CATALOG_PATH = Path("data") / "catalog.json"

KIND_SERVICE = "service"
KINDS = frozenset({KIND_SERVICE, "portal", "channel"})
SCOPES = frozenset({"federal", "state", "municipal"})
AREAS = frozenset({"health", "education", "vehicles", "city", "documents", "social", "tax", "safety"})
STATUS_APPROVED = "approved"
STATUSES = frozenset({STATUS_APPROVED, "candidate"})

logger = logging.getLogger("triage.automation")


class CatalogFileError(ValueError):
    """O arquivo do catálogo não pôde ser lido ou não é uma lista."""


class CatalogRecordError(ValueError):
    """O registro está fora do formato v2."""


@dataclass(frozen=True)
class Link:
    """Página oficial de uma fonte."""

    label: str
    url: str


@dataclass(frozen=True)
class Phone:
    """Telefone oficial, no formato em que o cidadão disca (`156`, `0800 61 61 61`)."""

    label: str
    number: str


@dataclass(frozen=True)
class ServiceEntry:
    """Fonte pública do catálogo, com seus links e telefones."""

    id: str
    category: str | None
    kind: str
    scope: str
    coverage: str
    area: str
    display_name: str
    agency: str
    instructions: str
    keywords: tuple[str, ...]
    links: tuple[Link, ...]
    phones: tuple[Phone, ...]
    source_note: str
    verified_on: str
    status: str


def _text(record: dict, name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CatalogRecordError(f"campo {name} ausente ou não é texto")
    return value


def _choice(record: dict, name: str, allowed: frozenset[str]) -> str:
    value = _text(record, name)
    if value not in allowed:
        raise CatalogRecordError(f"campo {name} com valor inválido: {value!r}")
    return value


def _category(record: dict) -> str | None:
    if "category" not in record:
        raise CatalogRecordError("campo category ausente")
    value = record["category"]
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise CatalogRecordError("campo category deve ser texto ou null")
    return value


def _list_field(record: dict, name: str) -> list:
    value = record.get(name)
    if not isinstance(value, list):
        raise CatalogRecordError(f"campo {name} ausente ou não é lista")
    return value


def _keywords(record: dict) -> tuple[str, ...]:
    values = _list_field(record, "keywords")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise CatalogRecordError("campo keywords deve ser lista de textos")
    return tuple(values)


def _items(record: dict, name: str, item_type: type) -> tuple:
    fields = tuple(item_type.__dataclass_fields__)
    items = []
    for raw in _list_field(record, name):
        if not isinstance(raw, dict):
            raise CatalogRecordError(f"campo {name} deve ser lista de objetos")
        items.append(item_type(**{field: _text(raw, field) for field in fields}))
    return tuple(items)


def _validate_shape(entry: ServiceEntry) -> None:
    """Regras que cruzam campos: o que cada `kind` exige e a data de verificação."""
    if entry.kind == KIND_SERVICE and not entry.links:
        raise CatalogRecordError("kind service exige ao menos um link")
    if not entry.links and not entry.phones:
        raise CatalogRecordError("registro sem link e sem telefone")
    try:
        date.fromisoformat(entry.verified_on)
    except ValueError as error:
        raise CatalogRecordError(f"verified_on inválido: {entry.verified_on!r}") from error


def parse_entry(record: object) -> ServiceEntry:
    """Converte um registro do JSON em `ServiceEntry`; registro fora do formato levanta `CatalogRecordError`."""
    if not isinstance(record, dict):
        raise CatalogRecordError(f"esperava objeto, veio {type(record).__name__}")
    entry = ServiceEntry(
        id=_text(record, "id"),
        category=_category(record),
        kind=_choice(record, "kind", KINDS),
        scope=_choice(record, "scope", SCOPES),
        coverage=_text(record, "coverage"),
        area=_choice(record, "area", AREAS),
        display_name=_text(record, "display_name"),
        agency=_text(record, "agency"),
        instructions=_text(record, "instructions"),
        keywords=_keywords(record),
        links=_items(record, "links", Link),
        phones=_items(record, "phones", Phone),
        source_note=_text(record, "source_note"),
        verified_on=_text(record, "verified_on"),
        status=_choice(record, "status", STATUSES),
    )
    _validate_shape(entry)
    return entry


def read_catalog_records(path: Path = CATALOG_PATH) -> list:
    """Lê os registros crus do arquivo; ausente, ilegível ou fora de lista levanta `CatalogFileError`."""
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CatalogFileError(f"Catálogo indisponível ({path}): {error}") from error
    if not isinstance(records, list):
        raise CatalogFileError(f"Catálogo inválido (esperava uma lista): {path}")
    return records


def load_catalog(path: Path = CATALOG_PATH) -> list[ServiceEntry]:
    """Lê as entradas v2 na ordem do arquivo; falha segura: arquivo ausente ou inválido devolve `[]`.

    Registro inválido ou com `id` repetido é ignorado com log.
    """
    try:
        records = read_catalog_records(path)
    except CatalogFileError as error:
        logger.error("%s", error)
        return []
    entries: list[ServiceEntry] = []
    seen_ids: set[str] = set()
    for record in records:
        try:
            entry = parse_entry(record)
        except CatalogRecordError as error:
            logger.error("Registro do catálogo inválido (%s): %r", error, record)
            continue
        if entry.id in seen_ids:
            logger.error("Registro do catálogo com id repetido ignorado: %s", entry.id)
            continue
        seen_ids.add(entry.id)
        entries.append(entry)
    return entries


def approved_only(entries: list[ServiceEntry]) -> list[ServiceEntry]:
    """As entradas aprovadas: só elas podem chegar ao cidadão."""
    return [entry for entry in entries if entry.status == STATUS_APPROVED]
