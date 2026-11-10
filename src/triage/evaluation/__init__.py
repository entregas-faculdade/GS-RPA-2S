"""Métricas de validação do classificador sobre o conjunto rotulado."""

from triage.evaluation.metrics import (
    ClassMetrics,
    accuracy,
    automatic_accuracy,
    automatic_coverage,
    confusion_matrix,
    per_class_metrics,
    review_rate,
)

__all__ = [
    "ClassMetrics",
    "accuracy",
    "automatic_accuracy",
    "automatic_coverage",
    "confusion_matrix",
    "per_class_metrics",
    "review_rate",
]
