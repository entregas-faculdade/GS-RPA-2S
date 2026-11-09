"""Leitores de pedidos em txt, csv e json: erro de um arquivo ou registro vira rejeição, nunca exceção."""

import csv
import io
import json
import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from triage.ingestion.models import (
    REASON_EMPTY_FILE,
    REASON_INVALID_CSV,
    REASON_INVALID_JSON,
    REASON_MISSING_TEXT,
    REASON_MISSING_TEXT_COLUMN,
    REASON_TOO_LARGE,
    REASON_UNREADABLE_ENCODING,
    REASON_UNREADABLE_FILE,
    Rejection,
    Request,
)
from triage.ingestion.sanitizer import TextTooLargeError, sanitize, validate

logger = logging.getLogger("triage.ingestion")

# `utf-8-sig` é UTF-8 estrito que também aceita o BOM que o Excel grava em CSV.
FILE_ENCODING = "utf-8-sig"
ID_FIELD = "id"
TEXT_FIELD = "text"

ReadResult = tuple[list[Request], list[Rejection]]


def _build(request_id: str, text: str, source: str) -> Request | Rejection:
    try:
        clean_text = sanitize(text)
    except TextTooLargeError:
        return Rejection(source, REASON_TOO_LARGE)
    request = Request(request_id.strip(), clean_text, source)
    rejection = validate(request)
    return request if rejection is None else rejection


def _split(outcomes: Iterable[Request | Rejection]) -> ReadResult:
    requests: list[Request] = []
    rejections: list[Rejection] = []
    for outcome in outcomes:
        (requests if isinstance(outcome, Request) else rejections).append(outcome)
    return requests, rejections


def _load(path: Path) -> str | Rejection:
    """Lê o arquivo inteiro; devolve a rejeição se ele for ilegível ou vazio."""
    try:
        with path.open(encoding=FILE_ENCODING, newline="") as handle:
            content = handle.read()
    except UnicodeDecodeError:
        return Rejection(path.name, REASON_UNREADABLE_ENCODING)
    except OSError:
        return Rejection(path.name, REASON_UNREADABLE_FILE)
    if not content.strip():
        return Rejection(path.name, REASON_EMPTY_FILE)
    return content


def read_txt(path: Path) -> ReadResult:
    """Um pedido por arquivo; o id é o nome do arquivo sem extensão."""
    content = _load(path)
    if isinstance(content, Rejection):
        return [], [content]
    return _split([_build(path.stem, content, path.name)])


def read_csv(path: Path) -> ReadResult:
    """Colunas `id,text`, uma linha por pedido."""
    content = _load(path)
    if isinstance(content, Rejection):
        return [], [content]
    try:
        reader = csv.DictReader(io.StringIO(content, newline=""))
        if TEXT_FIELD not in (reader.fieldnames or []):
            return [], [Rejection(path.name, REASON_MISSING_TEXT_COLUMN)]
        rows = list(reader)
    except csv.Error:
        return [], [Rejection(path.name, REASON_INVALID_CSV)]
    if not rows:
        return [], [Rejection(path.name, REASON_EMPTY_FILE)]
    return _split(
        _build(row.get(ID_FIELD) or "", row.get(TEXT_FIELD) or "", f"{path.name}#{number}")
        for number, row in enumerate(rows, start=1)
    )


def _as_id(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return ""


def _from_json_item(item: object, source: str) -> Request | Rejection:
    if not isinstance(item, dict):
        return Rejection(source, REASON_INVALID_JSON)
    text = item.get(TEXT_FIELD)
    if not isinstance(text, str):
        return Rejection(source, REASON_MISSING_TEXT)
    return _build(_as_id(item.get(ID_FIELD)), text, source)


def read_json(path: Path) -> ReadResult:
    """Lista de objetos `{"id", "text"}` ou um objeto único."""
    content = _load(path)
    if isinstance(content, Rejection):
        return [], [content]
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, RecursionError):
        return [], [Rejection(path.name, REASON_INVALID_JSON)]
    if isinstance(data, dict):
        return _split([_from_json_item(data, path.name)])
    if not isinstance(data, list):
        return [], [Rejection(path.name, REASON_INVALID_JSON)]
    if not data:
        return [], [Rejection(path.name, REASON_EMPTY_FILE)]
    return _split(
        _from_json_item(item, f"{path.name}#{number}") for number, item in enumerate(data, start=1)
    )


READERS: dict[str, Callable[[Path], ReadResult]] = {
    ".txt": read_txt,
    ".csv": read_csv,
    ".json": read_json,
}


def read_folder(path: str | Path) -> ReadResult:
    """Lê todos os arquivos suportados da pasta (sem recursão).

    Pasta inexistente levanta `FileNotFoundError`: quem decide o que fazer é o chamador.
    """
    folder = Path(path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Pasta de entrada não encontrada: {folder}")
    requests: list[Request] = []
    rejections: list[Rejection] = []
    for entry in sorted(folder.iterdir()):
        if not entry.is_file():
            continue
        reader = READERS.get(entry.suffix.lower())
        if reader is None:
            logger.warning("Extensão não suportada, arquivo ignorado: %s", entry.name)
            continue
        file_requests, file_rejections = reader(entry)
        requests.extend(file_requests)
        rejections.extend(file_rejections)
    for rejection in rejections:
        logger.warning("Pedido rejeitado: %s (%s)", rejection.source, rejection.reason)
    return requests, rejections
