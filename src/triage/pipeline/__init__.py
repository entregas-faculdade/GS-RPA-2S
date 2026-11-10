"""Orquestração das etapas, com retry, idempotência e relatório de execução."""

from triage.pipeline.processor import (
    Deps,
    ProcessingResult,
    build_deps,
    process_request,
)
from triage.pipeline.report import RunReport, build_report, write_report
from triage.pipeline.runner import run_batch
from triage.pipeline.scheduler import watch

__all__ = [
    "Deps",
    "ProcessingResult",
    "RunReport",
    "build_deps",
    "build_report",
    "process_request",
    "run_batch",
    "watch",
    "write_report",
]
