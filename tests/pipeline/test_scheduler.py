"""`watch`: reexecuta, sobrevive a erro de rodada e para limpo com o sinal de parada."""

from collections.abc import Callable
from pathlib import Path
from threading import Event

import pytest

from triage.pipeline import Deps, scheduler


def test_watch_runs_once_and_stops_on_event(
    make_deps: Callable[..., Deps], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = Event()
    calls: list[Path] = []

    def fake_run_batch(input_dir: Path, deps: Deps) -> None:
        calls.append(input_dir)
        stop.set()

    monkeypatch.setattr(scheduler, "run_batch", fake_run_batch)

    scheduler.watch(tmp_path, 0.01, make_deps(), stop)

    assert calls == [tmp_path]


def test_watch_survives_a_failing_round(
    make_deps: Callable[..., Deps], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = Event()
    calls: list[int] = []

    def flaky_run_batch(input_dir: Path, deps: Deps) -> None:
        calls.append(len(calls))
        if len(calls) == 1:
            raise OSError("disco cheio")
        stop.set()

    monkeypatch.setattr(scheduler, "run_batch", flaky_run_batch)

    scheduler.watch(tmp_path, 0.01, make_deps(), stop)

    assert len(calls) == 2


def test_watch_returns_without_running_when_already_stopped(
    make_deps: Callable[..., Deps], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stop = Event()
    stop.set()
    monkeypatch.setattr(scheduler, "run_batch", lambda *_: pytest.fail("não deveria rodar"))

    scheduler.watch(tmp_path, 0.01, make_deps(), stop)


def test_watch_stops_cleanly_on_keyboard_interrupt(
    make_deps: Callable[..., Deps], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(*_args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler, "run_batch", interrupted)

    scheduler.watch(tmp_path, 0.01, make_deps(), Event())
