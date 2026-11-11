"""Carga do agente e composição do prompt de sistema (sem rede)."""

import json
from pathlib import Path

import pytest

from triage.agent import DEFAULT_AGENT_ID, AgentError, compose_system_prompt, load_agent

AGENT_FILES = ["identity.md", "rules.md", "workflow.md", "config.json"]


def _write_config(agent_dir: Path, **changes: object) -> None:
    config = json.loads((agent_dir / "config.json").read_text(encoding="utf-8"))
    config.update(changes)
    (agent_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_loads_the_real_agent_with_the_initial_parameters() -> None:
    agent = load_agent(DEFAULT_AGENT_ID)

    assert agent.agent_id == DEFAULT_AGENT_ID
    assert "rewrite" in agent.tasks
    params = agent.params
    assert (params.temperature, params.timeout_seconds, params.attempts) == (0.2, 15.0, 2)
    assert (params.base_delay_seconds, params.max_delay_seconds) == (1.0, 4.0)
    assert params.max_tokens > 0


@pytest.mark.parametrize("agent_id", ["", "Triage", "../x", "a/b", "a b", "triage_assistant"])
def test_invalid_id_is_rejected(agent_id: str, agents_dir: Path) -> None:
    with pytest.raises(AgentError, match="id de agente inválido"):
        load_agent(agent_id, agents_dir)


def test_unknown_agent_is_a_missing_file_error(agents_dir: Path) -> None:
    with pytest.raises(AgentError, match="ausente") as raised:
        load_agent("nao-existe", agents_dir)
    assert isinstance(raised.value.__cause__, OSError)


@pytest.mark.parametrize("name", AGENT_FILES)
def test_missing_agent_file_is_an_error_naming_the_file(name: str, agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / name).unlink()
    with pytest.raises(AgentError, match=name):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


def test_missing_global_rules_is_an_error(agents_dir: Path) -> None:
    (agents_dir / "global_rules.md").unlink()
    with pytest.raises(AgentError, match="global_rules.md"):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


@pytest.mark.parametrize("name", AGENT_FILES)
def test_blank_agent_file_is_an_error(name: str, agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / name).write_text("  \n", encoding="utf-8")
    with pytest.raises(AgentError, match="vazio"):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


def test_invalid_json_keeps_the_cause(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "config.json").write_text("{ nao e json", encoding="utf-8")
    with pytest.raises(AgentError, match="JSON inválido") as raised:
        load_agent(DEFAULT_AGENT_ID, agents_dir)
    assert isinstance(raised.value.__cause__, json.JSONDecodeError)


RETRIES_OK = {"attempts": 2, "base_delay_seconds": 1, "max_delay_seconds": 4}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"temperature": 2.5}, "temperature"),
        ({"temperature": -0.1}, "temperature"),
        ({"temperature": "alta"}, "temperature"),
        ({"max_tokens": 0}, "max_tokens"),
        ({"max_tokens": 1.5}, "max_tokens"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"timeout_seconds": True}, "timeout_seconds"),
        ({"retries": {**RETRIES_OK, "attempts": 0}}, "retries.attempts"),
        ({"retries": {**RETRIES_OK, "base_delay_seconds": -1}}, "base_delay_seconds"),
        ({"retries": {**RETRIES_OK, "base_delay_seconds": 5}}, "max_delay_seconds deve ser >="),
        ({"retries": "duas"}, "retries.attempts"),
    ],
)
def test_out_of_range_parameter_is_an_error(
    changes: dict[str, object], message: str, agents_dir: Path, agent_dir: Path
) -> None:
    _write_config(agent_dir, **changes)
    with pytest.raises(AgentError, match=message):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


def test_parameter_range_limits_are_accepted(agents_dir: Path, agent_dir: Path) -> None:
    retries = {"attempts": 1, "base_delay_seconds": 0, "max_delay_seconds": 0}
    _write_config(agent_dir, temperature=0, retries=retries)
    assert load_agent(DEFAULT_AGENT_ID, agents_dir).params.temperature == 0.0
    _write_config(agent_dir, temperature=2)
    assert load_agent(DEFAULT_AGENT_ID, agents_dir).params.temperature == 2.0


def test_workflow_without_the_rewrite_section_is_an_error(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "workflow.md").write_text("# Fluxo\n\n## Tarefa: outra\n\ntexto\n", encoding="utf-8")
    with pytest.raises(AgentError, match="Tarefa: rewrite"):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


def test_workflow_with_an_empty_rewrite_section_is_an_error(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "workflow.md").write_text("## Tarefa: rewrite\n\n", encoding="utf-8")
    with pytest.raises(AgentError, match="Tarefa: rewrite"):
        load_agent(DEFAULT_AGENT_ID, agents_dir)


def test_system_prompt_is_ordered_global_identity_rules_task(agents_dir: Path, agent_dir: Path) -> None:
    (agents_dir / "global_rules.md").write_text("GLOBAL", encoding="utf-8")
    (agent_dir / "identity.md").write_text("IDENTIDADE", encoding="utf-8")
    (agent_dir / "rules.md").write_text("REGRAS", encoding="utf-8")
    (agent_dir / "workflow.md").write_text("## Tarefa: outra\nNAO\n\n## Tarefa: rewrite\nTAREFA\n", encoding="utf-8")

    prompt = compose_system_prompt(load_agent(DEFAULT_AGENT_ID, agents_dir), "rewrite")

    assert prompt == "GLOBAL\n\nIDENTIDADE\n\nREGRAS\n\nTAREFA"


def test_unknown_task_has_no_prompt() -> None:
    with pytest.raises(AgentError, match="não tem a tarefa 'locate'"):
        compose_system_prompt(load_agent(DEFAULT_AGENT_ID), "locate")


def test_loaded_agent_is_immutable() -> None:
    agent = load_agent(DEFAULT_AGENT_ID)
    with pytest.raises(AttributeError):
        agent.identity = "outra"
    with pytest.raises(TypeError):
        agent.tasks["x"] = "y"  # type: ignore[index]
