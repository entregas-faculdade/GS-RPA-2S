"""Verificação de links com timeout e retry: nunca levanta exceção de rede."""

import logging
from dataclasses import dataclass

import requests

from triage.common.retry import RetryPolicy, retry_with_backoff

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 0.5
MAX_BACKOFF_SECONDS = 4.0
HEAD_NOT_IMPLEMENTED = 501
CLIENT_ERROR_MIN = 400
SERVER_ERROR_MIN = 500
OK_STATUS_MIN = 200
OK_STATUS_MAX = 399

logger = logging.getLogger("triage.automation")


class TransientHttpError(Exception):
    """Resposta HTTP 5xx: falha do servidor que vale repetir."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


@dataclass(frozen=True)
class LinkStatus:
    """Resultado da verificação: `ok` só para HTTP 200–399."""

    ok: bool
    status_code: int | None
    error: str | None


def _head_refused(status_code: int) -> bool:
    """HEAD recusado: qualquer 4xx (o gov.br responde 403 ao HEAD e 200 ao GET) ou 501; 5xx comum não conta."""
    return CLIENT_ERROR_MIN <= status_code < SERVER_ERROR_MIN or status_code == HEAD_NOT_IMPLEMENTED


def _probe(url: str, timeout: float) -> int:
    """Uma tentativa: HEAD, com GET se o HEAD for recusado (o GET decide). 5xx vira `TransientHttpError`."""
    response = requests.head(url, timeout=timeout, allow_redirects=True)
    if _head_refused(response.status_code):
        response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
    try:
        status_code = response.status_code
    finally:
        response.close()
    if status_code >= SERVER_ERROR_MIN:
        raise TransientHttpError(status_code)
    return status_code


def check_link(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_ATTEMPTS,
    backoff: float = DEFAULT_BACKOFF_SECONDS,
) -> LinkStatus:
    """Verifica se `url` responde com HTTP 200–399; `retries` é o total de tentativas.

    Timeout, erro de conexão e HTTP 5xx são repetidos com espera exponencial; qualquer
    outra falha encerra na hora. Nunca levanta: o defeito vira `LinkStatus(ok=False, ...)`.
    """
    policy = RetryPolicy(
        attempts=retries,
        base_delay=backoff,
        max_delay=MAX_BACKOFF_SECONDS,
        transient=(requests.Timeout, requests.ConnectionError, TransientHttpError),
    )
    try:
        status_code = retry_with_backoff(lambda: _probe(url, timeout), policy)
    except TransientHttpError as error:
        logger.warning("Link com erro de servidor após %d tentativa(s): %s", retries, error)
        return LinkStatus(ok=False, status_code=error.status_code, error=str(error))
    except requests.RequestException as error:
        logger.warning("Link inacessível (%s)", type(error).__name__)
        return LinkStatus(ok=False, status_code=None, error=type(error).__name__)
    ok = OK_STATUS_MIN <= status_code <= OK_STATUS_MAX
    return LinkStatus(ok=ok, status_code=status_code, error=None if ok else f"HTTP {status_code}")
