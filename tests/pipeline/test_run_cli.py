"""`run.py` com o pipeline: códigos de saída, relatório gerado e `--watch`."""

import dataclasses
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from triage.config import Settings
from triage.pipeline import Deps

RUN_PATH = Path(__file__).resolve().parents[2] / "run.py"
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


@pytest.fixture
def run_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_entrypoint_pipeline", RUN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def offline(run_module: ModuleType, make_deps: Callable[..., Deps], monkeypatch: pytest.MonkeyPatch) -> Deps:
    """Troca a montagem das dependências por uma sem rede (link simulado) e com banco temporário."""
    deps = make_deps()
    monkeypatch.setattr(run_module, "build_deps", lambda settings, db_path: dataclasses.replace(deps, settings=settings))
    return deps


def test_run_over_samples_exits_0_and_writes_reports(run_module: ModuleType, offline: Deps, tmp_path: Path) -> None:
    output = tmp_path / "saida"

    code = run_module.main(["--input", str(SAMPLES_DIR), "--output", str(output)])

    assert code == 0
    assert list((output / "reports").glob("run-*.json"))
    assert list((output / "reports").glob("run-*.md"))


def test_unreachable_database_exits_1(run_module: ModuleType, tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    input_dir.mkdir()

    code = run_module.main(["--input", str(input_dir), "--output", str(tmp_path / "out"), "--db", str(tmp_path)])

    assert code == 1


def test_invalid_interval_exits_2(run_module: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        run_module.main(["--input", str(tmp_path), "--output", str(tmp_path), "--interval", "0"])

    assert exit_info.value.code == 2


def test_watch_flag_hands_control_to_the_scheduler(
    run_module: ModuleType, offline: Deps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict[str, object] = {}
    monkeypatch.setattr(
        run_module, "watch", lambda input_dir, interval, deps, stop: received.update(interval=interval, stop=stop)
    )

    code = run_module.main(["--input", str(SAMPLES_DIR), "--output", str(tmp_path / "o"), "--watch", "--interval", "5"])

    assert code == 0
    assert received["interval"] == 5.0
    assert not received["stop"].is_set()


def test_llm_flag_overrides_settings(run_module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[bool] = []

    def fake_build_deps(settings: Settings, db_path: str) -> Deps:
        seen.append(settings.llm_enabled)
        raise OSError("para aqui")

    monkeypatch.setattr(run_module, "build_deps", fake_build_deps)

    run_module.main(["--input", str(tmp_path), "--output", str(tmp_path / "o"), "--llm"])
    run_module.main(["--input", str(tmp_path), "--output", str(tmp_path / "o"), "--no-llm"])

    assert seen == [True, False]
