"""Decisão de triagem: responder sozinho ou encaminhar à revisão humana."""

from dataclasses import dataclass
from enum import Enum

from triage.classification.classifier import SOURCE_RULE, Classification
from triage.classification.urgency import is_urgent
from triage.config import Settings, load_settings

OTHER_LABEL = "other"
RULE_CONFIDENCE_FLOOR = 0.90
ACTION_AUTO_ANSWER = "auto_answer"
ACTION_HUMAN_REVIEW = "human_review"


class ReviewReason(Enum):
    """Motivos fechados para encaminhar um pedido à revisão humana."""

    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS = "ambiguous"
    URGENT = "urgent"
    OUT_OF_CATALOG = "out_of_catalog"
    INVALID_INPUT = "invalid_input"
    LINK_UNAVAILABLE = "link_unavailable"


@dataclass(frozen=True)
class Decision:
    """Ação escolhida, categoria, confiança considerada e motivo (`None` quando responde sozinho)."""

    action: str
    category: str
    confidence: float
    reason: ReviewReason | None


@dataclass(frozen=True)
class _Scores:
    confidence: float
    margin: float


def _scores(classification: Classification) -> _Scores:
    """Confiança da categoria escolhida e folga para a melhor das demais.

    Quando a fonte é uma regra única, a confiança sobe para ao menos `RULE_CONFIDENCE_FLOOR`: o atalho
    inequívoco não deve ser barrado por um modelo tímido, e a folga usa essa mesma confiança.
    """
    probabilities = classification.probabilities
    confidence = probabilities.get(classification.label, 0.0)
    if classification.source == SOURCE_RULE:
        confidence = max(confidence, RULE_CONFIDENCE_FLOOR)
    runner_up = max(
        (value for label, value in probabilities.items() if label != classification.label),
        default=0.0,
    )
    return _Scores(confidence, confidence - runner_up)


def _review_reason(urgent: bool, label: str, scores: _Scores, settings: Settings) -> ReviewReason | None:
    if urgent:
        return ReviewReason.URGENT
    if label == OTHER_LABEL:
        return ReviewReason.OUT_OF_CATALOG
    if scores.confidence < settings.confidence_min:
        return ReviewReason.LOW_CONFIDENCE
    if scores.margin < settings.ambiguity_margin:
        return ReviewReason.AMBIGUOUS
    return None


def triage_decision(
    request_text: str, classification: Classification, settings: Settings | None = None
) -> Decision:
    """Decide entre `auto_answer` e `human_review`.

    Ordem de avaliação fixa; o primeiro gatilho que dispara define o `reason`:
    (a) urgência no texto (vale mesmo com confiança 1.0), (b) categoria `other` (fora do catálogo),
    (c) confiança abaixo de `confidence_min`, (d) diferença para a segunda melhor abaixo de
    `ambiguity_margin`. Nenhum gatilho → `auto_answer` com `reason=None`. Os limiares vêm de `settings`
    (padrão: `load_settings()`). `invalid_input` e `link_unavailable` são decididos fora desta função.
    """
    active_settings = settings if settings is not None else load_settings()
    scores = _scores(classification)
    reason = _review_reason(is_urgent(request_text), classification.label, scores, active_settings)
    action = ACTION_AUTO_ANSWER if reason is None else ACTION_HUMAN_REVIEW
    return Decision(action, classification.label, scores.confidence, reason)
