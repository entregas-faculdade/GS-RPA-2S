"""Testes da leitura de configuração."""

from pathlib import Path

import pytest

from triage.config import (
    DEFAULT_LINK_CHECK_USER_AGENT,
    FINDER_MARGIN,
    FINDER_MIN_SCORE,
    load_settings,
)

ENV_KEYS = (
    "LLM_ENABLED",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_AGENT_ID",
    "LLM_FALLBACK_MODELS",
    "LOG_LEVEL",
    "LINK_CHECK_USER_AGENT",
    "FINDER_MIN_SCORE",
    "FINDER_MARGIN",
)


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


def test_finder_thresholds_default_when_unset(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.env")

    assert settings.finder_min_score == FINDER_MIN_SCORE
    assert settings.finder_margin == FINDER_MARGIN


def test_finder_thresholds_come_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FINDER_MIN_SCORE", "0.4")
    monkeypatch.setenv("FINDER_MARGIN", " 0.2 ")

    settings = load_settings(tmp_path / "missing.env")

    assert settings.finder_min_score == 0.4
    assert settings.finder_margin == 0.2


INVALID_FINDER_VALUES = [
    (name, raw_value)
    for name in ("FINDER_MIN_SCORE", "FINDER_MARGIN")
    for raw_value in ("abc", "1.5", "-0.1", "nan")
]


@pytest.mark.parametrize("invalid", INVALID_FINDER_VALUES)
def test_invalid_finder_threshold_falls_back_to_the_default_with_a_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture, invalid: tuple[str, str]
) -> None:
    name, raw_value = invalid
    monkeypatch.setenv(name, raw_value)

    with caplog.at_level("WARNING", logger="triage.config"):
        settings = load_settings(tmp_path / "missing.env")

    assert (settings.finder_min_score, settings.finder_margin) == (FINDER_MIN_SCORE, FINDER_MARGIN)
    assert name in caplog.text


@pytest.mark.parametrize("raw_value", ["0", "1"])
def test_finder_thresholds_accept_the_range_limits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, raw_value: str) -> None:
    monkeypatch.setenv("FINDER_MIN_SCORE", raw_value)

    assert load_settings(tmp_path / "missing.env").finder_min_score == float(raw_value)


def test_llm_agent_and_fallback_models_default_when_unset(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.env")

    assert settings.llm_agent_id == "triage-assistant"
    assert settings.llm_fallback_models == ()


def test_llm_agent_id_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_AGENT_ID", " outro-agente ")
    assert load_settings(tmp_path / "missing.env").llm_agent_id == "outro-agente"


def test_blank_llm_agent_id_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LLM_AGENT_ID", "  ")
    assert load_settings(tmp_path / "missing.env").llm_agent_id == "triage-assistant"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("", ()),
        (" , ,", ()),
        ("modelo-a", ("modelo-a",)),
        ("modelo-a, modelo-b ,modelo-c", ("modelo-a", "modelo-b", "modelo-c")),
        ("modelo-a,,modelo-b,", ("modelo-a", "modelo-b")),
    ],
)
def test_fallback_models_are_a_trimmed_comma_separated_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, raw_value: str, expected: tuple[str, ...]
) -> None:
    monkeypatch.setenv("LLM_FALLBACK_MODELS", raw_value)
    assert load_settings(tmp_path / "missing.env").llm_fallback_models == expected
