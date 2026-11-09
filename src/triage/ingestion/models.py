"""Modelos imutáveis da etapa de ingestão."""

from dataclasses import dataclass

REASON_EMPTY_FILE = "empty_file"
REASON_INVALID_JSON = "invalid_json"
REASON_INVALID_CSV = "invalid_csv"
REASON_MISSING_TEXT_COLUMN = "missing_text_column"
REASON_MISSING_TEXT = "missing_text"
REASON_UNREADABLE_ENCODING = "unreadable_encoding"
REASON_UNREADABLE_FILE = "unreadable_file"
REASON_TOO_LARGE = "too_large"
REASON_EMPTY_ID = "empty_id"
REASON_TEXT_TOO_SHORT = "text_too_short"


@dataclass(frozen=True)
class Request:
    """Pedido válido: `text` já passou pela sanitização; `source` é arquivo ou arquivo#registro."""

    id: str
    text: str
    source: str


@dataclass(frozen=True)
class Rejection:
    """Arquivo ou registro descartado; `reason` é um dos códigos `REASON_*` (nunca o texto do pedido)."""

    source: str
    reason: str
