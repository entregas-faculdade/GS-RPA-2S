"""Conteúdo do catálogo versionado (piloto São Paulo): integridade dos dados, sem rede."""

import json
from collections import defaultdict

import pytest

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import CATALOG_PATH, ServiceEntry, load_catalog
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup, resolve_service

APPROVED = "approved"
KEYWORDS_MIN = 5
REQUIRED_AREAS = ("health", "education", "vehicles", "city", "safety")
GOV_BR = frozenset({"gov.br"})

ORIGINAL_CATEGORY_URLS = {
    "driver_license": "https://www.gov.br/pt-br/servicos/emitir-a-carteira-nacional-de-habilitacao-digital-cnh-e",
    "cpf_registration": "https://www.gov.br/pt-br/servicos/inscrever-no-cpf",
    "id_card": "https://www.gov.br/governodigital/pt-br/identidade/cin",
    "birth_certificate": "https://www.gov.br/pt-br/noticias/assistencia-social/2021/11/emissao-gratuita-da-certidao-de-nascimento-e-garantida-por-lei-federal",
    "voter_id": "https://www.gov.br/pt-br/servicos",
    "social_benefits": "https://www.gov.br/mds/pt-br/acoes-e-programas/cadastro-unico",
    "social_security": "https://www.gov.br/inss/pt-br/servicos/aposentadorias",
    "property_tax": "https://www.gov.br/pt-br/servicos",
}

# Termos que podem aparecer em registros de áreas diferentes porque nomeiam o mesmo órgão ou número,
# e não um assunto que o cidadão confundiria. Cada exceção traz o motivo; a lista começa vazia.
SHARED_KEYWORDS_ACROSS_AREAS: dict[str, str] = {}


def _alive(url: str) -> LinkStatus:
    return LinkStatus(True, 200, None)


def _approved() -> list[ServiceEntry]:
    return [entry for entry in load_catalog() if entry.status == APPROVED]


def test_every_record_loads_in_the_v2_format() -> None:
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert len(load_catalog()) == len(records)


def test_ids_are_unique() -> None:
    ids = [record["id"] for record in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))]
    assert len(ids) == len(set(ids))


def test_every_link_of_approved_records_is_in_the_allowlist() -> None:
    for entry in _approved():
        assert all(is_allowed(link.url) for link in entry.links), entry.id


def test_every_approved_record_has_enough_keywords() -> None:
    for entry in _approved():
        assert len(entry.keywords) >= KEYWORDS_MIN, entry.id


@pytest.mark.parametrize("category", sorted(ORIGINAL_CATEGORY_URLS))
def test_original_categories_still_resolve_to_the_same_url(category: str) -> None:
    lookup = CatalogLookup(load_catalog(), GOV_BR, _alive)
    resolution = resolve_service(category, lookup)
    assert resolution.service is not None
    assert resolution.service.links[0].url == ORIGINAL_CATEGORY_URLS[category]


@pytest.mark.parametrize("area", REQUIRED_AREAS)
def test_each_pilot_area_has_an_approved_record(area: str) -> None:
    assert any(entry.area == area for entry in _approved()), area


def test_safety_has_an_approved_record_with_phone() -> None:
    assert any(entry.area == "safety" and entry.phones for entry in _approved())


def test_keywords_are_not_shared_across_areas_except_documented() -> None:
    areas_by_keyword: dict[str, set[str]] = defaultdict(set)
    for entry in load_catalog():
        for keyword in entry.keywords:
            areas_by_keyword[keyword.strip().lower()].add(entry.area)
    shared = {keyword for keyword, areas in areas_by_keyword.items() if len(areas) > 1}
    assert shared - set(SHARED_KEYWORDS_ACROSS_AREAS) == set()
