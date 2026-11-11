"""Renderização das telas Streamlit; toda decisão fica no `AppService` e nos pacotes do núcleo."""

import uuid
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from triage.interface.service import (
    KIND_ANSWERED,
    KIND_ERROR,
    KIND_INVALID,
    AppService,
    SubmitOutcome,
)
from triage.pipeline.processor import Conversation
from triage.storage.schema import RATING_DOWN, RATING_UP

BANNER = "Protótipo acadêmico com dados sintéticos. Não envie dados pessoais reais."
REVIEW_WARNING = "Dados de demonstração; não envie dados pessoais reais. A fila de revisão não exige login."
EMPTY_QUEUE = "Nenhum pedido aguardando revisão."
EXPORT_DIR = Path("output") / "exports"
EXPORT_WARNING = (
    "O texto exportado é o anonimizado, mas pode conter dado pessoal residual: revise-o antes de "
    "levá-lo a data/labeled/."
)
EXPORT_EMPTY = "Nada exportado: não há pedidos rotulados (ou o banco ou a pasta estão inacessíveis)."
NO_LABEL = "(não informar)"
FEEDBACK_THANKS = "Obrigado pela avaliação!"
FEEDBACK_ALREADY = "Sua avaliação já foi registrada."
CHAT_PLACEHOLDER = "Descreva o serviço público de que você precisa"
HISTORY_KEY = "citizen_history"
FEEDBACK_KEY = "citizen_feedback"
CONVERSATION_KEY = "citizen_conversation"
NEW_CONVERSATION_LABEL = "Nova conversa"


@dataclass(frozen=True)
class ChatTurn:
    """Uma pergunta e o desfecho dela; existe só na sessão (exibição e memória da conversa)."""

    question: str
    outcome: SubmitOutcome


def render_banner() -> None:
    st.info(BANNER)


def _show_outcome(outcome: SubmitOutcome) -> None:
    if outcome.kind == KIND_ANSWERED:
        st.success(outcome.message)
    elif outcome.kind in (KIND_INVALID, KIND_ERROR):
        st.warning(outcome.message)
    else:
        st.info(outcome.message)


def _render_feedback(service: AppService, turn_index: int, outcome: SubmitOutcome) -> None:
    """Botões 👍/👎 da resposta `turn_index`; cada resposta tem chaves e estado próprios."""
    if outcome.request_hash is None:
        return
    feedback_notes = st.session_state.setdefault(FEEDBACK_KEY, {})
    if turn_index in feedback_notes:
        st.caption(feedback_notes[turn_index])
        return
    up_column, down_column = st.columns(2)
    for column, rating, label in ((up_column, RATING_UP, "👍"), (down_column, RATING_DOWN, "👎")):
        if column.button(label, key=f"feedback_{turn_index}_{rating}"):
            accepted = service.send_feedback(outcome.request_hash, rating)
            feedback_notes[turn_index] = FEEDBACK_THANKS if accepted else FEEDBACK_ALREADY
            st.rerun()


def _render_history(service: AppService) -> None:
    for turn_index, turn in enumerate(st.session_state.get(HISTORY_KEY, [])):
        with st.chat_message("user"):
            st.text(turn.question)
        with st.chat_message("assistant"):
            _show_outcome(turn.outcome)
            _render_feedback(service, turn_index, turn.outcome)


def _reset_conversation() -> None:
    """Nova conversa: esquece o histórico, a memória e as avaliações da tela e troca o identificador."""
    st.session_state[HISTORY_KEY] = []
    st.session_state[FEEDBACK_KEY] = {}
    st.session_state[CONVERSATION_KEY] = uuid.uuid4().hex


def _current_conversation(service: AppService) -> Conversation:
    """A conversa para o próximo envio: identificador, número da mensagem e só as últimas mensagens anteriores."""
    history = st.session_state.get(HISTORY_KEY, [])
    conversation_id = st.session_state.setdefault(CONVERSATION_KEY, uuid.uuid4().hex)
    recent = tuple(turn.question for turn in history[-service.history_turns :])
    return Conversation(conversation_id, len(history) + 1, recent)


def render_citizen_tab(service: AppService) -> None:
    """Chat com memória: a conversa fica na sessão e as últimas mensagens vão ao serviço como contexto."""
    if st.button(NEW_CONVERSATION_LABEL, key="new_conversation"):
        _reset_conversation()
        st.rerun()
    _render_history(service)
    message = st.chat_input(CHAT_PLACEHOLDER, key="citizen_message")
    if message is None or not message.strip():
        return
    outcome = service.submit(message, _current_conversation(service))
    st.session_state.setdefault(HISTORY_KEY, []).append(ChatTurn(message, outcome))
    st.rerun()


def _render_review_item(service: AppService, entry) -> None:
    confidence = "—" if entry.confidence is None else f"{entry.confidence:.0%}"
    with st.container(border=True):
        st.markdown(f"**Pedido #{entry.id}** · motivo: `{entry.reason}` · {entry.created_at}")
        st.markdown(f"Categoria sugerida: `{entry.category or '—'}` · confiança: {confidence}")
        st.text(entry.anonymized_text)
        note = st.text_input("Nota de resolução", key=f"note_{entry.id}")
        options = [NO_LABEL, *service.label_options()]
        suggested = options.index(entry.category) if entry.category in options else 0
        choice = st.selectbox("Categoria correta", options, index=suggested, key=f"label_{entry.id}")
        if st.button("Marcar como resolvido", key=f"resolve_{entry.id}"):
            service.resolve(entry.id, note, None if choice == NO_LABEL else choice)
            st.rerun()


def _render_export(service: AppService) -> None:
    st.caption(EXPORT_WARNING)
    if st.button("Exportar pedidos rotulados", key="export_labeled"):
        path = service.export_labeled(EXPORT_DIR)
        if path is None:
            st.warning(EXPORT_EMPTY)
        else:
            st.success(f"Exportado em {path}")


def render_review_tab(service: AppService) -> None:
    """Fila pendente com o texto anonimizado e a ação de resolver."""
    st.warning(REVIEW_WARNING)
    entries = service.pending_reviews()
    if not entries:
        st.caption(EMPTY_QUEUE)
    for entry in entries:
        _render_review_item(service, entry)
    _render_export(service)
