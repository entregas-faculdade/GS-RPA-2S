"""Testes das métricas com amostras pequenas de resultado conhecido."""

from collections.abc import Callable

import pytest

from triage.evaluation import (
    ClassMetrics,
    accuracy,
    automatic_accuracy,
    automatic_coverage,
    confusion_matrix,
    per_class_metrics,
    review_rate,
)

LABELS = ["a", "b", "c"]
Y_TRUE = ["a", "a", "a", "b", "b", "c"]
Y_PRED = ["a", "a", "b", "b", "c", "c"]


def test_accuracy_counts_hits() -> None:
    assert accuracy(Y_TRUE, Y_PRED) == pytest.approx(4 / 6)


def test_accuracy_perfect_and_zero() -> None:
    assert accuracy(["a", "b"], ["a", "b"]) == 1.0
    assert accuracy(["a", "b"], ["b", "a"]) == 0.0


def test_confusion_matrix_rows_are_true_labels() -> None:
    assert confusion_matrix(Y_TRUE, Y_PRED, LABELS) == [[2, 1, 0], [0, 1, 1], [0, 0, 1]]


def test_confusion_matrix_follows_label_order() -> None:
    assert confusion_matrix(["a", "b"], ["b", "b"], ["b", "a"]) == [[1, 0], [1, 0]]


def test_confusion_matrix_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="fora da lista"):
        confusion_matrix(["a", "z"], ["a", "a"], LABELS)


def test_per_class_metrics_known_values() -> None:
    metrics = per_class_metrics(Y_TRUE, Y_PRED, LABELS)
    assert metrics["a"] == ClassMetrics(precision=1.0, recall=pytest.approx(2 / 3), f1=pytest.approx(0.8), support=3)
    assert metrics["b"] == ClassMetrics(precision=0.5, recall=0.5, f1=0.5, support=2)
    assert metrics["c"] == ClassMetrics(precision=0.5, recall=1.0, f1=pytest.approx(2 / 3), support=1)


def test_per_class_metrics_class_never_predicted_nor_present_is_zero() -> None:
    metrics = per_class_metrics(["a", "a"], ["a", "a"], ["a", "b"])
    assert metrics["b"] == ClassMetrics(0.0, 0.0, 0.0, 0)


def test_per_class_metrics_class_never_predicted_has_zero_precision() -> None:
    metrics = per_class_metrics(["a", "b"], ["a", "a"], ["a", "b"])
    assert metrics["b"] == ClassMetrics(0.0, 0.0, 0.0, 1)


def test_review_rate_and_coverage_are_complementary() -> None:
    reviewed = [True, False, False, True, False]
    assert review_rate(reviewed) == pytest.approx(0.4)
    assert automatic_coverage(reviewed) == pytest.approx(0.6)


def test_automatic_accuracy_ignores_reviewed_requests() -> None:
    reviewed = [False, False, False, True, True, True]
    assert automatic_accuracy(Y_TRUE, Y_PRED, reviewed) == pytest.approx(2 / 3)


def test_automatic_accuracy_is_none_when_everything_goes_to_review() -> None:
    assert automatic_accuracy(["a"], ["b"], [True]) is None


@pytest.mark.parametrize("call", [
    lambda: accuracy([], []),
    lambda: accuracy(["a"], ["a", "b"]),
    lambda: confusion_matrix([], [], LABELS),
    lambda: review_rate([]),
    lambda: automatic_accuracy(["a"], ["a"], [True, False]),
])
def test_invalid_input_raises_value_error(call: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        call()
