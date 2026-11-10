"""Normalização determinística do texto antes das regras e do TF-IDF."""

import re
import unicodedata

from triage.privacy.patterns import CPF_MARKER, EMAIL_MARKER, PHONE_MARKER

# Marcadores da anonimização dizem que houve um dado pessoal, não qual é o assunto: se virassem
# token, "[CPF]" em qualquer pedido pareceria um pedido sobre CPF.
_MARKERS_PATTERN = re.compile("|".join(re.escape(marker) for marker in (CPF_MARKER, PHONE_MARKER, EMAIL_MARKER)))
_NON_WORD_PATTERN = re.compile(r"[^a-z0-9]+")

# Stopwords curtas, já sem acento (a normalização remove os acentos antes do filtro).
PT_BR_STOPWORDS = frozenset(
    {
        "a", "o", "as", "os", "um", "uma", "uns", "umas",
        "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos",
        "e", "ou", "que", "se", "com", "por", "para", "pra", "ao", "aos",
        "eu", "me", "meu", "minha", "meus", "minhas", "tenho", "tem",
        "como", "qual", "onde", "quero", "preciso", "gostaria", "saber",
        "boa", "bom", "dia", "tarde", "noite", "oi", "ola",
    }
)  # fmt: skip


def fold(text: str) -> str:
    """Minúsculas, sem acentos e sem marcadores de anonimização; mantém pontuação e espaços."""
    without_markers = _MARKERS_PATTERN.sub(" ", text)
    decomposed = unicodedata.normalize("NFKD", without_markers.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize(text: str) -> str:
    """Devolve os tokens do texto, em minúsculas, sem acento, pontuação e stopwords, separados por espaço."""
    tokens = _NON_WORD_PATTERN.sub(" ", fold(text)).split()
    return " ".join(token for token in tokens if token not in PT_BR_STOPWORDS)
