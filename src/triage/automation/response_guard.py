"""Validação da saída do LLM: só passa texto que mantém um link oficial e não inventa link nem telefone."""

import re
from urllib.parse import urlsplit

from triage.automation.catalog import ServiceEntry

MAX_RESPONSE_LENGTH = 1200
MIN_PHONE_DIGITS = 3
URL_PATTERN = re.compile(r"https?://[^\s<>\"'\]\[)(]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[^\s<>\"'\]\[)(]+@[^\s<>\"'\]\[)(]+")
BARE_ADDRESS_PATTERN = re.compile(
    r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:/[^\s<>\"'\]\[)(]*)?",
    re.IGNORECASE,
)
DIGIT_SEQUENCE_PATTERN = re.compile(r"\d(?:[\d ()\- ]*\d)?")
TRAILING_PUNCTUATION = ".,;:!?"

REJECT_EMPTY = "empty"
REJECT_TOO_LONG = "too_long"
REJECT_FOREIGN_URL = "foreign_url"
REJECT_FOREIGN_PHONE = "foreign_phone"
REJECT_MISSING_URL = "missing_url"


def _urls_in(text: str) -> list[str]:
    """URLs do texto, sem a pontuação final de frase colada ao link."""
    return [match.rstrip(TRAILING_PUNCTUATION) for match in URL_PATTERN.findall(text)]


def _service_hosts(service: ServiceEntry) -> set[str]:
    return {(urlsplit(link.url).hostname or "").lower() for link in service.links}


def _foreign_bare_address(text: str, service: ServiceEntry) -> bool:
    """Há endereço sem esquema (`golpe.com`, `x.com.br/pagar`) que não é o domínio de um link do serviço nem um domínio pai dele?

    Citar o domínio de um link do serviço ou um pai (`gov.br`) é legítimo; qualquer caminho (`/...`)
    torna o endereço um link, que só vale se for a URL completa de um link do serviço (já tratada em `_urls_in`).
    """
    hosts = _service_hosts(service)
    for candidate in BARE_ADDRESS_PATTERN.findall(URL_PATTERN.sub(" ", text)):
        host = candidate.rstrip(TRAILING_PUNCTUATION).lower()
        if "/" in host or not any(host == known or known.endswith("." + host) for known in hosts):
            return True
    return False


def phone_digit_sequences(text: str) -> list[str]:
    """Dígitos de cada sequência que pode ser telefone (espaço, hífen ou parênteses entre dígitos), com ao menos 3 dígitos.

    URLs e e-mails são ignorados: os números neles não são telefone.
    """
    cleaned = EMAIL_PATTERN.sub(" ", URL_PATTERN.sub(" ", text))
    sequences = (re.sub(r"\D", "", match) for match in DIGIT_SEQUENCE_PATTERN.findall(cleaned))
    return [digits for digits in sequences if len(digits) >= MIN_PHONE_DIGITS]


def _foreign_phone(text: str, service: ServiceEntry) -> bool:
    """Há sequência de dígitos que não é exatamente um telefone do serviço? Na dúvida, sim."""
    known = {re.sub(r"\D", "", phone.number) for phone in service.phones}
    return any(digits not in known for digits in phone_digit_sequences(text))


def validate_llm_output(text: str, service: ServiceEntry) -> str | None:
    """Devolve o motivo da rejeição, ou `None` se a saída serve.

    Rejeita texto vazio, acima de `MAX_RESPONSE_LENGTH`, com URL que não seja de um link do serviço
    (igualdade exata), com telefone que não seja do serviço ou sem nenhuma URL do serviço.
    """
    if not text or not text.strip():
        return REJECT_EMPTY
    if len(text) > MAX_RESPONSE_LENGTH:
        return REJECT_TOO_LONG
    urls = _urls_in(text)
    service_urls = {link.url for link in service.links}
    if any(url not in service_urls for url in urls) or _foreign_bare_address(text, service):
        return REJECT_FOREIGN_URL
    if _foreign_phone(text, service):
        return REJECT_FOREIGN_PHONE
    if service_urls and service_urls.isdisjoint(urls):
        return REJECT_MISSING_URL
    return None
