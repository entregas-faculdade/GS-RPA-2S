"""Reexecução periódica do robô."""

import logging
from pathlib import Path
from threading import Event

from triage.pipeline.processor import Deps
from triage.pipeline.runner import run_batch

logger = logging.getLogger("triage.pipeline")


def _run_round(input_dir: str | Path, deps: Deps) -> None:
    try:
        run_batch(input_dir, deps)
    except Exception as error:  # noqa: BLE001 - uma rodada ruim não pode matar o agendador
        logger.error("Rodada falhou (%s); tentando de novo na próxima", type(error).__name__)


def watch(input_dir: str | Path, interval_seconds: float, deps: Deps, stop_event: Event) -> None:
    """Chama `run_batch` a cada `interval_seconds` até `stop_event` ser acionado ou Ctrl+C.

    Erro numa rodada é logado e o laço segue; a idempotência faz os arquivos já processados não repetirem.

    Agendamento externo (alternativa a este laço): rode `python run.py --input <pasta> --output <pasta>`
    pelo cron (`*/10 * * * * cd /caminho && python run.py`) ou pelo Agendador de Tarefas do Windows
    (ação "Iniciar um programa": `python`, argumentos `run.py --input <pasta>`, iniciar em: a raiz do repositório).
    """
    try:
        while not stop_event.is_set():
            _run_round(input_dir, deps)
            stop_event.wait(interval_seconds)
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário; encerrando o agendador")
