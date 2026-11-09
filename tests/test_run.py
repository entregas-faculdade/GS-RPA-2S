"""Testes do ponto de entrada `run.py`."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

RUN_PATH = Path(__file__).resolve().parent.parent / "run.py"


@pytest.fixture(scope="module")
def run_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_entrypoint", RUN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_input_returns_2_and_logs_error(run_module: ModuleType, tmp_path: Path) -> None:
    output = tmp_path / "out"

    code = run_module.main(["--input", str(tmp_path / "nao-existe"), "--output", str(output)])

    assert code == 2
    assert "Pasta de entrada não encontrada" in (output / "logs" / "run.log").read_text(encoding="utf-8")


def test_existing_input_returns_0(run_module: ModuleType, tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()

    code = run_module.main(["--input", str(input_dir), "--output", str(tmp_path / "out")])

    assert code == 0


def test_help_lists_input_and_output(run_module: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        run_module.main(["--help"])

    help_text = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "--input" in help_text
    assert "--output" in help_text
