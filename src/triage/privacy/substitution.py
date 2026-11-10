"""Substituição de um padrão por marcador, contando só as trocas que de fato ocorreram."""

import re
from collections.abc import Callable


def substitute(
    pattern: re.Pattern[str],
    marker: str | None,
    text: str,
    replacer: Callable[[re.Match[str]], str] | None = None,
) -> tuple[str, int]:
    """Aplica `pattern` e conta só as trocas que de fato viraram marcador."""
    replaced = 0

    def swap(match: re.Match[str]) -> str:
        nonlocal replaced
        result = replacer(match) if replacer else marker
        if result != match.group():
            replaced += 1
        return result

    return pattern.sub(swap, text), replaced
