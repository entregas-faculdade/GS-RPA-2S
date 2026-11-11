"""Catálogo estático e curado de fontes públicas: cada registro traz vários links e telefones (formato v2)."""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CATALOG_PATH = Path("data") / "catalog.json"
CATALOG_DIR_PATH = Path("data") / "catalog.d"
CATALOG_DIR_PATTERN = "*.json"
MAX_CONTENT_LENGTH = 3000

KIND_SERVICE = "service"
KINDS = frozenset({KIND_SERVICE, "portal", "channel"})
SCOPES = frozenset({"federal", "state", "municipal"})
AREAS = frozenset({"health", "education", "vehicles", "city", "documents", "social", "tax", "safety"})
STATUS_APPROVED = "approved"
STATUSES = frozenset({STATUS_APPROVED, "candidate"})
DEFAULT_MAX_AGE_DAYS = 180

logger = logging.getLogger("triage.automation")


class CatalogFileError(ValueError):
    """O arquivo do catálogo não pôde ser lido ou não é uma lista."""


class CatalogRecordError(ValueError):
    """O registro está fora do formato v2."""


@dataclass(frozen=True)
class Link:
    """Página oficial de uma fonte; `manual_check_on` é a data (ISO) em que uma pessoa a abriu e atestou."""

    label: str
    url: str
    manual_check_on: str | None = None


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
    content: str = ""


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


def _content(record: dict) -> str:
    """Trecho oficial da página, opcional: ausente vale vazio; presente, precisa ser texto não vazio de até `MAX_CONTENT_LENGTH`."""
    if "content" not in record:
        return ""
    value = _text(record, "content")
    if len(value) > MAX_CONTENT_LENGTH:
        raise CatalogRecordError(f"campo content com {len(value)} caracteres (limite {MAX_CONTENT_LENGTH})")
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


def _manual_check_on(raw: dict) -> str | None:
    if "manual_check_on" not in raw:
        return None
    value = _text(raw, "manual_check_on")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise CatalogRecordError(f"manual_check_on inválido: {value!r}") from error
    return value


def _links(record: dict) -> tuple[Link, ...]:
    links = []
    for raw in _list_field(record, "links"):
        if not isinstance(raw, dict):
            raise CatalogRecordError("campo links deve ser lista de objetos")
        links.append(Link(_text(raw, "label"), _text(raw, "url"), _manual_check_on(raw)))
    return tuple(links)


def manual_check_valid(link: Link, today: date, max_age_days: int) -> bool:
    """O atestado manual do link existe e não é futuro nem mais velho que `max_age_days`?"""
    if link.manual_check_on is None:
        return False
    age_days = (today - date.fromisoformat(link.manual_check_on)).days
    return 0 <= age_days <= max_age_days


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
        links=_links(record),
        phones=_items(record, "phones", Phone),
        source_note=_text(record, "source_note"),
        verified_on=_text(record, "verified_on"),
        status=_choice(record, "status", STATUSES),
        content=_content(record),
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


def catalog_extra_files(directory: Path | None = CATALOG_DIR_PATH) -> list[Path]:
    """Os `*.json` da pasta da base enriquecida, em ordem de nome; pasta ausente, vazia ou ilegível devolve `[]`."""
    if directory is None or not directory.is_dir():
        return []
    try:
        return sorted(directory.glob(CATALOG_DIR_PATTERN), key=lambda file: file.name)
    except OSError as error:
        logger.error("Pasta do catálogo ilegível (%s): %s", directory, error)
        return []


def _parse_records(records: list, seen_ids: set[str]) -> list[ServiceEntry]:
    """Converte os registros de um arquivo; inválido ou com `id` já visto (neste ou em arquivo anterior) é ignorado com log."""
    entries: list[ServiceEntry] = []
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


def load_catalog(path: Path = CATALOG_PATH, extra_dir: Path | None = CATALOG_DIR_PATH) -> list[ServiceEntry]:
    """Lê as entradas v2 de `path` e depois de cada `*.json` de `extra_dir` (ordem de nome); `extra_dir=None` lê só `path`.

    Falha segura: arquivo ausente, ilegível ou fora de lista é registrado e ignorado, sem derrubar os demais.
    Registro inválido ou com `id` repetido (vale o primeiro, mesmo entre arquivos) é ignorado com log.
    """
    entries: list[ServiceEntry] = []
    seen_ids: set[str] = set()
    for file in [path, *catalog_extra_files(extra_dir)]:
        try:
            records = read_catalog_records(file)
        except CatalogFileError as error:
            logger.error("%s", error)
            continue
        entries.extend(_parse_records(records, seen_ids))
    return entries


def approved_only(entries: list[ServiceEntry]) -> list[ServiceEntry]:
    """As entradas aprovadas: só elas podem chegar ao cidadão."""
    return [entry for entry in entries if entry.status == STATUS_APPROVED]
