"""Resolução de categoria em serviço do catálogo, só com fonte aprovada e links permitidos e no ar."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from triage.automation.allowlist import is_allowed, load_allowed_suffixes
from triage.automation.catalog import (
    KIND_SERVICE,
    Link,
    ServiceEntry,
    approved_only,
    load_catalog,
)
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
        catalog: Sequence[ServiceEntry],
        allowed_suffixes: frozenset[str],
        link_checker: Callable[[str], LinkStatus] = check_link,
    ) -> None:
        self._catalog = tuple(catalog)
        self._allowed_suffixes = allowed_suffixes
        self._link_checker = link_checker
        self._link_cache: dict[str, LinkStatus] = {}

    def _check_once(self, url: str) -> LinkStatus:
        if url not in self._link_cache:
            self._link_cache[url] = self._link_checker(url)
        return self._link_cache[url]

    def _link_is_usable(self, entry: ServiceEntry, link: Link) -> bool:
        if not is_allowed(link.url, self._allowed_suffixes):
            logger.error("Defeito no catálogo: link de %s fora da allowlist", entry.id)
            return False
        status = self._check_once(link.url)
        if not status.ok:
            logger.warning("Link de %s indisponível (%s)", entry.id, status.error)
        return status.ok

    def approved_entries(self) -> list[ServiceEntry]:
        """As entradas `approved`, para o localizador."""
        return approved_only(list(self._catalog))

    def resolve_entry(self, entry: ServiceEntry) -> Resolution:
        """Verifica a entrada e a devolve só com os links vivos; sem nenhum link vivo, `link_unavailable`.

        Entrada só com telefones (sem link) é aceita sem verificação de rede.
        """
        live_links = tuple(link for link in entry.links if self._link_is_usable(entry, link))
        if entry.links and not live_links:
            return Resolution(None, REASON_LINK_UNAVAILABLE)
        return Resolution(replace(entry, links=live_links), None)

    def resolve(self, category: str) -> Resolution:
        """Devolve o serviço da categoria, ou `Resolution(None, motivo)`; nunca levanta exceção de rede."""
        if category == OTHER_CATEGORY:
            return Resolution(None, REASON_OUT_OF_CATALOG)
        entry = next(
            (item for item in self.approved_entries() if item.category == category and item.kind == KIND_SERVICE),
            None,
        )
        if entry is None:
            return Resolution(None, REASON_OUT_OF_CATALOG)
        return self.resolve_entry(entry)


def build_default_lookup() -> CatalogLookup:
    """Monta a consulta com o catálogo e a allowlist versionados em `data/`."""
    return CatalogLookup(load_catalog(), load_allowed_suffixes())


def resolve_service(category: str, lookup: CatalogLookup | None = None) -> Resolution:
    """Resolve a categoria em serviço. Passe o mesmo `lookup` na execução toda para não verificar um link duas vezes."""
    return (lookup or build_default_lookup()).resolve(category)
