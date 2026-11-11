"""Linter dos arquivos de um agente: devolve todos os problemas de uma vez, sem levantar."""

import json
import re
from pathlib import Path

from triage.agent.definition import (
    AGENT_FILES,
    AGENT_ID_PATTERN,
    AGENTS_DIR,
    CONFIG_FILE,
    GLOBAL_RULES_FILE,
    REQUIRED_TASKS,
    WORKFLOW_FILE,
    AgentError,
    params_problems,
    parse_tasks,
    read_text_file,
)

SECRET_PATTERNS = (
    ("chave de API (sk-/gsk_)", re.compile(r"\b(?:sk|gsk)[-_][A-Za-z0-9_-]{8,}")),
    ("token Bearer", re.compile(r"\bBearer\s+\S{8,}", re.IGNORECASE)),
    ("atribuição de chave", re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*\S+", re.IGNORECASE)),
    ("URL de provedor", re.compile(r"https?://", re.IGNORECASE)),
)


def _secret_problems(name: str, text: str) -> list[str]:
    return [f"{name}: contém {label}" for label, pattern in SECRET_PATTERNS if pattern.search(text)]


def _config_problems(text: str) -> list[str]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        return [f"{CONFIG_FILE}: JSON inválido na linha {error.lineno}, coluna {error.colno}"]
    return params_problems(raw)


def _workflow_problems(text: str) -> list[str]:
    tasks = parse_tasks(text)
    return [f"{WORKFLOW_FILE}: falta a seção '## Tarefa: {task}'" for task in REQUIRED_TASKS if not tasks.get(task)]


def lint_agent(agent_id: str, agents_dir: Path = AGENTS_DIR) -> list[str]:
    """Problemas do agente `agent_id` em `agents_dir`; lista vazia quando ele está em ordem."""
    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        return [f"id de agente inválido (use [a-z0-9-]+): {agent_id!r}"]
    paths = [agents_dir / GLOBAL_RULES_FILE, *(agents_dir / agent_id / name for name in AGENT_FILES)]
    problems: list[str] = []
    texts: dict[str, str] = {}
    for path in paths:
        try:
            texts[path.name] = read_text_file(path)
        except AgentError as error:
            problems.append(str(error))
    if CONFIG_FILE in texts:
        problems.extend(_config_problems(texts[CONFIG_FILE]))
    if WORKFLOW_FILE in texts:
        problems.extend(_workflow_problems(texts[WORKFLOW_FILE]))
    for name, text in texts.items():
        problems.extend(_secret_problems(name, text))
    return problems
