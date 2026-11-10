"""Resolução de categoria em serviço do catálogo, só com link permitido e no ar."""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from triage.automation.allowlist import is_allowed, load_allowed_suffixes
from triage.automation.catalog import ServiceEntry, load_catalog
from triage.automation.link_check import LinkStatus, check_link

REASON_OUT_OF_CATALOG = "out_of_catalog"
REASON_LINK_UNAVAILABLE = "link_unavailable"
OTHER_CATEGORY = "other"

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class Resolution:
    """Serviço resolvido (`reason` é `None`) ou, na falha, `service` é `None` e `reason` diz a causa."""

    service: ServiceEntry | None
    reason: str | None


class CatalogLookup:
    """Consulta o catálogo; guarda o resultado de cada link verificado, uma vez por instância (uma execução)."""

    def __init__(
        self,
        catalog: Mapping[str, ServiceEntry],
        allowed_suffixes: frozenset[str],
        link_checker: Callable[[str], LinkStatus] = check_link,
    ) -> None:
        self._catalog = catalog
        self._allowed_suffixes = allowed_suffixes
        self._link_checker = link_checker
        self._link_cache: dict[str, LinkStatus] = {}

    def _check_once(self, url: str) -> LinkStatus:
        if url not in self._link_cache:
            self._link_cache[url] = self._link_checker(url)
        return self._link_cache[url]

    def resolve(self, category: str) -> Resolution:
        """Devolve o serviço da categoria, ou `Resolution(None, motivo)`; nunca levanta exceção de rede."""
        service = self._catalog.get(category)
        if category == OTHER_CATEGORY or service is None:
            return Resolution(None, REASON_OUT_OF_CATALOG)
        if not is_allowed(service.url, self._allowed_suffixes):
            logger.error("Defeito no catálogo: URL de %s fora da allowlist", category)
            return Resolution(None, REASON_LINK_UNAVAILABLE)
        status = self._check_once(service.url)
        if not status.ok:
            logger.warning("Link de %s indisponível (%s)", category, status.error)
            return Resolution(None, REASON_LINK_UNAVAILABLE)
        return Resolution(service, None)


def build_default_lookup() -> CatalogLookup:
    """Monta a consulta com o catálogo e a allowlist versionados em `data/`."""
    return CatalogLookup(load_catalog(), load_allowed_suffixes())


def resolve_service(category: str, lookup: CatalogLookup | None = None) -> Resolution:
    """Resolve a categoria em serviço. Passe o mesmo `lookup` na execução toda para não verificar um link duas vezes."""
    return (lookup or build_default_lookup()).resolve(category)
