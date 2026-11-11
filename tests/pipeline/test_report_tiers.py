"""Relatório: contagem de respondidos por degrau, no JSON e no Markdown, sem texto de pedido."""

import json
from datetime import UTC, datetime, timedelta

from triage.pipeline import ProcessingResult, build_report
from triage.pipeline.report import render_markdown

START = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def _answered(tier: str) -> ProcessingResult:
    return ProcessingResult("answered", "id_card", 0.9, response_text="texto da resposta", link_status="ok", tier=tier)


def _report(results: list[ProcessingResult]):
    return build_report(1, START, START + timedelta(seconds=2), results)


def test_report_counts_answered_by_tier() -> None:
    results = [
        _answered("catalog"),
        _answered("catalog"),
        _answered("finder"),
        ProcessingResult("queued_for_review", reason="out_of_catalog", response_text="não tenho"),
    ]

    report = _report(results)

    assert report.tiers == {"catalog": 2, "finder": 1}
    assert report.to_dict()["tiers"] == {"catalog": 2, "finder": 1}


def test_report_without_answers_has_zero_tiers() -> None:
    assert _report([ProcessingResult("skipped_duplicate")]).tiers == {"catalog": 0, "finder": 0}


def test_markdown_shows_the_tier_table() -> None:
    markdown = render_markdown(_report([_answered("catalog"), _answered("finder"), _answered("finder")]))

    assert "## Respondidos por degrau" in markdown
    assert "| serviço específico do catálogo | 1 |" in markdown
    assert "| fonte achada pelo localizador | 2 |" in markdown


def test_report_never_carries_response_text() -> None:
    report = _report([_answered("finder")])

    assert "texto da resposta" not in json.dumps(report.to_dict(), ensure_ascii=False)
    assert "texto da resposta" not in render_markdown(report)
