"""Definição do agente LLM a partir de arquivos versionados: carga, validação e composição do prompt."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

AGENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "agents"
DEFAULT_AGENT_ID = "triage-assistant"
AGENT_ID_PATTERN = re.compile(r"[a-z0-9-]+")
GLOBAL_RULES_FILE = "global_rules.md"
IDENTITY_FILE = "identity.md"
RULES_FILE = "rules.md"
WORKFLOW_FILE = "workflow.md"
CONFIG_FILE = "config.json"
AGENT_FILES = (IDENTITY_FILE, RULES_FILE, WORKFLOW_FILE, CONFIG_FILE)
TASK_HEADING = re.compile(r"^## Tarefa: (\S+)\s*$", re.MULTILINE)
REQUIRED_TASKS = ("answer", "categorize")
TEMPERATURE_MIN = 0.0
TEMPERATURE_MAX = 2.0
PROMPT_SEPARATOR = "\n\n"


class AgentError(Exception):
    """O agente não pôde ser carregado: a mensagem diz o que corrigir."""


@dataclass(frozen=True)
class AgentParams:
    """Parâmetros de chamada e política de retry do agente, lidos de `config.json`."""

    temperature: float
    max_tokens: int
    timeout_seconds: float
    attempts: int
    base_delay_seconds: float
    max_delay_seconds: float
    max_candidates: int


@dataclass(frozen=True)
class AgentDefinition:
    """Agente imutável: persona, regras, seções de fluxo por tarefa e parâmetros."""

    agent_id: str
    global_rules: str
    identity: str
    rules: str
    tasks: Mapping[str, str]
    params: AgentParams


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_temperature(value: object) -> bool:
    return _is_number(value) and TEMPERATURE_MIN <= value <= TEMPERATURE_MAX  # type: ignore[operator]


def _is_positive_number(value: object) -> bool:
    return _is_number(value) and value > 0  # type: ignore[operator]


def _is_non_negative_number(value: object) -> bool:
    return _is_number(value) and value >= 0  # type: ignore[operator]


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


PARAM_RULES = (
    ("temperature", _is_temperature, f"número em [{TEMPERATURE_MIN:g}, {TEMPERATURE_MAX:g}]"),
    ("max_tokens", _is_positive_int, "inteiro positivo"),
    ("timeout_seconds", _is_positive_number, "número positivo"),
    ("max_candidates", _is_positive_int, "inteiro positivo"),
    ("retries.attempts", _is_positive_int, "inteiro positivo"),
    ("retries.base_delay_seconds", _is_non_negative_number, "número não negativo"),
    ("retries.max_delay_seconds", _is_non_negative_number, "número não negativo"),
)


def _lookup(raw: dict, dotted_name: str) -> object:
    """Valor de `a.b` em `raw`; qualquer degrau ausente ou que não seja objeto dá `None`."""
    value: object = raw
    for key in dotted_name.split("."):
        value = value.get(key) if isinstance(value, dict) else None
    return value


def params_problems(raw: object) -> list[str]:
    """Lista os problemas de um `config.json` já decodificado; vazia quando ele serve."""
    if not isinstance(raw, dict):
        return [f"{CONFIG_FILE}: deve ser um objeto JSON"]
    problems = [
        f"{CONFIG_FILE}: {name} deve ser {expected}"
        for name, is_valid, expected in PARAM_RULES
        if not is_valid(_lookup(raw, name))
    ]
    if not problems and raw["retries"]["max_delay_seconds"] < raw["retries"]["base_delay_seconds"]:
        problems.append(f"{CONFIG_FILE}: retries.max_delay_seconds deve ser >= retries.base_delay_seconds")
    return problems


def _build_params(raw: dict) -> AgentParams:
    retries = raw["retries"]
    return AgentParams(
        temperature=float(raw["temperature"]),
        max_tokens=raw["max_tokens"],
        timeout_seconds=float(raw["timeout_seconds"]),
        attempts=retries["attempts"],
        base_delay_seconds=float(retries["base_delay_seconds"]),
        max_delay_seconds=float(retries["max_delay_seconds"]),
        max_candidates=raw["max_candidates"],
    )


def parse_tasks(workflow_text: str) -> dict[str, str]:
    """Separa o `workflow.md` em seções `## Tarefa: <nome>`; o corpo de cada uma vai sem as bordas em branco."""
    headings = list(TASK_HEADING.finditer(workflow_text))
    tasks: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(workflow_text)
        tasks[heading.group(1)] = workflow_text[heading.end():end].strip()
    return tasks


def read_text_file(path: Path) -> str:
    """Lê um arquivo de texto obrigatório e não vazio; ausência, ilegibilidade ou vazio é `AgentError`."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise AgentError(f"arquivo do agente ausente ou ilegível: {path}") from error
    if not text:
        raise AgentError(f"arquivo do agente vazio: {path}")
    return text


def _read_config(path: Path) -> dict:
    try:
        raw = json.loads(read_text_file(path))
    except json.JSONDecodeError as error:
        raise AgentError(f"{path}: JSON inválido na linha {error.lineno}, coluna {error.colno}") from error
    problems = params_problems(raw)
    if problems:
        raise AgentError(f"{path}: " + "; ".join(problems))
    return raw


def _validate_agent_id(agent_id: str) -> None:
    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        raise AgentError(f"id de agente inválido (use [a-z0-9-]+): {agent_id!r}")


def load_agent(agent_id: str, agents_dir: Path = AGENTS_DIR) -> AgentDefinition:
    """Carrega o agente `agent_id` de `agents_dir`; qualquer defeito vira `AgentError` com a causa preservada."""
    _validate_agent_id(agent_id)
    agent_dir = agents_dir / agent_id
    tasks = parse_tasks(read_text_file(agent_dir / WORKFLOW_FILE))
    missing = [task for task in REQUIRED_TASKS if not tasks.get(task)]
    if missing:
        raise AgentError(f"{agent_dir / WORKFLOW_FILE}: falta a seção '## Tarefa: {missing[0]}'")
    return AgentDefinition(
        agent_id=agent_id,
        global_rules=read_text_file(agents_dir / GLOBAL_RULES_FILE),
        identity=read_text_file(agent_dir / IDENTITY_FILE),
        rules=read_text_file(agent_dir / RULES_FILE),
        tasks=MappingProxyType(tasks),
        params=_build_params(_read_config(agent_dir / CONFIG_FILE)),
    )


def compose_system_prompt(agent: AgentDefinition, task: str) -> str:
    """Prompt de sistema de uma tarefa: regras globais, identidade, regras e a seção do fluxo, nessa ordem."""
    section = agent.tasks.get(task)
    if section is None:
        raise AgentError(f"o agente '{agent.agent_id}' não tem a tarefa '{task}'")
    return PROMPT_SEPARATOR.join((agent.global_rules, agent.identity, agent.rules, section))
