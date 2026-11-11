"""Fixtures do agente: cópia do agente real do repositório, que cada teste pode quebrar à vontade."""

import shutil
from pathlib import Path

import pytest

from triage.agent import AGENTS_DIR, DEFAULT_AGENT_ID


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    target = tmp_path / "agents"
    shutil.copytree(AGENTS_DIR, target)
    return target


@pytest.fixture
def agent_dir(agents_dir: Path) -> Path:
    return agents_dir / DEFAULT_AGENT_ID
