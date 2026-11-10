"""Fixtures do pacote de automação: fábrica de entradas do catálogo v2 e de registros crus."""

from collections.abc import Callable

import pytest

from triage.automation.catalog import Link, Phone, ServiceEntry

GOOD_URL = "https://www.gov.br/inss"


def _record(**overrides: object) -> dict:
    record: dict = {
        "id": "social_security",
        "category": "social_security",
        "kind": "service",
        "scope": "federal",
        "coverage": "Brasil",
        "area": "social",
        "display_name": "Aposentadoria (INSS)",
        "agency": "INSS",
        "instructions": "Entre com a conta gov.br.",
        "keywords": ["inss", "aposentadoria"],
        "links": [{"label": "Portal do INSS", "url": GOOD_URL}],
        "phones": [],
        "source_note": "fonte",
        "verified_on": "2026-11-09",
        "status": "approved",
    }
    return {**record, **overrides}


@pytest.fixture
def make_record() -> Callable[..., dict]:
    """Fábrica de registro cru válido do catálogo v2, com os campos sobrescritos."""
    return _record


@pytest.fixture
def make_entry() -> Callable[..., ServiceEntry]:
    """Fábrica de `ServiceEntry`: `links` e `phones` aceitam pares `(rótulo, valor)`."""

    def build(
        entry_id: str = "social_security",
        links: tuple[tuple[str, str], ...] = (("Portal do INSS", GOOD_URL),),
        phones: tuple[tuple[str, str], ...] = (),
        **overrides: object,
    ) -> ServiceEntry:
        values: dict = {
            "id": entry_id,
            "category": entry_id,
            "kind": "service",
            "scope": "federal",
            "coverage": "Brasil",
            "area": "social",
            "display_name": "Aposentadoria (INSS)",
            "agency": "INSS",
            "instructions": "Entre com a conta gov.br.",
            "keywords": ("inss",),
            "links": tuple(Link(*pair) for pair in links),
            "phones": tuple(Phone(*pair) for pair in phones),
            "source_note": "fonte",
            "verified_on": "2026-11-09",
            "status": "approved",
        }
        return ServiceEntry(**{**values, **overrides})

    return build
