"""Testes da leitura de configuração."""

from pathlib import Path

import pytest

from triage.config import DEFAULT_LINK_CHECK_USER_AGENT, load_settings

ENV_KEYS = ("LLM_ENABLED", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "LOG_LEVEL", "LINK_CHECK_USER_AGENT")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)


def test_defaults_without_env_file_or_variables(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.env")

    assert settings.llm_enabled is False
    assert settings.llm_base_url == ""
    assert settings.llm_api_key == ""
    assert settings.log_level == "INFO"
    assert settings.output_dir == "output"


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_MODEL", "modelo-x")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings(tmp_path / "missing.env")

    assert settings.llm_enabled is True
    assert settings.llm_model == "modelo-x"
    assert settings.log_level == "DEBUG"


def test_reads_dotenv_file(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("LLM_BASE_URL=http://exemplo.invalido\nLOG_LEVEL=WARNING\n", encoding="utf-8")

    settings = load_settings(dotenv)

    assert settings.llm_base_url == "http://exemplo.invalido"
    assert settings.log_level == "WARNING"


def test_settings_are_immutable(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.env")

    with pytest.raises(AttributeError):
        settings.log_level = "DEBUG"


def test_link_check_user_agent_defaults_to_the_project_name(tmp_path: Path) -> None:
    assert load_settings(tmp_path / "missing.env").link_check_user_agent == DEFAULT_LINK_CHECK_USER_AGENT


def test_link_check_user_agent_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LINK_CHECK_USER_AGENT", " Robo-Teste/1.0 ")
    assert load_settings(tmp_path / "missing.env").link_check_user_agent == "Robo-Teste/1.0"


def test_blank_link_check_user_agent_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LINK_CHECK_USER_AGENT", "   ")
    assert load_settings(tmp_path / "missing.env").link_check_user_agent == DEFAULT_LINK_CHECK_USER_AGENT
