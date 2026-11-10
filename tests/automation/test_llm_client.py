"""Cliente compatível com OpenAI: contrato da requisição e tradução de falhas (sem rede)."""

import logging
from dataclasses import replace
from typing import Any

import pytest
import requests

from triage.automation import llm_client
from triage.automation.llm_client import (
    REQUEST_TIMEOUT_SECONDS,
    LlmInvalidResponse,
    LlmUnavailable,
    OpenAICompatibleClient,
    build_llm_client,
)
from triage.common.retry import RetryPolicy
from triage.config import Settings

PROVIDER_CREDENTIAL = "sk-segredo-de-teste-123"
FAST_POLICY = RetryPolicy(attempts=2, base_delay=0.0, max_delay=0.0, transient=llm_client.DEFAULT_RETRY_POLICY.transient)
SETTINGS = Settings(True, "https://llm.example/v1/", "modelo-x", PROVIDER_CREDENTIAL, "INFO", "output")


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None, json_error: bool = False) -> None:
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self) -> Any:
        if self._json_error:
            raise ValueError("não é JSON")
        return self._payload


def _ok(content: Any) -> FakeResponse:
    return FakeResponse(payload={"choices": [{"message": {"content": content}}]})


class FakePost:
    """Substitui `requests.post`: devolve ou levanta cada item da fila, registrando as chamadas."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient("https://llm.example/v1/", "modelo-x", PROVIDER_CREDENTIAL, FAST_POLICY)


def _patch_post(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakePost:
    fake = FakePost(*outcomes)
    monkeypatch.setattr(llm_client.requests, "post", fake)
    return fake


def test_posts_chat_completion_with_timeout_and_key_only_in_header(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, _ok("  texto reformulado  "))
    assert _client().rewrite("prompt X") == "texto reformulado"
    call = fake.calls[0]
    assert call["url"] == "https://llm.example/v1/chat/completions"
    assert call["timeout"] == REQUEST_TIMEOUT_SECONDS
    assert call["headers"] == {"Authorization": f"Bearer {PROVIDER_CREDENTIAL}"}
    assert call["json"]["model"] == "modelo-x"
    assert call["json"]["messages"] == [{"role": "user", "content": "prompt X"}]
    assert PROVIDER_CREDENTIAL not in str(call["json"])


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(payload={}),
        FakeResponse(payload={"choices": []}),
        FakeResponse(payload={"choices": [{}]}),
        FakeResponse(payload=["lista"]),
        FakeResponse(payload=None),
        FakeResponse(json_error=True),
        _ok(""),
        _ok("   \n"),
        _ok(None),
        _ok(["não é texto"]),
    ],
)
def test_malformed_or_empty_answer_is_invalid_response(monkeypatch: pytest.MonkeyPatch, response: FakeResponse) -> None:
    _patch_post(monkeypatch, response)
    with pytest.raises(LlmInvalidResponse):
        _client().rewrite("p")


def test_transient_failure_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, requests.Timeout("lento"), _ok("ok"))
    assert _client().rewrite("p") == "ok"
    assert len(fake.calls) == 2


@pytest.mark.parametrize("failure", [requests.Timeout("t"), requests.ConnectionError("c"), FakeResponse(503)])
def test_persistent_transient_failure_is_unavailable(monkeypatch: pytest.MonkeyPatch, failure: Any) -> None:
    fake = _patch_post(monkeypatch, failure, failure)
    with pytest.raises(LlmUnavailable):
        _client().rewrite("p")
    assert len(fake.calls) == 2


def test_client_error_is_unavailable_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, FakeResponse(401))
    with pytest.raises(LlmUnavailable):
        _client().rewrite("p")
    assert len(fake.calls) == 1


def test_api_key_never_reaches_logs_or_exceptions(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _patch_post(monkeypatch, FakeResponse(503), FakeResponse(503))
    with caplog.at_level(logging.DEBUG), pytest.raises(LlmUnavailable) as raised:
        _client().rewrite("p")
    assert PROVIDER_CREDENTIAL not in caplog.text
    assert PROVIDER_CREDENTIAL not in str(raised.value)
    assert PROVIDER_CREDENTIAL not in repr(raised.value.__cause__)


def test_factory_returns_none_when_llm_is_disabled() -> None:
    assert build_llm_client(replace(SETTINGS, llm_enabled=False)) is None


@pytest.mark.parametrize("field", ["llm_base_url", "llm_model", "llm_api_key"])
def test_factory_returns_none_when_configuration_is_incomplete(field: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert build_llm_client(replace(SETTINGS, **{field: ""})) is None
    assert PROVIDER_CREDENTIAL not in caplog.text


def test_factory_builds_client_when_enabled_and_complete() -> None:
    assert isinstance(build_llm_client(SETTINGS), OpenAICompatibleClient)
