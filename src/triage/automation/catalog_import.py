"""Importa a planilha `.xlsx` da base enriquecida para registros do catálogo (formato v2).

Só a biblioteca padrão lê a planilha (`zipfile` e `xml.etree`). As tabelas de mapeamento vivem em
`data/catalog_import.json`; a saída é determinística (ordem da planilha), então rodar duas vezes gera o mesmo arquivo.
"""

import json
import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import (
    KIND_SERVICE,
    STATUS_APPROVED,
    CatalogRecordError,
    ServiceEntry,
    parse_entry,
)

IMPORT_CONFIG_PATH = Path("data") / "catalog_import.json"
KIND_PORTAL = "portal"
STATUS_CANDIDATE = "candidate"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORKBOOK_PART = "xl/workbook.xml"
WORKBOOK_RELS_PART = "xl/_rels/workbook.xml.rels"
SHARED_STRINGS_PART = "xl/sharedStrings.xml"

logger = logging.getLogger("triage.automation")


class CatalogImportError(ValueError):
    """A planilha ou a configuração da importação não pôde ser lida."""


@dataclass(frozen=True)
class ImportConfig:
    """Tabelas de mapeamento da planilha para o catálogo (lidas de `data/catalog_import.json`)."""

    id_prefix: str
    columns: dict[str, str]
    scopes: dict[str, dict[str, str]]
    portal_prefix: str
    default_area: str
    areas: dict[str, str]
    instruction_template: str
    source_note_template: str
    candidate_note_template: str


@dataclass(frozen=True)
class ImportOptions:
    """O que muda a cada importação: a data de verificação, a allowlist e o nome da planilha de origem."""

    verified_on: str
    allowed_suffixes: frozenset[str]
    source_name: str


@dataclass(frozen=True)
class Pair:
    """Registro importado que aponta para o mesmo link de um registro do catálogo atual."""

    imported_id: str
    existing_id: str


@dataclass
class ImportReport:
    """O que a importação fez: linhas lidas, registros gerados e o que ficou de fora ou fora do padrão."""

    rows_read: int = 0
    records: list[dict] = field(default_factory=list)
    ignored: list[tuple[str, str]] = field(default_factory=list)
    candidates: list[tuple[str, str]] = field(default_factory=list)
    default_area: list[tuple[str, str]] = field(default_factory=list)


def _fold(text: str) -> str:
    """Texto sem acento, minúsculo e com espaços únicos: compara cabeçalho e categoria sem depender da grafia."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.casefold().split())


def load_import_config(path: Path = IMPORT_CONFIG_PATH) -> ImportConfig:
    """Lê as tabelas de mapeamento; arquivo ausente, ilegível ou incompleto levanta `CatalogImportError`."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ImportConfig(
            id_prefix=raw["id_prefix"],
            columns=raw["columns"],
            scopes=raw["scopes"],
            portal_prefix=raw["portal_prefix"],
            default_area=raw["default_area"],
            areas={_fold(name): area for name, area in raw["areas"].items()},
            instruction_template=raw["instruction_template"],
            source_note_template=raw["source_note_template"],
            candidate_note_template=raw["candidate_note_template"],
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise CatalogImportError(f"Configuração da importação indisponível ({path}): {error}") from error


