"""Testes da leitura de configuração: `config/settings.json` e a chave do LLM no ambiente."""

import copy
import importlib.util
import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import triage.config
from triage.config import (
    AMBIGUITY_MARGIN,
    CONFIDENCE_MIN,
    DEFAULT_CONFIG_PATH,
    DEFAULT_LINK_CHECK_USER_AGENT,
    DEFAULT_LOG_LEVEL,
    FINDER_MARGIN,
    FINDER_MIN_SCORE,
    ConfigError,
    Settings,
    load_settings,
)

ROOT = Path(__file__).resolve().parent.parent
OLD_ENV_KEYS = (
    "LLM_ENABLED",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_AGENT_ID",
    "LLM_FALLBACK_MODELS",
    "LLM_ASSIST_LOCATE",
    "LOG_LEVEL",
    "LINK_CHECK_USER_AGENT",
    "CONFIDENCE_MIN",
    "AMBIGUITY_MARGIN",
    "FINDER_MIN_SCORE",
    "FINDER_MARGIN",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (*OLD_ENV_KEYS, "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def missing_env(tmp_path: Path) -> Path:
    return tmp_path / "missing.env"


def _shipped() -> dict[str, Any]:
    return json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))


def _write_config(tmp_path: Path, change: Callable[[dict[str, Any]], None] = lambda data: None) -> Path:
    data = copy.deepcopy(_shipped())
    change(data)
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _load(tmp_path: Path, change: Callable[[dict[str, Any]], None] = lambda data: None) -> Settings:
    return load_settings(tmp_path / "missing.env", _write_config(tmp_path, change))


def test_shipped_config_loads_without_warning(missing_env: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="triage.config"):
        settings = load_settings(missing_env)

    assert caplog.records == []
    assert settings.llm_base_url == "https://openrouter.ai/api/v1"
    assert settings.llm_model == "deepseek/deepseek-v4-flash"
    assert settings.llm_fallback_models == (
        "deepseek/deepseek-v4-flash-0731",
        "deepseek/deepseek-v3.2",
        "minimax/minimax-m3:free",
        "openrouter/free",
    )


def test_shipped_config_equals_the_code_defaults(missing_env: Path) -> None:
    settings = load_settings(missing_env)

    assert settings.llm_enabled is False
    assert settings.llm_assist_locate is False
    assert settings.llm_agent_id == "triage-assistant"
    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert (settings.confidence_min, settings.ambiguity_margin) == (CONFIDENCE_MIN, AMBIGUITY_MARGIN)
    assert (settings.finder_min_score, settings.finder_margin) == (FINDER_MIN_SCORE, FINDER_MARGIN)
    assert settings.link_check_user_agent == DEFAULT_LINK_CHECK_USER_AGENT
    assert settings.output_dir == "output"


def test_shipped_config_is_found_from_another_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing_env: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    assert load_settings(missing_env).llm_model == "deepseek/deepseek-v4-flash"
    assert DEFAULT_CONFIG_PATH == ROOT / "config" / "settings.json"


def test_reads_every_section(tmp_path: Path) -> None:
    def change(data: dict[str, Any]) -> None:
        data["log_level"] = " DEBUG "
        data["llm"].update(
            enabled=True, base_url=" http://x ", model="m", agent_id=" outro ", fallback_models=["a"], assist_locate=True
        )
        data["triage"].update(confidence_min=0.8, ambiguity_margin=0.3)
        data["finder"].update(min_score=0.4, margin=0.2)
        data["link_check"]["user_agent"] = " Robo-Teste/1.0 "

    settings = _load(tmp_path, change)

    assert (settings.log_level, settings.llm_enabled, settings.llm_assist_locate) == ("DEBUG", True, True)
    assert (settings.llm_base_url, settings.llm_model, settings.llm_agent_id) == ("http://x", "m", "outro")
    assert settings.llm_fallback_models == ("a",)
    assert (settings.confidence_min, settings.ambiguity_margin) == (0.8, 0.3)
    assert (settings.finder_min_score, settings.finder_margin) == (0.4, 0.2)
    assert settings.link_check_user_agent == "Robo-Teste/1.0"


def test_settings_are_immutable(missing_env: Path) -> None:
    with pytest.raises(AttributeError):
        load_settings(missing_env).log_level = "DEBUG"


