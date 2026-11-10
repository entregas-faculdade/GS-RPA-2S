"""Auditoria do catálogo: esquema, allowlist, links, telefones e idade da verificação. Nunca altera o catálogo."""

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date

import requests

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import (
    STATUS_APPROVED,
    CatalogRecordError,
    ServiceEntry,
    parse_entry,
)
from triage.automation.link_check import LinkStatus
from triage.automation.response_guard import phone_digit_sequences

LEVEL_OK = "ok"
LEVEL_WARNING = "warning"
LEVEL_ERROR = "error"
DEFAULT_MAX_AGE_DAYS = 180
PAGE_TIMEOUT_SECONDS = 10.0
MAX_PAGE_CHARS = 2_000_000
TAG_PATTERN = re.compile(r"<[^>]+>")

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class Check:
    """Resultado de uma verificação sobre uma entrada (`level`: ok, warning ou error)."""

    entry_id: str
    name: str
    level: str
    detail: str


@dataclass(frozen=True)
class AuditOptions:
    """Dependências e limites da auditoria; `offline` pula toda chamada de rede."""

    link_checker: Callable[[str], LinkStatus]
    fetch_page_text: Callable[[str], str | None]
    max_age_days: int = DEFAULT_MAX_AGE_DAYS
    offline: bool = False
    today: date = field(default_factory=date.today)


def fetch_page_text(url: str) -> str | None:
    """Texto da página (tags removidas), ou `None` se ela não responder; nunca levanta exceção de rede."""
    try:
        response = requests.get(url, timeout=PAGE_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        logger.warning("Página indisponível para conferir telefone (%s)", type(error).__name__)
        return None
    if not response.ok:
        return None
    return TAG_PATTERN.sub(" ", response.text[:MAX_PAGE_CHARS])


def _record_id(record: object, index: int) -> str:
    if isinstance(record, dict) and isinstance(record.get("id"), str):
        return record["id"]
    return f"#{index + 1}"


class CatalogAuditor:
    """Audita registros crus do catálogo; guarda links e páginas já consultados (uma vez por execução)."""

    def __init__(self, allowed_suffixes: frozenset[str], options: AuditOptions) -> None:
        self._allowed_suffixes = allowed_suffixes
        self._options = options
        self._statuses: dict[str, LinkStatus] = {}
        self._pages: dict[str, str | None] = {}

    def audit(self, records: Sequence[object]) -> list[Check]:
        """Um resultado por verificação, na ordem dos registros."""
        checks: list[Check] = []
        seen_ids: set[str] = set()
        for index, record in enumerate(records):
            entry_id = _record_id(record, index)
            try:
                entry = parse_entry(record)
            except CatalogRecordError as error:
                checks.append(Check(entry_id, "schema", LEVEL_ERROR, str(error)))
                continue
            if entry.id in seen_ids:
                checks.append(Check(entry.id, "id", LEVEL_ERROR, "id repetido; o segundo registro é ignorado"))
                continue
            seen_ids.add(entry.id)
            checks.append(Check(entry.id, "schema", LEVEL_OK, "registro válido e id único"))
            checks.extend(self._audit_entry(entry))
        return checks

    def _audit_entry(self, entry: ServiceEntry) -> list[Check]:
        checks = self._check_allowlist(entry)
        usable_urls = [link.url for link in entry.links if is_allowed(link.url, self._allowed_suffixes)]
        if not self._options.offline:
            live_urls, link_checks = self._check_links(entry, usable_urls)
            checks.extend(link_checks)
            checks.extend(self._check_phones(entry, live_urls))
        checks.append(self._check_age(entry))
        return checks

    def _check_allowlist(self, entry: ServiceEntry) -> list[Check]:
        return [
            Check(entry.id, "allowlist", LEVEL_ERROR, f"link fora da allowlist: {link.url}")
            for link in entry.links
            if not is_allowed(link.url, self._allowed_suffixes)
        ]

    def _status(self, url: str) -> LinkStatus:
        if url not in self._statuses:
            self._statuses[url] = self._options.link_checker(url)
        return self._statuses[url]

    def _page_text(self, url: str) -> str | None:
        if url not in self._pages:
            self._pages[url] = self._options.fetch_page_text(url)
        return self._pages[url]

    def _check_links(self, entry: ServiceEntry, urls: list[str]) -> tuple[list[str], list[Check]]:
        """Verifica cada link permitido; devolve os vivos e os resultados (o resumo da entrada vem por último)."""
        statuses = {url: self._status(url) for url in urls}
        live_urls = [url for url, status in statuses.items() if status.ok]
        checks = [
            Check(entry.id, "link", LEVEL_OK if status.ok else LEVEL_WARNING, f"{url}: {'responde' if status.ok else status.error}")
            for url, status in statuses.items()
        ]
        if entry.links and not live_urls:
            level = LEVEL_ERROR if entry.status == STATUS_APPROVED else LEVEL_WARNING
            checks.append(Check(entry.id, "links", level, "nenhum link vivo"))
        elif len(live_urls) < len(entry.links):
            checks.append(Check(entry.id, "links", LEVEL_WARNING, f"{len(live_urls)} de {len(entry.links)} links vivos"))
        return live_urls, checks

    def _check_phones(self, entry: ServiceEntry, live_urls: list[str]) -> list[Check]:
        """Confere cada telefone no texto das páginas vivas; nunca é erro (a página pode ser dinâmica ou recusar robô)."""
        if not entry.phones:
            return []
        found: set[str] = set()
        for url in live_urls:
            found.update(phone_digit_sequences(self._page_text(url) or ""))
        checks = []
        for phone in entry.phones:
            confirmed = re.sub(r"\D", "", phone.number) in found
            detail = f"{phone.number}: {'confirmado' if confirmed else 'não confirmado'}"
            checks.append(Check(entry.id, "phone", LEVEL_OK if confirmed else LEVEL_WARNING, detail))
        return checks

    def _check_age(self, entry: ServiceEntry) -> Check:
        age_days = (self._options.today - date.fromisoformat(entry.verified_on)).days
        if age_days > self._options.max_age_days:
            detail = f"verificado há {age_days} dias (limite {self._options.max_age_days})"
            return Check(entry.id, "verified_on", LEVEL_WARNING, detail)
        return Check(entry.id, "verified_on", LEVEL_OK, f"verificado há {age_days} dias")


def audit_catalog(records: Sequence[object], allowed_suffixes: frozenset[str], options: AuditOptions) -> list[Check]:
    """Audita os registros crus do catálogo e devolve um resultado por verificação."""
    return CatalogAuditor(allowed_suffixes, options).audit(records)


def has_errors(checks: Sequence[Check]) -> bool:
    """Alguma verificação terminou em erro?"""
    return any(check.level == LEVEL_ERROR for check in checks)