def _read_part(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        return archive.read(name)
    except KeyError as error:
        raise CatalogImportError(f"Planilha sem a parte {name}") from error


def _first_sheet_part(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(_read_part(archive, WORKBOOK_PART))
    sheet = workbook.find(f"{{{SHEET_NS}}}sheets/{{{SHEET_NS}}}sheet")
    if sheet is None:
        raise CatalogImportError("Planilha sem nenhuma aba")
    relationship_id = sheet.get(f"{{{DOC_REL_NS}}}id")
    for relationship in ET.fromstring(_read_part(archive, WORKBOOK_RELS_PART)):
        if relationship.get("Id") == relationship_id and relationship.tag == f"{{{PKG_REL_NS}}}Relationship":
            target = relationship.get("Target", "")
            return target.lstrip("/") if target.startswith("/") else f"xl/{target}"
    raise CatalogImportError("Planilha com aba sem arquivo associado")


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Textos compartilhados da planilha; ausentes quando ela usa só `inlineStr`."""
    if SHARED_STRINGS_PART not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(SHARED_STRINGS_PART))
    return ["".join(node.text or "" for node in item.iter(f"{{{SHEET_NS}}}t")) for item in root.iter(f"{{{SHEET_NS}}}si")]


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{SHEET_NS}}}t"))
    value = cell.findtext(f"{{{SHEET_NS}}}v", default="")
    if kind == "s" and value:
        return shared[int(value)]
    return value


def _column_index(reference: str) -> int:
    """Posição (de 0) da coluna na referência da célula: `A1` é 0, `B7` é 1, `AA3` é 26."""
    letters = re.match(r"[A-Za-z]+", reference)
    if letters is None:
        raise CatalogImportError(f"Referência de célula inválida: {reference!r}")
    index = 0
    for char in letters.group().upper():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _row_cells(row: ET.Element, shared: list[str]) -> list[str]:
    """Os textos da linha por posição de coluna; coluna vazia (célula ausente) vira texto vazio."""
    cells: list[str] = []
    for cell in row.iter(f"{{{SHEET_NS}}}c"):
        position = _column_index(cell.get("r", ""))
        cells.extend([""] * (position + 1 - len(cells)))
        cells[position] = _cell_text(cell, shared)
    return cells


def _sheet_table(archive: zipfile.ZipFile) -> list[tuple[int, list[str]]]:
    shared = _shared_strings(archive)
    sheet = ET.fromstring(_read_part(archive, _first_sheet_part(archive)))
    rows = sheet.iter(f"{{{SHEET_NS}}}row")
    return [(int(row.get("r", position)), _row_cells(row, shared)) for position, row in enumerate(rows, start=1)]


def read_xlsx_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    """Linhas da primeira aba como `(número da linha, {cabeçalho normalizado: texto})`, sem a linha de cabeçalho.

    Aceita `sharedStrings` e `inlineStr`. Arquivo ausente, que não é zip ou sem aba levanta `CatalogImportError`.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            table = _sheet_table(archive)
    except (OSError, zipfile.BadZipFile, ET.ParseError, IndexError, ValueError) as error:
        raise CatalogImportError(f"Planilha ilegível ({path}): {error}") from error
    if not table:
        raise CatalogImportError(f"Planilha sem linhas ({path})")
    headers = [_fold(name) for name in table[0][1]]
    return [(line, dict(zip(headers, [*cells, *[""] * len(headers)], strict=False))) for line, cells in table[1:]]


def _require_columns(rows: list[tuple[int, dict[str, str]]], config: ImportConfig) -> None:
    if not rows:
        return
    present = rows[0][1]
    missing = [name for name in config.columns.values() if _fold(name) not in present]
    if missing:
        raise CatalogImportError(f"Planilha sem as colunas: {', '.join(missing)}")


def _split_keywords(text: str) -> list[str]:
    """Palavras-chave separadas por vírgula, aparadas, sem vazio e sem repetição (mantém a ordem)."""
    unique: dict[str, None] = {}
    for part in text.split(","):
        if part.strip():
            unique.setdefault(part.strip(), None)
    return list(unique)


def _fields(values: dict[str, str], config: ImportConfig) -> dict[str, str]:
    return {name: values.get(_fold(column), "").strip() for name, column in config.columns.items()}


def _problem(fields: dict[str, str], config: ImportConfig, seen_ids: set[str]) -> str | None:
    """Por que a linha é ignorada, ou `None` se segue para a conversão."""
    row_id = fields["id"]
    if not row_id:
        return "linha sem ID"
    if not fields["url"]:
        return "linha sem URL"
    if row_id.lower() in seen_ids:
        return "ID repetido"
    if row_id[0].upper() not in config.scopes:
        return f"prefixo do ID sem esfera na configuração: {row_id[0]!r}"
    return None


def _status_and_note(fields: dict[str, str], line: int, config: ImportConfig, options: ImportOptions) -> tuple[str, str]:
    note = config.source_note_template.format(
        file=options.source_name, line=line, id=fields["id"], notes=fields["notes"] or "sem notas"
    )
    if is_allowed(fields["url"], options.allowed_suffixes):
        return STATUS_APPROVED, note
    host = urlsplit(fields["url"]).hostname or fields["url"]
    return STATUS_CANDIDATE, config.candidate_note_template.format(note=note, host=host)


def _build_record(fields: dict[str, str], line: int, config: ImportConfig, options: ImportOptions) -> dict:
    status, source_note = _status_and_note(fields, line, config, options)
    scope = config.scopes[fields["id"][0].upper()]
    is_portal = fields["name"].casefold().startswith(config.portal_prefix.casefold())
    return {
        "id": f"{config.id_prefix}{fields['id'].lower()}",
        "category": None,
        "kind": KIND_PORTAL if is_portal else KIND_SERVICE,
        "scope": scope["scope"],
        "coverage": scope["coverage"],
        "area": config.areas.get(_fold(fields["category"]), config.default_area),
        "display_name": fields["name"],
        "agency": fields["agency"],
        "instructions": config.instruction_template.format(agency=fields["agency"], name=fields["name"]),
        "keywords": _split_keywords(fields["keywords"]),
        "links": [{"label": fields["name"], "url": fields["url"]}],
        "phones": [],
        "source_note": source_note,
        "verified_on": options.verified_on,
        "status": status,
    }


def _ignore(report: ImportReport, label: str, reason: str) -> None:
    logger.warning("Linha da planilha ignorada (%s): %s", label, reason)
    report.ignored.append((label, reason))


def _convert_row(
    line: int, values: dict[str, str], context: tuple[ImportConfig, ImportOptions], report: ImportReport
) -> None:
    config, options = context
    fields = _fields(values, config)
    seen_ids = {record["id"].removeprefix(config.id_prefix) for record in report.records}
    label = fields["id"] or f"linha {line}"
    reason = _problem(fields, config, seen_ids)
    if reason is not None:
        _ignore(report, label, reason)
        return
    record = _build_record(fields, line, config, options)
    try:
        parse_entry(record)
    except CatalogRecordError as error:
        _ignore(report, label, f"registro inválido: {error}")
        return
    report.records.append(record)
    if record["status"] == STATUS_CANDIDATE:
        report.candidates.append((record["id"], "domínio fora da allowlist"))
    if _fold(fields["category"]) not in config.areas:
        report.default_area.append((record["id"], fields["category"]))


def convert_rows(
    rows: list[tuple[int, dict[str, str]]], config: ImportConfig, options: ImportOptions
) -> ImportReport:
    """Converte as linhas da planilha em registros do catálogo; linha inválida é ignorada com log e entra no relatório."""
    _require_columns(rows, config)
    report = ImportReport()
    for line, values in rows:
        if not any(value.strip() for value in values.values()):
            continue
        report.rows_read += 1
        _convert_row(line, values, (config, options), report)
    return report


def import_xlsx(path: Path, config: ImportConfig, options: ImportOptions) -> ImportReport:
    """Lê a planilha e a converte; o relatório traz os registros na ordem das linhas."""
    return convert_rows(read_xlsx_rows(path), config, options)


def _link_key(url: str) -> tuple[str, str, str]:
    """(host sem `www.`, caminho sem barra final, consulta), em minúsculas: o link normalizado."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").removeprefix("www.")
    return host, parts.path.rstrip("/").lower(), parts.query.lower()


def find_pairs(records: list[dict], entries: list[ServiceEntry]) -> list[Pair]:
    """Pares registro importado × registro do catálogo atual com o mesmo link normalizado (sem `www.` e sem barra final).

    Só informa: nada é removido nem fundido (os dois convivem, com ids diferentes). Host ou seção iguais não contam: dá ruído.
    """
    return [
        Pair(record["id"], entry.id)
        for record in records
        for entry in entries
        if any(_link_key(link.url) == _link_key(record["links"][0]["url"]) for link in entry.links)
    ]


def write_catalog_json(records: list[dict], path: Path) -> None:
    """Grava os registros em JSON determinístico (`indent=2`, UTF-8, fim de linha `\\n`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _section(title: str, lines: list[str]) -> list[str]:
    return [f"{title}: {len(lines)}", *(f"  - {line}" for line in lines)]


def format_report(report: ImportReport, pairs: list[Pair], out_path: Path) -> str:
    """O relatório da importação em texto (sem dado pessoal): contagens, motivos e pares com o catálogo atual."""
    lines = [
        f"Linhas lidas: {report.rows_read}",
        f"Registros gerados: {len(report.records)} (em {out_path})",
        *_section("Ignoradas", [f"{label}: {reason}" for label, reason in report.ignored]),
        *_section("Candidate", [f"{entry_id}: {reason}" for entry_id, reason in report.candidates]),
        *_section("Área no padrão", [f"{entry_id}: macro-categoria {category!r}" for entry_id, category in report.default_area]),
        *_section("Pares com o catálogo atual", [f"{p.imported_id} x {p.existing_id}" for p in pairs]),
    ]
    return "\n".join(lines)
