"""Repetição de operações com espera exponencial, só para falhas transitórias."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

logger = logging.getLogger("triage.retry")

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Quantas vezes tentar, quanto esperar e quais exceções contam como transitórias."""

    attempts: int
    base_delay: float
    max_delay: float
    transient: tuple[type[BaseException], ...]


def _delay_for(policy: RetryPolicy, attempt: int) -> float:
    """Espera exponencial (`base_delay * 2^(n-1)`) limitada a `max_delay`."""
    return min(policy.base_delay * (2 ** (attempt - 1)), policy.max_delay)


def retry_with_backoff(
    operation: Callable[[], T],
    policy: RetryPolicy,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Executa `operation`, repetindo só quando ela levanta uma exceção transitória.

    Esgotadas as tentativas, a última exceção transitória é relançada; qualquer outra
    exceção sobe de imediato, sem nova tentativa.
    """
    attempts = max(policy.attempts, 1)
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except policy.transient as error:
            if attempt == attempts:
                logger.error("Tentativa %d/%d falhou; desistindo: %s", attempt, attempts, error)
                raise
            delay = _delay_for(policy, attempt)
            logger.warning("Tentativa %d/%d falhou (%s); nova tentativa em %.2fs", attempt, attempts, error, delay)
            sleep(delay)
    raise AssertionError("inalcançável: o laço sempre retorna ou relança")  # pragma: no cover
