"""Renderização das telas Streamlit; toda decisão fica no `AppService` e nos pacotes do núcleo."""

import streamlit as st

from triage.interface.service import (
    KIND_ANSWERED,
    KIND_ERROR,
    KIND_INVALID,
    AppService,
    SubmitOutcome,
)
from triage.storage.schema import RATING_DOWN, RATING_UP

BANNER = "Protótipo acadêmico com dados sintéticos. Não envie dados pessoais reais."
REVIEW_WARNING = "Dados de demonstração; não envie dados pessoais reais. A fila de revisão não exige login."
EMPTY_QUEUE = "Nenhum pedido aguardando revisão."
FEEDBACK_THANKS = "Obrigado pela avaliação!"
FEEDBACK_ALREADY = "Sua avaliação já foi registrada."
OUTCOME_KEY = "citizen_outcome"
RATED_KEY = "citizen_rated"


def render_banner() -> None:
    st.info(BANNER)


def _show_outcome(outcome: SubmitOutcome) -> None:
    if outcome.kind == KIND_ANSWERED:
        st.success(outcome.message)
    elif outcome.kind in (KIND_INVALID, KIND_ERROR):
        st.warning(outcome.message)
    else:
        st.info(outcome.message)


def _render_feedback(service: AppService, outcome: SubmitOutcome) -> None:
    if outcome.request_hash is None:
        return
    if st.session_state.get(RATED_KEY) == outcome.request_hash:
        st.caption(FEEDBACK_THANKS)
        return
    up_column, down_column = st.columns(2)
    for column, rating, label in ((up_column, RATING_UP, "👍"), (down_column, RATING_DOWN, "👎")):
        if column.button(label, key=f"feedback_{rating}"):
            if not service.send_feedback(outcome.request_hash, rating):
                st.caption(FEEDBACK_ALREADY)
            st.session_state[RATED_KEY] = outcome.request_hash
            st.rerun()


def render_citizen_tab(service: AppService) -> None:
    """Caixa de pedido, resposta (ou aviso de encaminhamento) e avaliação 👍/👎."""
    text = st.text_area("Descreva o serviço público de que você precisa", key="citizen_text")
    if st.button("Enviar pedido"):
        st.session_state[OUTCOME_KEY] = service.submit(text)
        st.session_state.pop(RATED_KEY, None)
    outcome = st.session_state.get(OUTCOME_KEY)
    if outcome is None:
        return
    _show_outcome(outcome)
    _render_feedback(service, outcome)


def _render_review_item(service: AppService, entry) -> None:
    confidence = "—" if entry.confidence is None else f"{entry.confidence:.0%}"
    with st.container(border=True):
        st.markdown(f"**Pedido #{entry.id}** · motivo: `{entry.reason}` · {entry.created_at}")
        st.markdown(f"Categoria sugerida: `{entry.category or '—'}` · confiança: {confidence}")
        st.text(entry.anonymized_text)
        note = st.text_input("Nota de resolução", key=f"note_{entry.id}")
        if st.button("Marcar como resolvido", key=f"resolve_{entry.id}"):
            service.resolve(entry.id, note)
            st.rerun()


def render_review_tab(service: AppService) -> None:
    """Fila pendente com o texto anonimizado e a ação de resolver."""
    st.warning(REVIEW_WARNING)
    entries = service.pending_reviews()
    if not entries:
        st.caption(EMPTY_QUEUE)
    for entry in entries:
        _render_review_item(service, entry)
