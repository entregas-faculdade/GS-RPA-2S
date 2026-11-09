"""Leitura única da configuração do robô (variáveis de ambiente e `.env`)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DOTENV_PATH = Path(".env")
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_LEVEL = "INFO"
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


def _parse_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in TRUE_VALUES


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
    )
