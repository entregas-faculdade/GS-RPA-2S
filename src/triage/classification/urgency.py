"""Detecção de urgência/sensibilidade por léxico: pedido urgente nunca é respondido sozinho."""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from triage.classification.preprocessing import fold

URGENCY_TERMS_PATH = Path("data") / "urgency_terms.json"

logger = logging.getLogger("triage.classification")


@lru_cache(maxsize=None)
def _load_pattern(terms_path: Path) -> re.Pattern[str] | None:
    """Compila o léxico numa regex de palavra/expressão inteira; devolve `None` se não puder ser lido."""
    try:
        terms = json.loads(terms_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.error("Léxico de urgência indisponível (%s): %s", terms_path, error)
        return None
    if not isinstance(terms, list):
        logger.error("Léxico de urgência inválido (esperava uma lista): %s", terms_path)
        return None
    folded_terms = [fold(term).strip() for term in terms if isinstance(term, str) and term.strip()]
    if not folded_terms:
        logger.error("Léxico de urgência inválido ou vazio: %s", terms_path)
        return None
    alternatives = "|".join(re.escape(term) for term in folded_terms)
    return re.compile(rf"\b(?:{alternatives})\b")


def is_urgent(text: str, terms_path: Path = URGENCY_TERMS_PATH) -> bool:
    """Diz se o texto contém termo de urgência ou sensibilidade.

    Falha segura: se o léxico estiver ausente ou inválido, devolve `True` (na dúvida, revisão humana).
    """
    pattern = _load_pattern(terms_path)
    if pattern is None:
        return True
    return pattern.search(fold(text)) is not None
