"""`AppService` com conversa: mensagens anteriores anonimizadas, memória no LLM e hash do chat (cliente falso, sem rede)."""

import dataclasses
import logging
import sqlite3

import pytest
from sklearn.pipeline import Pipeline

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import load_catalog
from triage.automation.finder import ServiceFinder
from triage.automation.link_check import LinkStatus
from triage.automation.resolver import CatalogLookup
from triage.classification.decision import Decision, ReviewReason
from triage.config import Settings
from triage.interface.service import KIND_ANSWERED, KIND_DUPLICATE, AppService
from triage.pipeline import Deps, ProcessingResult
from triage.pipeline.processor import Conversation
from triage.storage import Repository

RG_TEXT = "Preciso saber como emitir a segunda via do meu RG. Nunca fiz esse pedido antes."
PREVIOUS_RAW = "Meu nome é Maria Souza, meu CPF é 123.456.789-09 e preciso negociar o IPTU em atraso"
FOLLOW_UP = "me passe o link correto para parcelamento"
RAW_SECRETS = ("Maria", "Souza", "123.456.789-09")


class FakeClient:
    """Responde que nenhuma fonte atende e guarda as mensagens recebidas."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def complete(self, _task: str, user_message: str) -> str:
        self.messages.append(user_message)
        return "NENHUMA_FONTE"


@pytest.fixture
def client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def chat_service(repository: Repository, settings: Settings, trained_model: Pipeline, client: FakeClient) -> AppService:
    """Serviço com o catálogo real, o LLM ligado (cliente falso) e a decisão fixa em revisão por baixa confiança."""
    tuned = dataclasses.replace(settings, llm_enabled=True)
    lookup = CatalogLookup(load_catalog(extra_dir=None), load_allowed_suffixes(), lambda _url: LinkStatus(True, 200, None))
    deps = Deps(
        repository=repository,
        lookup=lookup,
        settings=tuned,
        model=trained_model,
        llm_client=client,
        sleep=lambda _seconds: None,
        finder=ServiceFinder(lookup.approved_entries(), tuned),
    )
    return AppService(deps)


@pytest.fixture
def low_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    decision = Decision("human_review", "other", 0.3, ReviewReason.LOW_CONFIDENCE)
    monkeypatch.setattr("triage.pipeline.processor.triage_decision", lambda *_args, **_kwargs: decision)


def _dump(repository: Repository) -> str:
    with sqlite3.connect(repository._path) as connection:  # leitura direta só para conferir o que foi gravado
        return "\n".join(connection.iterdump())


@pytest.mark.usefixtures("low_confidence")
def test_follow_up_sends_the_anonymized_previous_message_and_recovers_the_iptu_source(
    chat_service: AppService, client: FakeClient
) -> None:
    chat_service.submit(FOLLOW_UP, Conversation("c1", 2, (PREVIOUS_RAW,)))

    (message,) = client.messages
    assert "CONVERSA ANTERIOR" in message
    assert "[NOME]" in message and "[CPF]" in message
    assert "IPTU (imposto predial e territorial urbano)" in message
    assert not any(secret in message for secret in RAW_SECRETS)


@pytest.mark.usefixtures("low_confidence")
def test_follow_up_without_the_conversation_does_not_recover_the_iptu_source(
    chat_service: AppService, client: FakeClient
) -> None:
    chat_service.submit(FOLLOW_UP)

    assert client.messages == []


@pytest.mark.usefixtures("low_confidence")
def test_raw_previous_message_never_reaches_the_client_the_database_or_the_log(
    chat_service: AppService, client: FakeClient, repository: Repository, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        chat_service.submit(FOLLOW_UP, Conversation("c1", 2, (PREVIOUS_RAW,)))

    stored = _dump(repository)
    assert FOLLOW_UP in stored
    for secret in RAW_SECRETS:
        assert not any(secret in text for text in (*client.messages, stored, caplog.text))
    assert "negociar o IPTU em atraso" not in stored and "negociar o IPTU em atraso" not in caplog.text


def test_previous_messages_are_sanitized_and_oversized_ones_are_dropped(
    chat_service: AppService, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[Conversation | None] = []

    def capture(_request: object, _deps: object, conversation: Conversation | None) -> ProcessingResult:
        received.append(conversation)
        return ProcessingResult("queued_for_review")

    monkeypatch.setattr("triage.interface.service.process_request", capture)

    chat_service.submit(RG_TEXT, Conversation("c1", 4, ("a" * 2500, "Meu CPF é 123.456.789-09 <b>urgente</b>", "   ")))

    assert received == [Conversation("c1", 4, ("Meu CPF é [CPF] urgente",))]


def test_submit_without_a_conversation_passes_none_to_the_pipeline(
    chat_service: AppService, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: list[Conversation | None] = []

    def capture(_request: object, _deps: object, conversation: Conversation | None) -> ProcessingResult:
        received.append(conversation)
        return ProcessingResult("queued_for_review")

    monkeypatch.setattr("triage.interface.service.process_request", capture)

    chat_service.submit(RG_TEXT)

    assert received == [None]


def test_the_same_question_in_the_chat_is_answered_each_time(service: AppService) -> None:
    kinds = [
        service.submit(RG_TEXT, Conversation("c1", 1)).kind,
        service.submit(RG_TEXT, Conversation("c1", 2, (RG_TEXT,))).kind,
        service.submit(RG_TEXT, Conversation("c2", 1)).kind,
    ]

    assert kinds == [KIND_ANSWERED] * 3


def test_chat_feedback_uses_the_hash_that_was_stored(service: AppService, repository: Repository) -> None:
    conversation = Conversation("c1", 1)
    outcome = service.submit(RG_TEXT, conversation)

    assert repository.already_processed(outcome.request_hash)
    assert service.send_feedback(outcome.request_hash, "up") is True


def test_a_request_without_a_conversation_still_deduplicates(service: AppService) -> None:
    service.submit(RG_TEXT)

    assert service.submit(RG_TEXT).kind == KIND_DUPLICATE


def test_history_turns_comes_from_the_settings(service: AppService, settings: Settings) -> None:
    assert service.history_turns == settings.chat_history_turns == 6
