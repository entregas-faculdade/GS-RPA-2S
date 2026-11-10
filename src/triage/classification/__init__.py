"""Classificação do assunto (regex + TF-IDF), confiança e decisão de revisão."""

from triage.classification.classifier import Classification, classify
from triage.classification.decision import Decision, ReviewReason, triage_decision
from triage.classification.model import ModelNotAvailableError
from triage.classification.urgency import is_urgent

__all__ = [
    "Classification",
    "Decision",
    "ModelNotAvailableError",
    "ReviewReason",
    "classify",
    "is_urgent",
    "triage_decision",
]
