"""Cliente compatível com OpenAI: contrato da requisição e tradução de falhas (sem rede)."""

import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import requests

from triage.agent import (
    DEFAULT_AGENT_ID,
    AgentError,
    compose_system_prompt,
    lint_agent,
    load_agent,
)
from triage.automation import llm_client
from triage.automation.llm_client import (
    LlmInvalidResponse,
    LlmUnavailable,
    OpenAICompatibleClient,
    build_llm_client,
)
from triage.config import Settings

PROVIDER_CREDENTIAL = "sk-segredo-de-teste-123"
SETTINGS = Settings(True, "https://llm.example/v1/", "modelo-x", PROVIDER_CREDENTIAL, "INFO", "output")
REAL_AGENT = load_agent(DEFAULT_AGENT_ID)
AGENT = replace(REAL_AGENT, params=replace(REAL_AGENT.params, base_delay_seconds=0.0, max_delay_seconds=0.0))


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


def _client(*models: str) -> OpenAICompatibleClient:
    return OpenAICompatibleClient("https://llm.example/v1/", PROVIDER_CREDENTIAL, models or ("modelo-x",), AGENT)


def _patch_post(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakePost:
    fake = FakePost(*outcomes)
    monkeypatch.setattr(llm_client.requests, "post", fake)
    return fake


def test_posts_chat_completion_with_timeout_and_key_only_in_header(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, _ok("  texto reformulado  "))
    assert _client().complete("rewrite", "texto X") == "texto reformulado"
    call = fake.calls[0]
    assert call["url"] == "https://llm.example/v1/chat/completions"
    assert call["headers"] == {"Authorization": f"Bearer {PROVIDER_CREDENTIAL}"}
    assert call["json"]["model"] == "modelo-x"
    assert PROVIDER_CREDENTIAL not in str(call["json"])


def test_request_sends_the_composed_system_prompt_and_the_agent_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, _ok("ok"))
    _client().complete("rewrite", "texto X")
    call = fake.calls[0]
    assert call["json"]["messages"] == [
        {"role": "system", "content": compose_system_prompt(AGENT, "rewrite")},
        {"role": "user", "content": "texto X"},
    ]
    assert call["json"]["temperature"] == AGENT.params.temperature
    assert call["json"]["max_tokens"] == AGENT.params.max_tokens
    assert call["timeout"] == AGENT.params.timeout_seconds


def test_retry_attempts_come_from_the_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    more_attempts = replace(AGENT, params=replace(AGENT.params, attempts=3))
    client = OpenAICompatibleClient("https://llm.example/v1", PROVIDER_CREDENTIAL, ("modelo-x",), more_attempts)
    fake = _patch_post(monkeypatch, FakeResponse(503), FakeResponse(503), FakeResponse(503))
    with pytest.raises(LlmUnavailable):
        client.complete("rewrite", "p")
    assert len(fake.calls) == 3


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
        _client().complete("rewrite", "p")


def test_transient_failure_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, requests.Timeout("lento"), _ok("ok"))
    assert _client().complete("rewrite", "p") == "ok"
    assert len(fake.calls) == 2


@pytest.mark.parametrize("failure", [requests.Timeout("t"), requests.ConnectionError("c"), FakeResponse(503)])
def test_persistent_transient_failure_is_unavailable(monkeypatch: pytest.MonkeyPatch, failure: Any) -> None:
    fake = _patch_post(monkeypatch, failure, failure)
    with pytest.raises(LlmUnavailable):
        _client().complete("rewrite", "p")
    assert len(fake.calls) == 2


def test_client_error_is_unavailable_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, FakeResponse(401))
    with pytest.raises(LlmUnavailable):
        _client().complete("rewrite", "p")
    assert len(fake.calls) == 1


