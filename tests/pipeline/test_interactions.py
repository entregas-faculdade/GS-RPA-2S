"""Catalogação da interação no pipeline: categoria, origem, tag `needs_human` e resposta gravada (cliente falso)."""

import dataclasses
from collections.abc import Callable

import pytest

from triage.automation.llm_client import LlmInvalidResponse, LlmUnavailable
from triage.automation.topics import CATEGORIZE_TASK, TopicsError
from triage.classification.decision import Decision, ReviewReason
from triage.ingestion import Rejection, Request
from triage.pipeline import Deps, ProcessingResult, process_request
from triage.pipeline.processor import process_rejection, route_to_safe_review
from triage.storage import StorageError, StoredInteraction

RG_TEXT = "Preciso saber como emitir a segunda via do meu RG. Nunca fiz esse pedido antes."
URGENT_TEXT = "Meu benefício foi cortado e preciso de ajuda urgente hoje."
PII_TEXT = "Meu CPF é 123.456.789-09, e-mail fulano@example.com. Quero a segunda via do RG, carteira de identidade."
MakeDeps = Callable[..., Deps]


class FakeClient:
    """Responde a saída combinada (texto ou exceção) e guarda as chamadas."""

    def __init__(self, answer: str | BaseException = "tax") -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def complete(self, task: str, user_message: str) -> str:
        self.calls.append((task, user_message))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def _request(text: str = RG_TEXT) -> Request:
    return Request("r1", text, "r1.txt")


def _with_llm(make_deps: MakeDeps, client: FakeClient, **overrides: object) -> Deps:
    enabled = dataclasses.replace(make_deps().settings, llm_enabled=True)
    return make_deps(llm_client=client, settings=enabled, **overrides)


def _only_interaction(deps: Deps) -> StoredInteraction:
    (stored,) = deps.repository.interactions()
    return stored


@pytest.fixture
def decide(monkeypatch: pytest.MonkeyPatch) -> Callable[[ReviewReason], None]:
    def fix(reason: ReviewReason) -> None:
        decision = Decision("human_review", "other", 0.9, reason)
        monkeypatch.setattr("triage.pipeline.processor.triage_decision", lambda *_args, **_kwargs: decision)

    return fix


def test_answered_without_llm_uses_the_service_area(make_deps: MakeDeps) -> None:
    deps = make_deps()

    result = process_request(_request(), deps, run_id=3)

    stored = _only_interaction(deps)
    assert (result.topic, result.topic_source, result.needs_human) == ("documents", "catalog", False)
    assert (stored.record.topic, stored.record.topic_source, stored.record.needs_human) == ("documents", "catalog", False)
    assert (stored.record.tier, stored.record.run_id) == ("catalog", 3)
    assert stored.record.response_text == result.response_text
    assert result.service is None


def test_the_chat_has_no_run(make_deps: MakeDeps) -> None:
    deps = make_deps()

    process_request(_request(), deps)

    assert _only_interaction(deps).record.run_id is None


def test_a_valid_llm_id_is_the_topic(make_deps: MakeDeps) -> None:
    client = FakeClient("tax")
    deps = _with_llm(make_deps, client)

    result = process_request(_request(), deps)

    assert (result.topic, result.topic_source, result.status) == ("tax", "llm", "answered")
    assert [task for task, _ in client.calls] == [CATEGORIZE_TASK]
    assert _only_interaction(deps).record.topic_source == "llm"


def test_the_llm_receives_only_the_anonymized_text(make_deps: MakeDeps) -> None:
    client = FakeClient()

    process_request(_request(PII_TEXT), _with_llm(make_deps, client))

    (_task, message) = client.calls[0]
    assert "123.456.789-09" not in message
    assert "fulano@example.com" not in message


@pytest.mark.parametrize("error", [LlmUnavailable("Timeout"), LlmInvalidResponse("vazio"), "uma frase qualquer"])
def test_an_llm_failure_falls_back_and_the_answer_is_still_delivered(
    make_deps: MakeDeps, error: BaseException | str
) -> None:
    deps = _with_llm(make_deps, FakeClient(error))

    result = process_request(_request(), deps)

    assert (result.status, result.topic, result.topic_source) == ("answered", "documents", "catalog")
    assert "https://" in result.response_text


def test_urgency_is_safety_by_rule_and_never_calls_the_llm(make_deps: MakeDeps) -> None:
    client = FakeClient()
    deps = _with_llm(make_deps, client)

    result = process_request(_request(URGENT_TEXT), deps)

    assert (result.topic, result.topic_source, result.reason) == ("safety", "rule", "urgent")
    assert client.calls == []


def test_urgency_never_calls_the_llm_even_without_a_model(make_deps: MakeDeps) -> None:
    client = FakeClient()

    result = process_request(_request(URGENT_TEXT), _with_llm(make_deps, client, model=None))

    assert (result.topic, result.topic_source) == ("safety", "rule")
    assert client.calls == []


