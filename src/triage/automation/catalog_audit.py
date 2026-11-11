"""Auditoria do catálogo (catálogo + base enriquecida): esquema, `content`, allowlist, links, telefones e idade. Nunca altera nada."""

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date

import requests

from triage.automation.allowlist import is_allowed
from triage.automation.catalog import (
    DEFAULT_MAX_AGE_DAYS,
    STATUS_APPROVED,
    CatalogRecordError,
    Link,
    ServiceEntry,
    manual_check_valid,
    parse_entry,
)
from triage.automation.link_check import HTTP_FORBIDDEN, LinkStatus
from triage.automation.response_guard import phone_digit_sequences
from triage.config import DEFAULT_LINK_CHECK_USER_AGENT

LEVEL_OK = "ok"
LEVEL_WARNING = "warning"
LEVEL_ERROR = "error"
PAGE_TIMEOUT_SECONDS = 10.0
MAX_PAGE_CHARS = 2_000_000
TAG_PATTERN = re.compile(r"<[^>]+>")

logger = logging.getLogger("triage.automation")


@dataclass(frozen=True)
class Check:
    """Resultado de uma verificação sobre uma entrada (`level`: ok, warning ou error); `source` é o arquivo de origem."""

    entry_id: str
    name: str
    level: str
    detail: str
    source: str = ""


@dataclass(frozen=True)
class AuditOptions:
    """Dependências e limites da auditoria; `offline` pula toda chamada de rede."""

    link_checker: Callable[[str], LinkStatus]
    fetch_page_text: Callable[[str], str | None]
    max_age_days: int = DEFAULT_MAX_AGE_DAYS
    offline: bool = False
    today: date = field(default_factory=date.today)


def fetch_page_text(url: str, user_agent: str = DEFAULT_LINK_CHECK_USER_AGENT) -> str | None:
    """Texto da página (tags removidas), ou `None` se ela não responder; nunca levanta exceção de rede."""
    try:
        response = requests.get(url, timeout=PAGE_TIMEOUT_SECONDS, headers={"User-Agent": user_agent})
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
    """Audita registros crus do catálogo; guarda links, páginas e `id`s já vistos (uma vez por execução, entre arquivos)."""

    def __init__(self, allowed_suffixes: frozenset[str], options: AuditOptions) -> None:
        self._allowed_suffixes = allowed_suffixes
        self._options = options
        self._statuses: dict[str, LinkStatus] = {}
        self._pages: dict[str, str | None] = {}
        self._seen_ids: set[str] = set()

    def audit(self, records: Sequence[object], source: str = "") -> list[Check]:
        """Um resultado por verificação, na ordem dos registros, cada um com o arquivo de origem (`source`)."""
        checks: list[Check] = []
        for index, record in enumerate(records):
            checks.extend(replace(check, source=source) for check in self._audit_record(record, index))
        return checks

    def _audit_record(self, record: object, index: int) -> list[Check]:
        entry_id = _record_id(record, index)
        try:
            entry = parse_entry(record)
        except CatalogRecordError as error:
            return [Check(entry_id, "schema", LEVEL_ERROR, str(error))]
        if entry.id in self._seen_ids:
            return [Check(entry.id, "id", LEVEL_ERROR, "id repetido; o segundo registro é ignorado")]
        self._seen_ids.add(entry.id)
        return [Check(entry.id, "schema", LEVEL_OK, "registro válido e id único"), *self._audit_entry(entry)]

    def _audit_entry(self, entry: ServiceEntry) -> list[Check]:
        checks = self._check_allowlist(entry)
        usable_links = [link for link in entry.links if is_allowed(link.url, self._allowed_suffixes)]
        if not self._options.offline:
            live_urls, link_checks = self._check_links(entry, usable_links)
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

    def _manual_check(self, entry: ServiceEntry, link: Link, status: LinkStatus) -> Check | None:
        """Aviso para link bloqueado ao robô (HTTP 403) que tem atestado manual; `None` se não se aplica."""
        if status.status_code != HTTP_FORBIDDEN or link.manual_check_on is None:
            return None
        if manual_check_valid(link, self._options.today, self._options.max_age_days):
            detail = f"{link.url}: bloqueado ao robô (HTTP 403); atestado manual de {link.manual_check_on}"
        else:
            detail = f"{link.url}: atestado manual de {link.manual_check_on} vencido (limite {self._options.max_age_days} dias)"
        return Check(entry.id, "link", LEVEL_WARNING, detail)

    def _check_links(self, entry: ServiceEntry, links: list[Link]) -> tuple[list[str], list[Check]]:
        """Verifica cada link permitido; devolve os vivos e os resultados (o resumo da entrada vem por último).

        Link com atestado manual vigente conta como utilizável (o resolvedor o aceita), mas não como vivo:
        a página não foi lida, então não confirma telefone.
        """
        live_urls: list[str] = []
        accepted = 0
        checks: list[Check] = []
        for link in links:
            status = self._status(link.url)
            manual = self._manual_check(entry, link, status)
            if status.ok:
                live_urls.append(link.url)
                checks.append(Check(entry.id, "link", LEVEL_OK, f"{link.url}: responde"))
            elif manual is not None:
                accepted += manual_check_valid(link, self._options.today, self._options.max_age_days)
                checks.append(manual)
            else:
                checks.append(Check(entry.id, "link", LEVEL_WARNING, f"{link.url}: {status.error}"))
        checks.extend(self._links_summary(entry, len(live_urls) + accepted))
        return live_urls, checks

    @staticmethod
    def _links_summary(entry: ServiceEntry, usable: int) -> list[Check]:
        if entry.links and not usable:
            level = LEVEL_ERROR if entry.status == STATUS_APPROVED else LEVEL_WARNING
            return [Check(entry.id, "links", level, "nenhum link vivo")]
        if usable < len(entry.links):
            return [Check(entry.id, "links", LEVEL_WARNING, f"{usable} de {len(entry.links)} links vivos")]
        return []

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


def audit_catalog_files(
    files: Sequence[tuple[str, Sequence[object]]], allowed_suffixes: frozenset[str], options: AuditOptions
) -> list[Check]:
    """Audita vários arquivos (`(nome, registros)`, em ordem) como um conjunto: `id` repetido entre arquivos é erro."""
    auditor = CatalogAuditor(allowed_suffixes, options)
    return [check for name, records in files for check in auditor.audit(records, name)]


def has_errors(checks: Sequence[Check]) -> bool:
    """Alguma verificação terminou em erro?"""
    return any(check.level == LEVEL_ERROR for check in checks)