def test_missing_config_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="settings.json") as error:
        load_settings(tmp_path / "missing.env", tmp_path / "settings.json")

    assert isinstance(error.value.__cause__, OSError)


def test_unreadable_config_path_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_settings(tmp_path / "missing.env", tmp_path)


@pytest.mark.parametrize("content", ["", "{", "{'llm': {}}", "isto nao e json"])
def test_invalid_json_raises_config_error_with_the_cause(tmp_path: Path, content: str) -> None:
    config = tmp_path / "settings.json"
    config.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError, match="JSON") as error:
        load_settings(tmp_path / "missing.env", config)

    assert isinstance(error.value.__cause__, ValueError)


def test_json_that_is_not_an_object_raises_config_error(tmp_path: Path) -> None:
    config = tmp_path / "settings.json"
    config.write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(ConfigError, match="objeto"):
        load_settings(tmp_path / "missing.env", config)


FIELD_DEFAULTS = {
    "log_level": ("log_level", "INFO"),
    "llm.enabled": ("llm_enabled", False),
    "llm.base_url": ("llm_base_url", ""),
    "llm.model": ("llm_model", ""),
    "llm.agent_id": ("llm_agent_id", "triage-assistant"),
    "llm.fallback_models": ("llm_fallback_models", ()),
    "llm.assist_locate": ("llm_assist_locate", False),
    "triage.confidence_min": ("confidence_min", CONFIDENCE_MIN),
    "triage.ambiguity_margin": ("ambiguity_margin", AMBIGUITY_MARGIN),
    "finder.min_score": ("finder_min_score", FINDER_MIN_SCORE),
    "finder.margin": ("finder_margin", FINDER_MARGIN),
    "link_check.user_agent": ("link_check_user_agent", DEFAULT_LINK_CHECK_USER_AGENT),
}


def _set_field(data: dict[str, Any], label: str, value: Any) -> None:
    *sections, key = label.split(".")
    target = data
    for section in sections:
        target = target[section]
    target[key] = value


def _drop_field(data: dict[str, Any], label: str) -> None:
    *sections, key = label.split(".")
    target = data
    for section in sections:
        target = target[section]
    del target[key]


@pytest.mark.parametrize("label", FIELD_DEFAULTS)
def test_missing_field_falls_back_to_the_default_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, label: str
) -> None:
    attribute, default = FIELD_DEFAULTS[label]

    with caplog.at_level("WARNING", logger="triage.config"):
        settings = _load(tmp_path, lambda data: _drop_field(data, label))

    assert getattr(settings, attribute) == default
    assert [record.levelname for record in caplog.records] == ["WARNING"]
    assert label in caplog.text


WRONG_TYPES = [
    ("log_level", 5),
    ("llm.enabled", "true"),
    ("llm.enabled", 1),
    ("llm.base_url", 3),
    ("llm.model", None),
    ("llm.agent_id", ["x"]),
    ("llm.agent_id", "   "),
    ("llm.fallback_models", "a,b"),
    ("llm.fallback_models", ["a", 2]),
    ("llm.assist_locate", "false"),
    ("triage.confidence_min", "0.8"),
    ("triage.ambiguity_margin", True),
    ("finder.min_score", None),
    ("finder.margin", [0.1]),
    ("link_check.user_agent", ""),
]


@pytest.mark.parametrize(("label", "wrong"), WRONG_TYPES)
def test_field_of_the_wrong_type_falls_back_to_the_default_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, label: str, wrong: Any
) -> None:
    attribute, default = FIELD_DEFAULTS[label]

    with caplog.at_level("WARNING", logger="triage.config"):
        settings = _load(tmp_path, lambda data: _set_field(data, label, wrong))

    assert getattr(settings, attribute) == default
    assert label in caplog.text


@pytest.mark.parametrize("label", ["triage.confidence_min", "triage.ambiguity_margin", "finder.min_score", "finder.margin"])
@pytest.mark.parametrize("out_of_range", [1.5, -0.1, 2, -1, float("nan"), float("inf")])
def test_threshold_outside_zero_one_falls_back_to_the_default_with_a_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, label: str, out_of_range: float
) -> None:
    attribute, default = FIELD_DEFAULTS[label]

    with caplog.at_level("WARNING", logger="triage.config"):
        settings = _load(tmp_path, lambda data: _set_field(data, label, out_of_range))

    assert getattr(settings, attribute) == default
    assert label in caplog.text


