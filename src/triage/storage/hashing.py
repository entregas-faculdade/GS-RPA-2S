"""Hash de idempotência do pedido."""

import hashlib
import unicodedata


def normalize_text(text: str) -> str:
    """Normaliza Unicode (NFC), espaços e caixa, para que variações triviais gerem o mesmo hash."""
    composed = unicodedata.normalize("NFC", text)
    return " ".join(composed.split()).casefold()


def request_hash(anonymized_text: str) -> str:
    """SHA-256 (hex) do texto já anonimizado e normalizado; é a chave de idempotência do pedido."""
    return hashlib.sha256(normalize_text(anonymized_text).encode("utf-8")).hexdigest()
