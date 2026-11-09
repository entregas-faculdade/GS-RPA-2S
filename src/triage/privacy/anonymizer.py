"""Anonimização de dados pessoais: troca CPF, telefone e e-mail por marcadores.

Limites declarados: cobre apenas CPF, telefone brasileiro e e-mail. Nomes de pessoas, endereços,
RG e outros identificadores NÃO são anonimizados (risco residual).

Decisão sobre CPF: 11 dígitos soltos só são CPF se os dígitos verificadores forem válidos; o formato
pontuado (000.000.000-00) é sempre CPF. Assim, protocolos e códigos de 11 dígitos não são apagados.

Só o texto devolvido por `anonymize` pode ser logado, gravado ou enviado a uma API. A função é pura,
não registra o texto em log e é idempotente (os marcadores não contêm dígitos nem `@`).
"""

import re
from dataclasses import dataclass

from triage.privacy.patterns import (
    CPF_MARKER,
    CPF_PATTERN,
    CPF_PUNCTUATED_PATTERN,
    EMAIL_MARKER,
    EMAIL_PATTERN,
    PHONE_MARKER,
    PHONE_PATTERN,
)
from triage.privacy.validators import is_valid_cpf

KIND_CPF = "cpf"
KIND_PHONE = "phone"
KIND_EMAIL = "email"


@dataclass(frozen=True)
class AnonymizationResult:
    """Texto sem PII e a contagem de ocorrências substituídas por tipo."""

    text: str
    counts: dict[str, int]


def _replace_cpf(match: re.Match[str]) -> str:
    value = match.group()
    if CPF_PUNCTUATED_PATTERN.fullmatch(value) or is_valid_cpf(value):
        return CPF_MARKER
    return value


def _substitute(pattern: re.Pattern[str], marker: str | None, text: str, replacer=None) -> tuple[str, int]:
    """Aplica `pattern` e conta só as trocas que de fato viraram marcador."""
    replaced = 0

    def swap(match: re.Match[str]) -> str:
        nonlocal replaced
        result = replacer(match) if replacer else marker
        if result != match.group():
            replaced += 1
        return result

    return pattern.sub(swap, text), replaced


def anonymize(text: str) -> AnonymizationResult:
    """Substitui e-mail, CPF e telefone (nesta ordem) por marcadores e conta cada tipo."""
    text, emails = _substitute(EMAIL_PATTERN, EMAIL_MARKER, text)
    text, cpfs = _substitute(CPF_PATTERN, None, text, _replace_cpf)
    text, phones = _substitute(PHONE_PATTERN, PHONE_MARKER, text)
    return AnonymizationResult(text, {KIND_CPF: cpfs, KIND_PHONE: phones, KIND_EMAIL: emails})
