"""Configuração do log em arquivo e console, sem vazar a chave de API."""

import logging
from pathlib import Path

from triage.config import DEFAULT_LOG_LEVEL, Settings

LOGGER_NAME = "triage"
LOG_SUBDIR = "logs"
LOG_FILENAME = "run.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
REDACTION_PLACEHOLDER = "***"


class _SecretMaskFilter(logging.Filter):
    """Troca o segredo, se aparecer numa mensagem, por uma máscara."""

    def __init__(self, secret: str) -> None:
        super().__init__()
        self._secret = secret

    def filter(self, record: logging.LogRecord) -> bool:
        if self._secret:
            record.msg = record.getMessage().replace(self._secret, REDACTION_PLACEHOLDER)
            record.args = ()
        return True


def _resolve_level(level_name: str) -> int:
    level = logging.getLevelName(level_name.upper())
    if isinstance(level, int):
        return level
    return logging.getLevelName(DEFAULT_LOG_LEVEL)


def shutdown_logging() -> None:
    """Fecha e remove os handlers do robô, liberando o arquivo de log."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def configure_logging(settings: Settings) -> Path:
    """Configura log em `<output_dir>/logs/run.log` e no console; devolve o caminho do arquivo."""
    shutdown_logging()
    log_dir = Path(settings.output_dir) / LOG_SUBDIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILENAME

    formatter = logging.Formatter(LOG_FORMAT)
    secret_filter = _SecretMaskFilter(settings.llm_api_key)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_resolve_level(settings.log_level))
    for handler in (logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(formatter)
        handler.addFilter(secret_filter)
        logger.addHandler(handler)
    return log_path
