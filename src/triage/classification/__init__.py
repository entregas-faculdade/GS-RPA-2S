"""Classificação do assunto (regex + TF-IDF), confiança e decisão de revisão."""

from triage.classification.classifier import Classification, classify
from triage.classification.model import ModelNotAvailableError

__all__ = ["Classification", "ModelNotAvailableError", "classify"]