@pytest.mark.parametrize("limit", [0, 1, 0.0, 1.0])
def test_thresholds_accept_the_range_limits(tmp_path: Path, caplog: pytest.LogCaptureFixture, limit: float) -> None:
    with caplog.at_level("WARNING", logger="triage.config"):
        settings = _load(tmp_path, lambda data: _set_field(data, "finder.min_score", limit))

    assert settings.finder_min_score == float(limit)
    assert isinstance(settings.finder_min_score, float)
    assert caplog.records == []


@pytest.mark.parametrize("section", ["llm", "triage", "finder", "link_check"])
def test_missing_or_malformed_section_falls_back_to_the_defaults(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, section: str
) -> None:
    with caplog.at_level("WARNING", logger="triage.config"):
        missing = _load(tmp_path, lambda data: data.pop(section))
        malformed = _load(tmp_path, lambda data: data.update({section: "texto"}))

    expected = [attribute for label, (attribute, _) in FIELD_DEFAULTS.items() if label.startswith(f"{section}.")]
    for settings in (missing, malformed):
        assert [getattr(settings, attribute) for attribute in expected] == [
            default for label, (_, default) in FIELD_DEFAULTS.items() if label.startswith(f"{section}.")
        ]
    assert section in caplog.text


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ([], ()),
        (["modelo-a"], ("modelo-a",)),
        (["modelo-a", " modelo-b ", "modelo-c"], ("modelo-a", "modelo-b", "modelo-c")),
        (["modelo-a", "", "  ", "modelo-b"], ("modelo-a", "modelo-b")),
    ],
)
def test_fallback_models_is_a_trimmed_list_without_blanks(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, configured: list[str], expected: tuple[str, ...]
) -> None:
    with caplog.at_level("WARNING", logger="triage.config"):
        settings = _load(tmp_path, lambda data: _set_field(data, "llm.fallback_models", configured))

    assert settings.llm_fallback_models == expected
    assert caplog.records == []


def test_api_key_comes_only_from_the_environment(monkeypatch: pytest.MonkeyPatch, missing_env: Path) -> None:
    assert load_settings(missing_env).llm_api_key == ""

    monkeypatch.setenv("LLM_API_KEY", "chave-de-teste")

    assert load_settings(missing_env).llm_api_key == "chave-de-teste"


def test_api_key_is_read_from_the_dotenv_file(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("LLM_API_KEY=chave-do-arquivo\n", encoding="utf-8")

    assert load_settings(dotenv).llm_api_key == "chave-do-arquivo"


def test_old_environment_variables_do_not_change_the_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    baseline = load_settings(tmp_path / "missing.env")
    for key in OLD_ENV_KEYS:
        monkeypatch.setenv(key, "0.9" if key.endswith(("MIN", "MARGIN", "SCORE")) else "true")
    dotenv = tmp_path / ".env"
    dotenv.write_text("LLM_MODEL=do-arquivo\nLOG_LEVEL=DEBUG\nFINDER_MARGIN=0.9\n", encoding="utf-8")

    assert load_settings(dotenv) == baseline
    assert load_settings(tmp_path / "missing.env") == baseline


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_exits_with_1_when_the_config_is_broken(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    run_module = _load_module("run_config_entrypoint", ROOT / "run.py")
    monkeypatch.setattr(run_module, "load_settings", partial(load_settings, config_path=tmp_path / "ausente.json"))
    input_dir = tmp_path / "in"
    input_dir.mkdir()

    with caplog.at_level("ERROR", logger="triage.run"):
        code = run_module.main(["--input", str(input_dir), "--output", str(tmp_path / "out")])

    assert code == 1
    assert "Configuração inválida" in caplog.text
    assert not (tmp_path / "out").exists()


def test_app_shows_a_message_without_traceback_when_the_config_is_broken(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    st.cache_resource.clear()
    monkeypatch.setattr(triage.config, "load_settings", partial(load_settings, config_path=tmp_path / "ausente.json"))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)

    app.run()

    assert not app.exception
    assert [error.value for error in app.error] == [
        "Não foi possível iniciar o atendimento (configuração ou banco de dados inacessível). Tente novamente mais tarde."
    ]