def test_a_rejection_has_no_topic_needs_human_and_never_calls_the_llm(make_deps: MakeDeps) -> None:
    client = FakeClient()
    deps = _with_llm(make_deps, client)

    result = process_rejection(Rejection("vazio.txt", "arquivo vazio"), deps, run_id=2)

    stored = _only_interaction(deps)
    assert (result.topic, result.topic_source, result.needs_human) == (None, "none", True)
    assert (stored.record.topic, stored.record.topic_source, stored.record.needs_human) == (None, "none", True)
    assert (stored.status, stored.review_reason, stored.record.run_id) == ("rejected", "invalid_input", 2)
    assert client.calls == []


def test_the_tag_is_true_for_every_review_reason(make_deps: MakeDeps, decide: Callable[[ReviewReason], None]) -> None:
    flags: dict[str, bool] = {}
    for reason in (ReviewReason.OUT_OF_CATALOG, ReviewReason.LOW_CONFIDENCE, ReviewReason.AMBIGUOUS):
        decide(reason)
        flags[reason.value] = process_request(_request(f"pedido {reason.value}"), make_deps()).needs_human
    flags["urgent"] = process_request(_request(URGENT_TEXT), make_deps()).needs_human
    flags["link_unavailable"] = process_request(_request(), make_deps(link_ok=False)).needs_human
    flags["invalid_input"] = process_rejection(Rejection("x.txt", "vazio"), make_deps()).needs_human

    assert flags == {reason.value: True for reason in ReviewReason}


def test_the_tag_is_false_when_the_robot_answered(make_deps: MakeDeps) -> None:
    assert process_request(_request(), make_deps()).needs_human is False


def test_the_tag_matches_the_review_queue_exactly(make_deps: MakeDeps) -> None:
    deps = make_deps()
    process_request(_request(), deps)
    process_request(_request(URGENT_TEXT), deps)
    process_rejection(Rejection("x.txt", "vazio"), deps)

    queued = {item.request_hash for item in deps.repository.pending_reviews()}
    flagged = {item.record.request_hash for item in deps.repository.interactions() if item.record.needs_human}

    assert queued == flagged
    assert len(deps.repository.interactions()) == 3


def test_a_duplicate_creates_no_new_interaction(make_deps: MakeDeps) -> None:
    deps = make_deps()
    process_request(_request(), deps)

    result = process_request(_request(), deps)

    assert result.status == "skipped_duplicate"
    assert (result.topic, result.topic_source, result.needs_human) == (None, None, False)
    assert len(deps.repository.interactions()) == 1


def test_a_duplicate_rejection_creates_no_new_interaction(make_deps: MakeDeps) -> None:
    deps = make_deps()
    process_rejection(Rejection("x.txt", "vazio"), deps)

    process_rejection(Rejection("x.txt", "vazio"), deps)

    assert len(deps.repository.interactions()) == 1


def test_the_safe_review_catalogs_without_calling_the_llm(make_deps: MakeDeps) -> None:
    client = FakeClient()
    deps = _with_llm(make_deps, client)

    route_to_safe_review(_request(), deps, run_id=4)

    stored = _only_interaction(deps)
    assert stored.record.needs_human is True
    assert stored.record.topic_source in {"classifier", "catalog", "rule"}
    assert stored.record.run_id == 4
    assert client.calls == []


def test_a_failing_interaction_table_does_not_undo_the_request_or_the_queue(
    make_deps: MakeDeps, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    deps = make_deps()

    def broken(_record: object) -> None:
        raise StorageError("falha")

    monkeypatch.setattr(deps.repository, "save_interaction", broken)

    queued = process_request(_request(URGENT_TEXT), deps)
    answered = process_request(_request(), deps)

    assert (queued.status, answered.status) == ("queued_for_review", "answered")
    assert len(deps.repository.pending_reviews()) == 1
    assert "Interação não catalogada" in caplog.text
    assert "ajuda urgente" not in caplog.text


def test_an_invalid_vocabulary_leaves_the_interaction_without_a_topic(
    make_deps: MakeDeps, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise TopicsError("vocabulário quebrado")

    monkeypatch.setattr("triage.pipeline.processor.choose_topic", broken)

    result = process_request(_request(), make_deps())

    assert (result.status, result.topic, result.topic_source) == ("answered", None, "none")


def test_only_anonymized_text_reaches_the_interaction(make_deps: MakeDeps) -> None:
    deps = make_deps()

    process_request(_request(PII_TEXT), deps)

    stored = _only_interaction(deps)
    assert "123.456.789-09" not in stored.anonymized_text
    assert "123.456.789-09" not in (stored.record.response_text or "")


def test_the_result_carries_no_citizen_text(make_deps: MakeDeps) -> None:
    result: ProcessingResult = process_request(_request(PII_TEXT), make_deps())

    assert "123.456.789-09" not in repr(result)
