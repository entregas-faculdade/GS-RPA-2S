"""Relatório de execução: totais, categorias, motivos, links e LLM — sem texto de pedido e sem PII."""

import json
import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from triage.pipeline.processor import (
    LINK_OK,
    LINK_UNAVAILABLE,
    STATUS_ERROR,
    STATUS_SKIPPED_DUPLICATE,
    ProcessingResult,
)
from triage.storage.schema import (
    STATUS_ANSWERED,
    STATUS_QUEUED_FOR_REVIEW,
    STATUS_REJECTED,
)

REPORT_SUBDIR = "reports"
STATUS_ORDER = (STATUS_ANSWERED, STATUS_QUEUED_FOR_REVIEW, STATUS_REJECTED, STATUS_SKIPPED_DUPLICATE, STATUS_ERROR)
STATUS_LABELS = {
    STATUS_ANSWERED: "respondidos",
    STATUS_QUEUED_FOR_REVIEW: "encaminhados à revisão",
    STATUS_REJECTED: "rejeitados na ingestão",
    STATUS_SKIPPED_DUPLICATE: "já processados (ignorados)",
    STATUS_ERROR: "com erro",
}
REVIEW_STATUSES = (STATUS_QUEUED_FOR_REVIEW, STATUS_REJECTED)
LINK_LABELS = {LINK_OK: "no ar", LINK_UNAVAILABLE: "fora do ar"}
FILE_TIMESTAMP_FORMAT ="%Y%m%dT%H%M%S"

logger = logging.getLogger("triage.pipeline")


@dataclass(frozen=True)
class RunReport:
    """Resumo de uma execução; `links` conta por pedido (um link repetido conta em cada pedido que o usou)."""

    run_id: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    totals: dict[str, int]
    by_category: dict[str, int]
    by_review_reason: dict[str, int]
    links: dict[str, int]
    llm: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "totals": self.totals,
            "by_category": self.by_category,
            "by_review_reason": self.by_review_reason,
            "links": self.links,
            "llm": self.llm,
        }


def build_report(
    run_id: int, started_at: datetime, finished_at: datetime, results: Iterable[ProcessingResult]
) -> RunReport:
    """Agrega os desfechos da execução."""
    outcomes = list(results)
    status_count = Counter(result.status for result in outcomes)
    categories = Counter(result.category for result in outcomes if result.category is not None)
    reasons = Counter(
        result.reason for result in outcomes if result.status in REVIEW_STATUSES and result.reason
    )
    link_count = Counter(result.link_status for result in outcomes if result.link_status)
    fallbacks = Counter(result.fallback_reason for result in outcomes if result.fallback_reason)
    return RunReport(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round((finished_at - started_at).total_seconds(), 3),
        totals={status: status_count.get(status, 0) for status in STATUS_ORDER},
        by_category=dict(sorted(categories.items())),
        by_review_reason=dict(sorted(reasons.items())),
        links={LINK_OK: link_count.get(LINK_OK, 0), LINK_UNAVAILABLE: link_count.get(LINK_UNAVAILABLE, 0)},
        llm={"used": sum(result.used_llm for result in outcomes), "fallbacks": dict(sorted(fallbacks.items()))},
    )


def _table(title: str, counts: dict[str, int]) -> list[str]:
    if not counts:
        return [f"## {title}", "", "Nenhum registro.", ""]
    rows = [f"| {name} | {value} |" for name, value in counts.items()]
    return [f"## {title}", "", "| Item | Quantidade |", "|---|---|", *rows, ""]


def render_markdown(report: RunReport) -> str:
    """Versão legível do relatório, em português."""
    totals = {STATUS_LABELS[status]: count for status, count in report.totals.items()}
    links = {LINK_LABELS[status]: count for status, count in report.links.items()}
    lines = [
        f"# Relatório da execução {report.run_id}",
        "",
        f"- Início: {report.started_at.isoformat()}",
        f"- Fim: {report.finished_at.isoformat()}",
        f"- Duração: {report.duration_seconds} s",
        "",
        *_table("Totais por status", totals),
        *_table("Por categoria", report.by_category),
        *_table("Por motivo de revisão", report.by_review_reason),
        *_table("Links do catálogo (por pedido)", links),
        "## LLM",
        "",
        f"- Respostas reformuladas pelo LLM: {report.llm['used']}",
        f"- Fallbacks para o template: {report.llm['fallbacks'] or 'nenhum'}",
        "",
    ]
    return "\n".join(lines)


def write_report(report: RunReport, output_dir: str | Path) -> tuple[Path, Path]:
    """Grava `run-<data>-<id>.json` e `.md` em `<output_dir>/reports/`; devolve os dois caminhos."""
    folder = Path(output_dir) / REPORT_SUBDIR
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"run-{report.started_at.strftime(FILE_TIMESTAMP_FORMAT)}-{report.run_id}"
    json_path = folder / f"{stem}.json"
    markdown_path = folder / f"{stem}.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    logger.info("Relatório gravado em %s", json_path)
    return json_path, markdown_path
