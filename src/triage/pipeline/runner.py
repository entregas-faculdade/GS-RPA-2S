"""Execução em lote: lê a pasta, processa cada pedido isoladamente e fecha o registro da execução."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from triage.ingestion import read_folder
from triage.pipeline.export import write_interactions_csv
from triage.pipeline.processor import (
    STATUS_ERROR,
    Deps,
    ProcessingResult,
    process_rejection,
    process_request,
    route_to_safe_review,
)
from triage.pipeline.report import RunReport, build_report, write_report

logger = logging.getLogger("triage.pipeline")


def _now() -> datetime:
    return datetime.now(UTC)


def _try_safe_review(fallback: Callable[[], None], source: str) -> None:
    try:
        fallback()
    except Exception as error:  # noqa: BLE001 - o caminho seguro também pode falhar; a execução segue de qualquer forma
        logger.error("Não foi possível encaminhar %s à revisão (%s)", source, type(error).__name__)


def _isolated(
    action: Callable[[], ProcessingResult], source: str, fallback: Callable[[], None] | None = None
) -> ProcessingResult:
    """Roda a ação de um pedido; falha vira `error` (log só com o tipo do erro, sem texto) e a execução continua."""
    try:
        return action()
    except Exception as error:  # noqa: BLE001 - isolamento: um pedido nunca derruba os demais
        logger.error("Falha ao processar %s (%s); seguindo para o próximo", source, type(error).__name__)
        if fallback is not None:
            _try_safe_review(fallback, source)
        return ProcessingResult(STATUS_ERROR)


def _process_folder(input_dir: str | Path, deps: Deps, run_id: int) -> list[ProcessingResult]:
    requests, rejections = read_folder(input_dir)
    results = [
        _isolated(lambda rejection=rejection: process_rejection(rejection, deps, run_id), rejection.source)
        for rejection in rejections
    ]
    for request in requests:
        results.append(
            _isolated(
                lambda request=request: process_request(request, deps, run_id=run_id),
                request.source,
                lambda request=request: route_to_safe_review(request, deps, run_id),
            )
        )
    return results


def run_batch(input_dir: str | Path, deps: Deps) -> RunReport:
    """Processa todos os pedidos da pasta e grava o relatório e o CSV das interações da execução.

    A execução é aberta com `start_run` e sempre fechada com `finish_run`, mesmo se a leitura da pasta
    falhar. Pedidos já processados (mesmo hash) não são refeitos.
    """
    run_id = deps.repository.start_run()
    started_at = _now()
    results: list[ProcessingResult] = []
    try:
        results = _process_folder(input_dir, deps, run_id)
    finally:
        report = build_report(run_id, started_at, _now(), results)
        deps.repository.finish_run(run_id, report.totals)
        write_report(report, deps.settings.output_dir)
        write_interactions_csv(deps.repository, run_id, deps.settings.output_dir)
    logger.info("Execução %d concluída: %s", run_id, report.totals)
    return report
