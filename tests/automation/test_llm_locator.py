"""Escolha do LLM entre candidatas aprovadas: lista fechada, JSON estrito e falha segura (cliente falso, sem rede)."""

import json
import logging
from collections.abc import Callable

import pytest

from triage.automation.catalog import ServiceEntry
from triage.automation.llm_client import LlmInvalidResponse, LlmUnavailable
from triage.automation.llm_locator import build_locate_message, choose_entry

MakeEntry = Callable[..., ServiceEntry]
REQUEST = "preciso do alvara [NOME]"


class FakeClient:
    """Devolve a resposta combinada (ou levanta a combinada) e guarda as chamadas."""

    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def complete(self, task: str, user_message: str) -> str:
        self.calls.append((task, user_message))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer  # type: ignore[return-value]


@pytest.fixture
def candidates(make_entry: MakeEntry) -> tuple[ServiceEntry, ...]:
    return (
        make_entry("alvara", display_name="Alvará", agency="Prefeitura"),
        make_entry("iptu", display_name="IPTU", agency="Prefeitura"),
    )


def test_message_has_the_text_between_delimiters_and_one_line_per_candidate(candidates: tuple[ServiceEntry, ...]) -> None:
    message = build_locate_message(REQUEST, candidates)

    assert message.splitlines() == [
        "<<<PEDIDO",
        REQUEST,
        "PEDIDO>>>",
        "",
        "alvara | Alvará | Prefeitura",
        "iptu | IPTU | Prefeitura",
    ]


def test_valid_id_returns_that_candidate_and_uses_the_locate_task(candidates: tuple[ServiceEntry, ...]) -> None:
    client = FakeClient('{"id": "iptu"}')

    assert choose_entry(client, REQUEST, candidates) is candidates[1]
    assert [task for task, _ in client.calls] == ["locate"]


@pytest.mark.parametrize(
    "answer",
    [
        '{"id": "none"}',
        '{"id": "inventado"}',
        '{"id": "ALVARA"}',
        '{"id": null}',
        '{"id": 1}',
        '{"id": ["alvara"]}',
        '{"id": "alvara", "extra": "golpe.com"}',
        '{"outra": "alvara"}',
        '["alvara"]',
        '"alvara"',
        "alvara",
        "Acesse https://golpe.com para o alvará",
        '```json\n{"id": "alvara"}\n```',
        "{",
        "",
        '{"id": "' + "a" * 5000 + '"}',
    ],
)
def test_any_answer_outside_the_closed_format_is_no_choice(candidates: tuple[ServiceEntry, ...], answer: str) -> None:
    assert choose_entry(FakeClient(answer), REQUEST, candidates) is None


@pytest.mark.parametrize("error", [LlmUnavailable("timeout"), LlmInvalidResponse("vazio")])
def test_client_failure_is_no_choice_and_the_log_never_has_the_request(
    candidates: tuple[ServiceEntry, ...], error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="triage.automation"):
        assert choose_entry(FakeClient(error), REQUEST, candidates) is None

    assert "alvara [NOME]" not in caplog.text
    assert caplog.records


def test_invalid_answer_is_logged_without_the_request_or_the_answer(
    candidates: tuple[ServiceEntry, ...], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="triage.automation"):
        choose_entry(FakeClient("golpe.com"), REQUEST, candidates)

    assert "golpe.com" not in caplog.text
    assert "alvara [NOME]" not in caplog.text


def test_no_candidates_never_calls_the_client() -> None:
    client = FakeClient(json.dumps({"id": "x"}))

    assert choose_entry(client, REQUEST, ()) is None
    assert client.calls == []
