"""Leitura única da configuração do robô (variáveis de ambiente e `.env`)."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from triage.agent import DEFAULT_AGENT_ID

logger = logging.getLogger("triage.config")

DEFAULT_DOTENV_PATH = Path(".env")
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_LEVEL = "INFO"
CONFIDENCE_MIN = 0.60
AMBIGUITY_MARGIN = 0.15
FINDER_MIN_SCORE = 0.25
FINDER_MARGIN = 0.15
DEFAULT_LINK_CHECK_USER_AGENT = "GS-RPA-Triagem/1.0 (projeto academico FIAP)"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class Settings:
    """Configuração imutável do robô."""

    llm_enabled: bool
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    log_level: str
    output_dir: str
    confidence_min: float = CONFIDENCE_MIN
    ambiguity_margin: float = AMBIGUITY_MARGIN
    finder_min_score: float = FINDER_MIN_SCORE
    finder_margin: float = FINDER_MARGIN
    link_check_user_agent: str = DEFAULT_LINK_CHECK_USER_AGENT
    llm_agent_id: str = DEFAULT_AGENT_ID
    llm_fallback_models: tuple[str, ...] = ()


def _parse_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in TRUE_VALUES


def _parse_list(raw_value: str) -> tuple[str, ...]:
    """Itens separados por vírgula, sem espaços nas pontas e sem vazios."""
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


def _parse_threshold(name: str, default: float) -> float:
    """Lê um limiar em [0, 1] do ambiente; valor ausente, não numérico ou fora da faixa volta ao padrão."""
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        value = -1.0
    if not 0.0 <= value <= 1.0:
        logger.warning("Valor inválido para %s; usando o padrão %s", name, default)
        return default
    return value


def load_settings(dotenv_path: Path = DEFAULT_DOTENV_PATH) -> Settings:
    """Lê o `.env` (se existir) e o ambiente; a ausência do arquivo não é erro."""
    load_dotenv(dotenv_path=dotenv_path)
    return Settings(
        llm_enabled=_parse_bool(os.getenv("LLM_ENABLED", "")),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_model=os.getenv("LLM_MODEL", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        log_level=os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL,
        output_dir=DEFAULT_OUTPUT_DIR,
        confidence_min=_parse_threshold("CONFIDENCE_MIN", CONFIDENCE_MIN),
        ambiguity_margin=_parse_threshold("AMBIGUITY_MARGIN", AMBIGUITY_MARGIN),
        finder_min_score=_parse_threshold("FINDER_MIN_SCORE", FINDER_MIN_SCORE),
        finder_margin=_parse_threshold("FINDER_MARGIN", FINDER_MARGIN),
        link_check_user_agent=os.getenv("LINK_CHECK_USER_AGENT", "").strip() or DEFAULT_LINK_CHECK_USER_AGENT,
        llm_agent_id=os.getenv("LLM_AGENT_ID", "").strip() or DEFAULT_AGENT_ID,
        llm_fallback_models=_parse_list(os.getenv("LLM_FALLBACK_MODELS", "")),
    )
