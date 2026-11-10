"""Ponto de entrada da interface (`streamlit run app.py`): só monta o serviço e chama as telas."""

import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from triage.config import load_settings
from triage.interface.service import AppService, build_service
from triage.interface.views import render_banner, render_citizen_tab, render_review_tab
from triage.logging_setup import configure_logging
from triage.storage import StorageError

DB_FILENAME = "triage.db"
STARTUP_ERROR_MESSAGE = "Não foi possível iniciar o atendimento (banco de dados inacessível). Tente novamente mais tarde."

logger = logging.getLogger("triage.app")


@st.cache_resource
def _load_service() -> AppService | None:
    """Monta as dependências uma única vez; falha de infraestrutura vira `None` (mensagem na tela, sem traceback)."""
    settings = load_settings()
    configure_logging(settings)
    try:
        return build_service(settings, Path(settings.output_dir) / DB_FILENAME)
    except (StorageError, OSError) as error:
        logger.error("Falha ao montar a interface (%s)", type(error).__name__)
        return None


def main() -> None:
    st.set_page_config(page_title="Triagem de serviços públicos")
    st.title("Triagem de serviços públicos")
    render_banner()
    service = _load_service()
    if service is None:
        st.error(STARTUP_ERROR_MESSAGE)
        return
    citizen_tab, review_tab = st.tabs(["Cidadão", "Revisão"])
    with citizen_tab:
        render_citizen_tab(service)
    with review_tab:
        render_review_tab(service)


main()
