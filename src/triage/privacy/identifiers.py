"""Anonimização de identificadores numéricos: CEP, RG, documentos e datas completas."""

import re

from triage.privacy.patterns import (
    CNPJ_PUNCTUATED_PATTERN,
    DATE_MARKER,
    DATE_PATTERN,
    DOCUMENT_LABELED_PATTERN,
    DOCUMENT_MARKER,
    KIND_DATE,
    KIND_DOCUMENT,
    KIND_POSTAL_CODE,
    KIND_RG,
    POSTAL_CODE_LABELED_PATTERN,
    POSTAL_CODE_MARKER,
    POSTAL_CODE_PATTERN,
    RG_FORMAT_PATTERN,
    RG_LABELED_PATTERN,
    RG_MARKER,
)
from triage.privacy.substitution import substitute

MIN_DOCUMENT_DIGITS = 9
MAX_DOCUMENT_DIGITS = 15


def _keep_label(marker: str):
    """Troca só o número (grupo 2 ou o que vem após o rótulo do grupo 1) e preserva o rótulo."""

    def replace(match: re.Match[str]) -> str:
        return match.group(1) + marker

    return replace


def _replace_labeled_document(match: re.Match[str]) -> str:
    digits = sum(char.isdigit() for char in match.group(2))
    if MIN_DOCUMENT_DIGITS <= digits <= MAX_DOCUMENT_DIGITS:
        return match.group(1) + DOCUMENT_MARKER
    return match.group()


def _mask_postal_codes(text: str) -> tuple[str, int]:
    text, formatted = substitute(POSTAL_CODE_PATTERN, POSTAL_CODE_MARKER, text)
    text, labeled = substitute(POSTAL_CODE_LABELED_PATTERN, None, text, _keep_label(POSTAL_CODE_MARKER))
    return text, formatted + labeled


def _mask_rgs(text: str) -> tuple[str, int]:
    text, labeled = substitute(RG_LABELED_PATTERN, None, text, _keep_label(RG_MARKER))
    text, formatted = substitute(RG_FORMAT_PATTERN, RG_MARKER, text)
    return text, labeled + formatted


def _mask_documents(text: str) -> tuple[str, int]:
    text, cnpjs = substitute(CNPJ_PUNCTUATED_PATTERN, DOCUMENT_MARKER, text)
    text, labeled = substitute(DOCUMENT_LABELED_PATTERN, None, text, _replace_labeled_document)
    return text, cnpjs + labeled


def mask_identifiers(text: str) -> tuple[str, dict[str, int]]:
    """Troca documentos, CEP, RG e datas completas por marcador e devolve a contagem por tipo."""
    text, documents = _mask_documents(text)
    text, postal_codes = _mask_postal_codes(text)
    text, rgs = _mask_rgs(text)
    text, dates = substitute(DATE_PATTERN, DATE_MARKER, text)
    counts = {KIND_DOCUMENT: documents, KIND_POSTAL_CODE: postal_codes, KIND_RG: rgs, KIND_DATE: dates}
    return text, counts
