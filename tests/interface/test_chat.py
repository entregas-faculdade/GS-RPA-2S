"""Aba Cidadão em formato de chat, exercitada com `AppTest` e um serviço simulado (sem rede)."""

from streamlit.testing.v1 import AppTest

from triage.interface.service import (
    KIND_ANSWERED,
    KIND_HUMAN_REVIEW,
    KIND_INVALID,
    SubmitOutcome,
)

ANSWER_ONE = "Resposta um https://www.gov.br/um"
ANSWER_TWO = "Resposta dois https://www.gov.br/dois"
REVIEW_MESSAGE = "Encaminhamos seu pedido para atendimento humano."
INVALID_MESSAGE = "Não foi possível ler seu pedido."
FEEDBACK_THANKS = "Obrigado pela avaliação!"


class FakeService:
    """Dublê do `AppService`: registra cada texto recebido e devolve desfechos fixos por texto."""

    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.feedback: list[tuple[str, str]] = []
        self._outcomes = {
            "primeira": SubmitOutcome(KIND_ANSWERED, ANSWER_ONE, "hash-1"),
            "segunda": SubmitOutcome(KIND_ANSWERED, ANSWER_TWO, "hash-2"),
            "urgente": SubmitOutcome(KIND_HUMAN_REVIEW, REVIEW_MESSAGE),
            "ab": SubmitOutcome(KIND_INVALID, INVALID_MESSAGE),
        }

    def submit(self, text: str) -> SubmitOutcome:
        self.submitted.append(text)
        return self._outcomes[text]

    def send_feedback(self, request_hash: str, rating: str) -> bool:
        if any(sent[0] == request_hash for sent in self.feedback):
            return False
        self.feedback.append((request_hash, rating))
        return True


def _run_tab(service: FakeService) -> AppTest:
    def script() -> None:
        import streamlit as st

        from triage.interface.views import render_citizen_tab

        render_citizen_tab(st.session_state["service"])

    app = AppTest.from_function(script)
    app.session_state["service"] = service
    return app.run()


def _send(app: AppTest, text: str) -> AppTest:
    return app.chat_input[0].set_value(text).run()


def _all_values(app: AppTest) -> list[str]:
    values = []
    for message in app.chat_message:
        values.extend(child.value for child in message.children.values() if hasattr(child, "value"))
    return values


def test_answered_question_shows_question_then_answer() -> None:
    app = _send(_run_tab(FakeService()), "primeira")

    assert _all_values(app) == ["primeira", ANSWER_ONE]
    assert not app.exception


def test_two_questions_keep_arrival_order() -> None:
    app = _send(_send(_run_tab(FakeService()), "primeira"), "segunda")

    assert _all_values(app) == ["primeira", ANSWER_ONE, "segunda", ANSWER_TWO]


def test_rating_one_answer_does_not_mark_the_other() -> None:
    service = FakeService()
    app = _send(_send(_run_tab(service), "primeira"), "segunda")

    app.button(key="feedback_0_up").click().run()

    assert service.feedback == [("hash-1", "up")]
    assert [button.key for button in app.button] == ["feedback_1_up", "feedback_1_down"]
    assert FEEDBACK_THANKS in [caption.value for caption in app.caption]


def test_review_and_invalid_outcomes_have_no_rating() -> None:
    app = _send(_send(_run_tab(FakeService()), "urgente"), "ab")

    assert list(app.button) == []
    assert _all_values(app) == ["urgente", REVIEW_MESSAGE, "ab", INVALID_MESSAGE]


def test_blank_message_does_not_call_submit() -> None:
    service = FakeService()

    _send(_run_tab(service), "   ")

    assert service.submitted == []


def test_each_submit_receives_only_the_typed_text() -> None:
    service = FakeService()

    _send(_send(_run_tab(service), "primeira"), "segunda")

    assert service.submitted == ["primeira", "segunda"]


def test_new_session_starts_with_empty_conversation() -> None:
    service = FakeService()
    _send(_run_tab(service), "primeira")

    fresh = _run_tab(service)

    assert list(fresh.chat_message) == []
