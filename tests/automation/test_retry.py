"""Retry com espera exponencial: só repete exceção transitória."""

import pytest

from triage.common.retry import RetryPolicy, retry_with_backoff


class TransientError(Exception):
    pass


def _policy(attempts: int = 3) -> RetryPolicy:
    return RetryPolicy(attempts=attempts, base_delay=1.0, max_delay=3.0, transient=(TransientError,))


def _flaky(failures: int, error: Exception):
    calls = {"count": 0}

    def operation() -> str:
        calls["count"] += 1
        if calls["count"] <= failures:
            raise error
        return "ok"

    return operation, calls


def test_succeeds_on_second_attempt_waiting_once() -> None:
    operation, calls = _flaky(1, TransientError("falha"))
    delays: list[float] = []
    assert retry_with_backoff(operation, _policy(), delays.append) == "ok"
    assert calls["count"] == 2
    assert delays == [1.0]


def test_exhausts_attempts_and_reraises_last_error() -> None:
    operation, calls = _flaky(10, TransientError("sempre"))
    delays: list[float] = []
    with pytest.raises(TransientError, match="sempre"):
        retry_with_backoff(operation, _policy(3), delays.append)
    assert calls["count"] == 3
    assert delays == [1.0, 2.0]


def test_delay_is_capped_at_max_delay() -> None:
    operation, _ = _flaky(10, TransientError("x"))
    delays: list[float] = []
    with pytest.raises(TransientError):
        retry_with_backoff(operation, _policy(5), delays.append)
    assert delays == [1.0, 2.0, 3.0, 3.0]


def test_does_not_retry_non_transient_error() -> None:
    operation, calls = _flaky(10, ValueError("definitivo"))
    delays: list[float] = []
    with pytest.raises(ValueError, match="definitivo"):
        retry_with_backoff(operation, _policy(), delays.append)
    assert calls["count"] == 1
    assert delays == []


def test_zero_attempts_still_runs_once() -> None:
    operation, calls = _flaky(0, TransientError("x"))
    assert retry_with_backoff(operation, _policy(0), lambda _: None) == "ok"
    assert calls["count"] == 1


def test_logs_each_failed_attempt(caplog: pytest.LogCaptureFixture) -> None:
    operation, _ = _flaky(10, TransientError("x"))
    with caplog.at_level("WARNING", logger="triage.retry"), pytest.raises(TransientError):
        retry_with_backoff(operation, _policy(3), lambda _: None)
    assert len(caplog.records) == 3
