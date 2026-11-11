"""Leitura única da configuração do robô: `config/settings.json` (versionado) e a chave do LLM (`.env`)."""

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from triage.agent import DEFAULT_AGENT_ID

logger = logging.getLogger("triage.config")

DEFAULT_DOTENV_PATH = Path(".env")
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "settings.json"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_LEVEL = "INFO"
CONFIDENCE_MIN = 0.60
AMBIGUITY_MARGIN = 0.15
FINDER_MIN_SCORE = 0.25
FINDER_MARGIN = 0.15
DEFAULT_LINK_CHECK_USER_AGENT = "GS-RPA-Triagem/1.0 (projeto academico FIAP)"


class ConfigError(Exception):
    """Arquivo de configuração ausente, ilegível ou com JSON inválido: o robô não deve subir."""


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


def _read_config(config_path: Path) -> dict[str, Any]:
    """Lê o JSON de configuração; qualquer falha de leitura ou de formato vira `ConfigError`."""
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"Não foi possível ler a configuração em {config_path}") from error
    except ValueError as error:
        raise ConfigError(f"A configuração em {config_path} não é um JSON válido") from error
    if not isinstance(data, dict):
        raise ConfigError(f"A configuração em {config_path} deve ser um objeto JSON")
    return data


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    section = data.get(name)
    return section if isinstance(section, dict) else {}


def _pick(section: dict[str, Any], label: str, default: Any, is_valid: Callable[[Any], bool]) -> Any:
    """Valor do campo (`label` = `secao.campo`) se válido; ausente ou inválido volta ao padrão, com aviso."""
    key = label.rsplit(".", 1)[-1]
    value = section.get(key)
    if key in section and is_valid(value):
        return value
    logger.warning("Configuração ausente ou inválida em %s; usando o padrão %r", label, default)
    return default


def _is_text(value: Any) -> bool:
    return isinstance(value, str)


def _is_filled_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_flag(value: Any) -> bool:
    return isinstance(value, bool)


def _is_threshold(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0


def _is_text_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _text(section: dict[str, Any], label: str, default: str, *, required: bool = False) -> str:
    """Texto sem espaços nas pontas; com `required`, texto em branco também volta ao padrão."""
    return _pick(section, label, default, _is_filled_text if required else _is_text).strip()


def _flag(section: dict[str, Any], label: str, default: bool) -> bool:
    return _pick(section, label, default, _is_flag)


def _threshold(section: dict[str, Any], label: str, default: float) -> float:
    return float(_pick(section, label, default, _is_threshold))


def _text_list(section: dict[str, Any], label: str) -> tuple[str, ...]:
    """Lista de textos, sem espaços nas pontas e sem itens vazios; ausente ou inválida volta a vazia."""
    items = _pick(section, label, [], _is_text_list)
    return tuple(item.strip() for item in items if item.strip())


def _llm_settings(data: dict[str, Any]) -> dict[str, Any]:
    llm = _section(data, "llm")
    return {
        "llm_enabled": _flag(llm, "llm.enabled", False),
        "llm_base_url": _text(llm, "llm.base_url", ""),
        "llm_model": _text(llm, "llm.model", ""),
        "llm_agent_id": _text(llm, "llm.agent_id", DEFAULT_AGENT_ID, required=True),
        "llm_fallback_models": _text_list(llm, "llm.fallback_models"),
    }


def _tuning_settings(data: dict[str, Any]) -> dict[str, Any]:
    triage = _section(data, "triage")
    finder = _section(data, "finder")
    link_check = _section(data, "link_check")
    return {
        "confidence_min": _threshold(triage, "triage.confidence_min", CONFIDENCE_MIN),
        "ambiguity_margin": _threshold(triage, "triage.ambiguity_margin", AMBIGUITY_MARGIN),
        "finder_min_score": _threshold(finder, "finder.min_score", FINDER_MIN_SCORE),
        "finder_margin": _threshold(finder, "finder.margin", FINDER_MARGIN),
        "link_check_user_agent": _text(
            link_check, "link_check.user_agent", DEFAULT_LINK_CHECK_USER_AGENT, required=True
        ),
    }


def load_settings(dotenv_path: Path = DEFAULT_DOTENV_PATH, config_path: Path = DEFAULT_CONFIG_PATH) -> Settings:
    """Lê o JSON de configuração e a chave do LLM (`.env` ou ambiente); só `LLM_API_KEY` vem do ambiente.

    Arquivo de configuração ausente ou inválido levanta `ConfigError`; o `.env` ausente não é erro.
    """
    load_dotenv(dotenv_path=dotenv_path)
    data = _read_config(config_path)
    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        log_level=_text(data, "log_level", DEFAULT_LOG_LEVEL, required=True),
        output_dir=DEFAULT_OUTPUT_DIR,
        **_llm_settings(data),
        **_tuning_settings(data),
    )
