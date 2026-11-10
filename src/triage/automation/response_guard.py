"""Validação da saída do LLM: só passa texto que mantém o link oficial e não inventa outro."""

import re
from urllib.parse import urlsplit

from triage.automation.catalog import ServiceEntry

MAX_RESPONSE_LENGTH = 1200
URL_PATTERN = re.compile(r"https?://[^\s<>\"'\]\[)(]+", re.IGNORECASE)
BARE_ADDRESS_PATTERN = re.compile(
    r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:/[^\s<>\"'\]\[)(]*)?",
    re.IGNORECASE,
)
TRAILING_PUNCTUATION = ".,;:!?"

REJECT_EMPTY = "empty"
REJECT_TOO_LONG = "too_long"
REJECT_FOREIGN_URL = "foreign_url"
REJECT_MISSING_URL = "missing_url"


def _urls_in(text: str) -> list[str]:
    """URLs do texto, sem a pontuação final de frase colada ao link."""
    return [match.rstrip(TRAILING_PUNCTUATION) for match in URL_PATTERN.findall(text)]


def _foreign_bare_address(text: str, service: ServiceEntry) -> bool:
    """Há endereço sem esquema (`golpe.com`, `x.com.br/pagar`) que não é o domínio do serviço nem um domínio pai dele?

    Citar o domínio do serviço ou um pai (`gov.br`) é legítimo; qualquer caminho (`/...`) torna
    o endereço um link, que só vale se for a URL completa do serviço (já tratada em `_urls_in`).
    """
    service_host = (urlsplit(service.url).hostname or "").lower()
    for candidate in BARE_ADDRESS_PATTERN.findall(URL_PATTERN.sub(" ", text)):
        host = candidate.rstrip(TRAILING_PUNCTUATION).lower()
        if "/" in host or not (host == service_host or service_host.endswith("." + host)):
            return True
    return False


def validate_llm_output(text: str, service: ServiceEntry) -> str | None:
    """Devolve o motivo da rejeição, ou `None` se a saída serve.

    Rejeita texto vazio, acima de `MAX_RESPONSE_LENGTH`, com qualquer URL diferente da do
    serviço (igualdade exata) ou sem a URL do serviço.
    """
    if not text or not text.strip():
        return REJECT_EMPTY
    if len(text) > MAX_RESPONSE_LENGTH:
        return REJECT_TOO_LONG
    urls = _urls_in(text)
    if any(url != service.url for url in urls) or _foreign_bare_address(text, service):
        return REJECT_FOREIGN_URL
    if service.url not in urls:
        return REJECT_MISSING_URL
    return None
