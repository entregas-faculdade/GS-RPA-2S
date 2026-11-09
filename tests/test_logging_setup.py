"""Testes da configuração de log."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from triage.config import Settings
from triage.logging_setup import configure_logging, shutdown_logging

DUMMY_CREDENTIAL = "chave-ficticia-123"


@pytest.fixture(autouse=True)
def close_logging() -> Iterator[None]:
    yield
    shutdown_logging()


def _settings(output_dir: Path, log_level: str = "INFO") -> Settings:
    return Settings(
        llm_enabled=False,
        llm_base_url="",
        llm_model="",
        llm_api_key=DUMMY_CREDENTIAL,
        log_level=log_level,
        output_dir=str(output_dir),
    )


def test_creates_log_file_and_writes_messages(tmp_path: Path) -> None:
    log_path = configure_logging(_settings(tmp_path / "out"))

    logging.getLogger("triage.teste").info("mensagem de teste")

    assert log_path == tmp_path / "out" / "logs" / "run.log"
    assert "mensagem de teste" in log_path.read_text(encoding="utf-8")


def test_never_writes_api_key(tmp_path: Path) -> None:
    log_path = configure_logging(_settings(tmp_path))

    logging.getLogger("triage.teste").info("chave usada: %s", DUMMY_CREDENTIAL)

    content = log_path.read_text(encoding="utf-8")
    assert DUMMY_CREDENTIAL not in content
    assert "***" in content


def test_log_level_comes_from_settings(tmp_path: Path) -> None:
    log_path = configure_logging(_settings(tmp_path, log_level="WARNING"))

    logging.getLogger("triage.teste").info("ignorada")
    logging.getLogger("triage.teste").warning("registrada")

    content = log_path.read_text(encoding="utf-8")
    assert "ignorada" not in content
    assert "registrada" in content


def test_invalid_level_falls_back_to_info(tmp_path: Path) -> None:
    configure_logging(_settings(tmp_path, log_level="NAO-EXISTE"))

    assert logging.getLogger("triage").level == logging.INFO
