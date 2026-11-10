"""Anonimização de dados pessoais: troca CPF, telefone, e-mail, nome, endereço, CEP, RG, data e documentos.

Princípio: na dúvida, mascarar. Falso negativo (dado pessoal que passa) é a falha grave; falso positivo
(palavra comum mascarada) é aceitável quando raro. Cidade, estado e bairro NÃO são mascarados.

Limites declarados (risco residual): nome fora de qualquer contexto e fora da lista de prenomes pode passar;
endereço sem logradouro (só "perto da padaria") passa; cidade e bairro não são mascarados.

Ordem de aplicação (fixa, para um tipo não consumir o dígito de outro): e-mail, CPF, documentos, CEP, RG,
data, endereço, nome e, por último, telefone (o mais ambíguo, que só casa o que sobrou).

Decisão sobre CPF: 11 dígitos soltos só são CPF se os dígitos verificadores forem válidos; o formato
pontuado (000.000.000-00) é sempre CPF. Assim, protocolos e códigos de 11 dígitos não são apagados.

Só o texto devolvido por `anonymize` pode ser logado, gravado ou enviado a uma API. A função é pura,
não registra o texto em log e é idempotente (os marcadores não contêm dígitos nem `@`).
"""

import re
from dataclasses import dataclass

from triage.privacy.address import mask_addresses
from triage.privacy.identifiers import mask_identifiers
from triage.privacy.names import mask_names
from triage.privacy.patterns import (
    CPF_MARKER,
    CPF_PATTERN,
    CPF_PUNCTUATED_PATTERN,
    EMAIL_MARKER,
    EMAIL_PATTERN,
    KIND_ADDRESS,
    KIND_CPF,
    KIND_DATE,
    KIND_DOCUMENT,
    KIND_EMAIL,
    KIND_NAME,
    KIND_PHONE,
    KIND_POSTAL_CODE,
    KIND_RG,
    PHONE_MARKER,
    PHONE_PATTERN,
)
from triage.privacy.substitution import substitute
from triage.privacy.validators import is_valid_cpf

COUNT_KEYS = (
    KIND_CPF,
    KIND_PHONE,
    KIND_EMAIL,
    KIND_NAME,
    KIND_ADDRESS,
    KIND_POSTAL_CODE,
    KIND_RG,
    KIND_DATE,
    KIND_DOCUMENT,
)


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


def anonymize(text: str) -> AnonymizationResult:
    """Substitui os dados pessoais por marcadores, na ordem do docstring do módulo, e conta cada tipo."""
    counts: dict[str, int] = {}
    text, counts[KIND_EMAIL] = substitute(EMAIL_PATTERN, EMAIL_MARKER, text)
    text, counts[KIND_CPF] = substitute(CPF_PATTERN, None, text, _replace_cpf)
    text, identifiers = mask_identifiers(text)
    counts.update(identifiers)
    text, counts[KIND_ADDRESS] = mask_addresses(text)
    text, counts[KIND_NAME] = mask_names(text)
    text, counts[KIND_PHONE] = substitute(PHONE_PATTERN, PHONE_MARKER, text)
    return AnonymizationResult(text, {key: counts[key] for key in COUNT_KEYS})
