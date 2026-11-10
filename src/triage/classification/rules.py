"""Atalhos determinísticos por regex: um conjunto pequeno de padrões de alta precisão por categoria.

Os padrões rodam sobre o texto sem acento e em minúsculas (`fold`), então não levam acento. A categoria
`other` não tem regra: é o que sobra quando nenhum atalho casa.
"""

import re

from triage.classification.preprocessing import fold

CATEGORY_RULES: dict[str, tuple[re.Pattern[str], ...]] = {
    "driver_license": (
        re.compile(r"\bcnh\b"),
        re.compile(r"\bcarteira (?:nacional )?de (?:habilitacao|motorista)\b"),
        re.compile(r"\bprimeira habilitacao\b"),
    ),
    "property_tax": (
        re.compile(r"\biptu\b"),
        re.compile(r"\bimposto predial\b"),
    ),
    "id_card": (
        re.compile(r"\brg\b"),
        re.compile(r"\b(?:carteira|cedula|documento) de identidade\b"),
    ),
    "cpf_registration": (re.compile(r"\bcpf\b"),),
    "voter_id": (
        re.compile(r"\btitulo (?:de )?eleitor\b"),
        re.compile(r"\btitulo eleitoral\b"),
        re.compile(r"\bzona eleitoral\b"),
    ),
    "social_benefits": (
        re.compile(r"\bcad ?unico\b"),
        re.compile(r"\bbolsa familia\b"),
    ),
    "social_security": (
        re.compile(r"\binss\b"),
        re.compile(r"\baposentadoria\b"),
        re.compile(r"\bprevidencia social\b"),
    ),
    "birth_certificate": (re.compile(r"\bcertidao de (?:nascimento|casamento|obito)\b"),),
}


def match_categories(text: str) -> frozenset[str]:
    """Devolve as categorias cujas regras casam com o texto (vazio se nenhuma casar)."""
    folded = fold(text)
    return frozenset(
        category
        for category, patterns in CATEGORY_RULES.items()
        if any(pattern.search(folded) for pattern in patterns)
    )
