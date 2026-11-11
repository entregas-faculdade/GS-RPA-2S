"""Validação da saída do LLM: só passa texto ancorado nas fontes enviadas, sem link nem telefone inventado."""

import re
from collections.abc import Sequence
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
REJECT_MISSING_ANCHOR = "missing_anchor"


def _urls_in(text: str) -> list[str]:
    """URLs do texto, sem a pontuação final de frase colada ao link."""
    return [match.rstrip(TRAILING_PUNCTUATION) for match in URL_PATTERN.findall(text)]


def _source_hosts(sources: Sequence[ServiceEntry]) -> set[str]:
    return {(urlsplit(link.url).hostname or "").lower() for source in sources for link in source.links}


def _foreign_bare_address(text: str, sources: Sequence[ServiceEntry]) -> bool:
    """Há endereço sem esquema (`golpe.com`, `x.com.br/pagar`) que não é o domínio de um link das fontes nem um domínio pai dele?

    Citar o domínio de um link das fontes ou um pai (`gov.br`) é legítimo; qualquer caminho (`/...`)
    torna o endereço um link, que só vale se for a URL completa de um link das fontes (já tratada em `_urls_in`).
    """
    hosts = _source_hosts(sources)
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


def _source_phones(sources: Sequence[ServiceEntry]) -> set[str]:
    return {re.sub(r"\D", "", phone.number) for source in sources for phone in source.phones}


def _source_text_numbers(sources: Sequence[ServiceEntry]) -> set[str]:
    """Sequências de dígitos do texto oficial das fontes (`instructions` e `content`): números que o LLM pode repetir."""
    texts = [text for source in sources for text in (source.instructions, source.content)]
    return {digits for text in texts for digits in phone_digit_sequences(text)}


def validate_rag_output(text: str, sources: Sequence[ServiceEntry]) -> str | None:
    """Devolve o motivo da rejeição, ou `None` se a saída serve.

    Rejeita texto vazio, acima de `MAX_RESPONSE_LENGTH`, com URL que não seja de um link das fontes
    (igualdade exata), com número de 3+ dígitos que não seja telefone das fontes nem apareça no texto oficial delas
    (`instructions`, `content`) ou sem nenhum link nem telefone delas.
    """
    if not text or not text.strip():
        return REJECT_EMPTY
    if len(text) > MAX_RESPONSE_LENGTH:
        return REJECT_TOO_LONG
    urls = _urls_in(text)
    source_urls = {link.url for source in sources for link in source.links}
    if any(url not in source_urls for url in urls) or _foreign_bare_address(text, sources):
        return REJECT_FOREIGN_URL
    phones = _source_phones(sources)
    mentioned = phone_digit_sequences(text)
    allowed_numbers = phones | _source_text_numbers(sources)
    if any(digits not in allowed_numbers for digits in mentioned):
        return REJECT_FOREIGN_PHONE
    if source_urls.isdisjoint(urls) and phones.isdisjoint(mentioned):
        return REJECT_MISSING_ANCHOR
    return None
