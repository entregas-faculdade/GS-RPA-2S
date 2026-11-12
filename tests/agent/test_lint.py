"""Linter do agente e CLI `scripts/validate_agent.py` (sem rede)."""

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from triage.agent import DEFAULT_AGENT_ID, lint_agent

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_agent.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_agent_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _edit_config(agent_dir: Path, mutate: Callable[[dict], object]) -> None:
    config = json.loads((agent_dir / "config.json").read_text(encoding="utf-8"))
    mutate(config)
    (agent_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_the_real_agent_has_no_problems() -> None:
    assert lint_agent(DEFAULT_AGENT_ID) == []


def test_invalid_id_is_a_problem_not_an_exception(agents_dir: Path) -> None:
    assert lint_agent("../x", agents_dir) == ["id de agente inválido (use [a-z0-9-]+): '../x'"]


@pytest.mark.parametrize("name", ["identity.md", "rules.md", "workflow.md", "config.json"])
def test_missing_file_is_reported(name: str, agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / name).unlink()
    assert any(name in problem and "ausente" in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_missing_global_rules_is_reported(agents_dir: Path) -> None:
    (agents_dir / "global_rules.md").unlink()
    assert any("global_rules.md" in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_empty_file_is_reported(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "rules.md").write_text("\n", encoding="utf-8")
    assert any("vazio" in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_invalid_json_is_reported(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "config.json").write_text("{", encoding="utf-8")
    assert any("JSON inválido" in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda config: config.pop("temperature"), "temperature"),
        (lambda config: config.update(temperature=3), "temperature"),
        (lambda config: config.update(max_tokens=0), "max_tokens"),
        (lambda config: config.update(timeout_seconds=-1), "timeout_seconds"),
        (lambda config: config["retries"].update(attempts=0), "retries.attempts"),
        (lambda config: config["retries"].update(base_delay_seconds=-1), "base_delay_seconds"),
        (lambda config: config["retries"].update(max_delay_seconds=0.5), "max_delay_seconds deve ser >="),
        (lambda config: config.pop("retries"), "retries.attempts"),
    ],
)
def test_config_problems_are_reported(
    mutate: Callable[[dict], object], message: str, agents_dir: Path, agent_dir: Path
) -> None:
    _edit_config(agent_dir, mutate)
    assert any(message in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_missing_answer_section_is_reported(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "workflow.md").write_text("## Tarefa: outra\ntexto\n", encoding="utf-8")
    assert any("Tarefa: answer" in problem for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_missing_categorize_section_is_reported(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "workflow.md").write_text("## Tarefa: answer\ntexto\n", encoding="utf-8")
    problems = lint_agent(DEFAULT_AGENT_ID, agents_dir)
    assert any("Tarefa: categorize" in problem for problem in problems)
    assert not any("Tarefa: answer" in problem for problem in problems)


@pytest.mark.parametrize(
    "leak",
    [
        "use a chave sk-abcdef1234567890",
        "chave gsk_abcdef1234567890",
        "Authorization: Bearer abcdef1234567890",
        "api_key = abc123",
        "chame https://openrouter.ai/api/v1",
    ],
)
def test_secret_or_provider_url_is_reported(leak: str, agents_dir: Path, agent_dir: Path) -> None:
    with (agent_dir / "identity.md").open("a", encoding="utf-8") as file:
        file.write(f"\n{leak}\n")
    assert any(problem.startswith("identity.md: contém") for problem in lint_agent(DEFAULT_AGENT_ID, agents_dir))


def test_plain_words_about_keys_are_not_reported(agents_dir: Path, agent_dir: Path) -> None:
    with (agent_dir / "rules.md").open("a", encoding="utf-8") as file:
        file.write("\n- Nunca peça senha, token ou chave ao cidadão.\n")
    assert lint_agent(DEFAULT_AGENT_ID, agents_dir) == []


def test_all_problems_come_back_together(agents_dir: Path, agent_dir: Path) -> None:
    (agent_dir / "identity.md").unlink()
    (agent_dir / "workflow.md").write_text("sem seção", encoding="utf-8")
    assert len(lint_agent(DEFAULT_AGENT_ID, agents_dir)) == 3


def test_cli_exits_zero_for_the_real_agent(capsys: pytest.CaptureFixture[str]) -> None:
    assert _load_script().main([]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_exits_one_and_lists_the_problem(
    agents_dir: Path, agent_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (agent_dir / "config.json").write_text("{", encoding="utf-8")
    assert _load_script().main(["--agents-dir", str(agents_dir)]) == 1
    assert "JSON inválido" in capsys.readouterr().out

