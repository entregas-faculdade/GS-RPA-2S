"""`AppService`: o que a tela mostra em cada desfecho dos degraus (resposta, revisão com mensagem, revisão genérica)."""

import pytest
from sklearn.pipeline import Pipeline

from triage.automation.allowlist import load_allowed_suffixes
from triage.automation.catalog import Link, ServiceEntry, load_catalog
from triage.automation.finder import FinderMatch
from triage.automation.link_check import LinkStatus
from triage.automation.messages import build_no_information_message
from triage.automation.resolver import CatalogLookup
from triage.classification.decision import Decision, ReviewReason
from triage.config import Settings
from triage.interface.service import (
    KIND_ANSWERED,
    KIND_HUMAN_REVIEW,
    MESSAGE_HUMAN_REVIEW,
    AppService,
)
from triage.pipeline import Deps
from triage.storage import Repository

URGENT_TEXT = "Meu benefício foi cortado e preciso de ajuda urgente hoje."
ALVARA_TEXT = "Quero tirar o alvará de funcionamento do meu comércio."
PORTAL = ServiceEntry(
    id="gap_city",
    category=None,
    kind="portal",
    scope="municipal",
    coverage="Cidade de São Paulo",
    area="city",
    display_name="Atendimento da Prefeitura",
    agency="Prefeitura",
    instructions="Acesse o portal.",
    keywords=("alvara",),
    links=(Link("Portal geral", "https://www.gov.br/portal-geral"),),
    phones=(),
    source_note="fonte",
    verified_on="2026-11-09",
    status="approved",
)


class FakeFinder:
    def __init__(self, entry: ServiceEntry | None) -> None:
        self.entry = entry

    def find(self, _text: str) -> FinderMatch | None:
        return None if self.entry is None else FinderMatch(self.entry, 0.9, 0.5)


def _service(
    repository: Repository, settings: Settings, model: Pipeline, finder: FakeFinder | None = None
) -> AppService:
    lookup = CatalogLookup([*load_catalog(extra_dir=None), PORTAL], load_allowed_suffixes(), lambda _url: LinkStatus(True, 200, None))
    return AppService(Deps(repository=repository, lookup=lookup, settings=settings, model=model, finder=finder))


def _decide(monkeypatch: pytest.MonkeyPatch, reason: ReviewReason) -> None:
    decision = Decision("human_review", "other", 0.5, reason)
    monkeypatch.setattr("triage.pipeline.processor.triage_decision", lambda *_args, **_kwargs: decision)


def test_urgent_request_shows_emergency_phones_without_feedback_buttons(
    repository: Repository, settings: Settings, trained_model: Pipeline
) -> None:
    outcome = _service(repository, settings, trained_model).submit(URGENT_TEXT)

    assert outcome.kind == KIND_HUMAN_REVIEW
    assert "ligue agora" in outcome.message
    assert "192" in outcome.message
    assert "urgent" not in outcome.message
    assert outcome.request_hash is None


def test_source_found_shows_answer_with_feedback_buttons(
    repository: Repository, settings: Settings, trained_model: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _decide(monkeypatch, ReviewReason.OUT_OF_CATALOG)
    service = _service(repository, settings, trained_model, FakeFinder(PORTAL))

    outcome = service.submit(ALVARA_TEXT)

    assert outcome.kind == KIND_ANSWERED
    assert outcome.message.startswith("Não encontrei um serviço específico")
    assert outcome.request_hash is not None
    assert service.send_feedback(outcome.request_hash, "down") is True
    assert service.pending_reviews() == []


def test_source_not_found_shows_no_information_without_feedback_buttons(
    repository: Repository, settings: Settings, trained_model: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _decide(monkeypatch, ReviewReason.LOW_CONFIDENCE)
    service = _service(repository, settings, trained_model, FakeFinder(None))

    outcome = service.submit(ALVARA_TEXT)

    assert (outcome.kind, outcome.message, outcome.request_hash) == (
        KIND_HUMAN_REVIEW,
        build_no_information_message(),
        None,
    )
    assert [entry.reason for entry in service.pending_reviews()] == ["low_confidence"]


def test_review_without_message_keeps_the_generic_text(
    repository: Repository, settings: Settings, trained_model: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    _decide(monkeypatch, ReviewReason.AMBIGUOUS)

    outcome = _service(repository, settings, trained_model, FakeFinder(PORTAL)).submit(ALVARA_TEXT)

    assert (outcome.kind, outcome.message, outcome.request_hash) == (KIND_HUMAN_REVIEW, MESSAGE_HUMAN_REVIEW, None)