def test_api_key_never_reaches_logs_or_exceptions(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    _patch_post(monkeypatch, FakeResponse(503), FakeResponse(503))
    with caplog.at_level(logging.DEBUG), pytest.raises(LlmUnavailable) as raised:
        _client().complete("rewrite", "p")
    assert PROVIDER_CREDENTIAL not in caplog.text
    assert PROVIDER_CREDENTIAL not in str(raised.value)
    assert PROVIDER_CREDENTIAL not in repr(raised.value.__cause__)


def test_falls_back_to_the_next_model_when_the_first_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = _patch_post(monkeypatch, FakeResponse(401), _ok("do segundo"))
    with caplog.at_level(logging.WARNING, logger="triage.automation"):
        assert _client("principal", "reserva").complete("rewrite", "TEXTO-SIGILOSO") == "do segundo"
    assert [call["json"]["model"] for call in fake.calls] == ["principal", "reserva"]
    assert "principal" in caplog.text
    assert "TEXTO-SIGILOSO" not in caplog.text
    assert PROVIDER_CREDENTIAL not in caplog.text


def test_invalid_response_also_passes_to_the_next_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, _ok(""), _ok("do segundo"))
    assert _client("principal", "reserva").complete("rewrite", "p") == "do segundo"
    assert len(fake.calls) == 2


def test_models_are_tried_in_order_and_the_last_error_is_raised_when_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, FakeResponse(401), FakeResponse(403), _ok(None))
    with pytest.raises(LlmInvalidResponse):
        _client("a", "b", "c").complete("rewrite", "p")
    assert [call["json"]["model"] for call in fake.calls] == ["a", "b", "c"]


def test_a_working_first_model_does_not_touch_the_alternatives(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, _ok("ok"))
    _client("principal", "reserva").complete("rewrite", "p")
    assert len(fake.calls) == 1


def test_unknown_task_is_not_sent_to_the_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch)
    with pytest.raises(AgentError):
        _client().complete("locate", "p")
    assert fake.calls == []


def test_factory_returns_none_when_llm_is_disabled() -> None:
    assert build_llm_client(replace(SETTINGS, llm_enabled=False)) is None


@pytest.mark.parametrize("field", ["llm_base_url", "llm_model", "llm_api_key"])
def test_factory_returns_none_when_configuration_is_incomplete(field: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        assert build_llm_client(replace(SETTINGS, **{field: ""})) is None
    assert PROVIDER_CREDENTIAL not in caplog.text


def test_factory_builds_client_when_enabled_and_complete() -> None:
    assert isinstance(build_llm_client(SETTINGS), OpenAICompatibleClient)


def test_factory_passes_the_primary_model_then_the_alternatives(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_post(monkeypatch, FakeResponse(401), _ok("do segundo"))
    client = build_llm_client(replace(SETTINGS, llm_fallback_models=("reserva",)))
    assert client is not None
    assert client.complete("rewrite", "p") == "do segundo"
    assert [call["json"]["model"] for call in fake.calls] == ["modelo-x", "reserva"]


def test_factory_returns_none_and_logs_an_error_when_the_agent_does_not_exist(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        assert build_llm_client(replace(SETTINGS, llm_agent_id="nao-existe")) is None
    assert any(record.levelno == logging.ERROR and "nao-existe" in record.getMessage() for record in caplog.records)
    assert PROVIDER_CREDENTIAL not in caplog.text


def test_factory_returns_none_when_the_agent_has_lint_problems(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    broken = tmp_path / "agents"
    (broken / DEFAULT_AGENT_ID).mkdir(parents=True)
    (broken / "global_rules.md").write_text("regra", encoding="utf-8")
    for name in ("identity.md", "rules.md", "workflow.md"):
        (broken / DEFAULT_AGENT_ID / name).write_text("conteudo sigiloso do prompt", encoding="utf-8")
    (broken / DEFAULT_AGENT_ID / "config.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(llm_client, "lint_agent", lambda agent_id: lint_agent(agent_id, broken))

    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        assert build_llm_client(SETTINGS) is None
    assert "JSON inválido" in caplog.text
    assert "conteudo sigiloso do prompt" not in caplog.text


def test_factory_returns_none_when_loading_fails_after_the_linter_passes(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def failing_load(agent_id: str) -> None:
        raise AgentError("arquivo sumiu")

    monkeypatch.setattr(llm_client, "load_agent", failing_load)
    with caplog.at_level(logging.ERROR, logger="triage.automation"):
        assert build_llm_client(SETTINGS) is None
    assert "arquivo sumiu" in caplog.text
