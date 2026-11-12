"""Sanitização do texto bruto de um pedido e validação do pedido resultante."""

import re
import unicodedata

from triage.ingestion.models import (
    REASON_EMPTY_ID,
    REASON_TEXT_TOO_SHORT,
    Rejection,
    Request,
)

MAX_TEXT_LENGTH = 2000
MIN_TEXT_LENGTH = 3

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_HTML_COMMENT = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)
# Sem fechamento, o bloco vai até o fim do texto: melhor perder o resto que deixar script passar.
_SCRIPT_BLOCK = re.compile(r"<(script|style)\b[^>]*>.*?(?:</\1\s*>|$)", re.DOTALL | re.IGNORECASE)
# Exige letra, "/" ou "!" após "<" para não apagar comparações como "a < b".
_HTML_TAG = re.compile(r"</?[a-z!][^>]*>", re.IGNORECASE)
_SQL_INJECTION = (
    re.compile(r";\s*--"),
    re.compile(r"'\s*or\s*'1'\s*=\s*'1'?", re.IGNORECASE),
)
_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
_BLANK_LINES = re.compile(r"\n{3,}")


class TextTooLargeError(ValueError):
    """O texto bruto excede `MAX_TEXT_LENGTH`."""


def sanitize(text: str) -> str:
    """Normaliza e neutraliza o texto bruto; levanta `TextTooLargeError` se passar do limite."""
    if len(text) > MAX_TEXT_LENGTH:
        raise TextTooLargeError(f"texto com mais de {MAX_TEXT_LENGTH} caracteres")
    cleaned = unicodedata.normalize("NFKC", text)
    # Controles saem antes das tags para que `<scr\x00ipt>` não escape do filtro.
    cleaned = _CONTROL_CHARS.sub("", cleaned)
    for pattern in (_HTML_COMMENT, _SCRIPT_BLOCK, _HTML_TAG, *_SQL_INJECTION):
        cleaned = pattern.sub(" ", cleaned)
    cleaned = "\n".join(line.strip() for line in _HORIZONTAL_SPACE.sub(" ", cleaned).split("\n"))
    return _BLANK_LINES.sub("\n\n", cleaned).strip()


def validate(request: Request) -> Rejection | None:
    """Devolve a rejeição do pedido já sanitizado, ou `None` se ele é válido."""
    if not request.id.strip():
        return Rejection(request.source, REASON_EMPTY_ID)
    if len(request.text) < MIN_TEXT_LENGTH:
        return Rejection(request.source, REASON_TEXT_TOO_SHORT)
    return None
