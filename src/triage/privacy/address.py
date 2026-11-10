"""Anonimização de endereço: logradouro com nome próprio, número e complementos."""

from triage.privacy.patterns import ADDRESS_MARKER, ADDRESS_PATTERN
from triage.privacy.substitution import substitute


def mask_addresses(text: str) -> tuple[str, int]:
    """Troca cada logradouro com nome próprio (e o número e complementos que o seguem) por `[ENDERECO]`.

    "Rua" ou "buraco na rua" sem nome próprio não são mascarados; cidade, estado e bairro também não.
    """
    return substitute(ADDRESS_PATTERN, ADDRESS_MARKER, text)
