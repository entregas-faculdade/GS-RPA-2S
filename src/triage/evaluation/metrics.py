"""Métricas puras de classificação: acerto, precisão/recall/F1 por classe, matriz de confusão e revisão humana.

Todas as funções recebem listas de rótulos reais e previstos (e, onde cabe, quais pedidos foram à revisão)
e não leem arquivo nem modelo, então se testam com exemplos de resultado conhecido.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ClassMetrics:
    """Precisão, recall e F1 de uma classe; `support` é quantos pedidos reais ela tem na amostra."""

    precision: float
    recall: float
    f1: float
    support: int


def _check_same_size(first: Sequence[object], second: Sequence[object]) -> None:
    if len(first) != len(second):
        raise ValueError(f"Listas de tamanhos diferentes: {len(first)} e {len(second)}")
    if not first:
        raise ValueError("A amostra está vazia")


def _ratio(numerator: int, denominator: int) -> float:
    """Divisão que devolve 0.0 quando não há base de cálculo (classe sem previsão ou sem exemplo)."""
    return numerator / denominator if denominator else 0.0


def accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    """Fração de previsões iguais ao rótulo real."""
    _check_same_size(y_true, y_pred)
    hits = sum(real == predicted for real, predicted in zip(y_true, y_pred, strict=True))
    return hits / len(y_true)


def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> list[list[int]]:
    """Matriz com uma linha por rótulo real e uma coluna por rótulo previsto, na ordem de `labels`.

    Um rótulo fora de `labels` levanta `ValueError`: a matriz não pode perder pedidos em silêncio.
    """
    _check_same_size(y_true, y_pred)
    position = {label: index for index, label in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for real, predicted in zip(y_true, y_pred, strict=True):
        if real not in position or predicted not in position:
            raise ValueError(f"Rótulo fora da lista de classes: {real!r} / {predicted!r}")
        matrix[position[real]][position[predicted]] += 1
    return matrix


def _class_metrics(matrix: list[list[int]], index: int) -> ClassMetrics:
    true_positive = matrix[index][index]
    predicted_total = sum(row[index] for row in matrix)
    support = sum(matrix[index])
    precision = _ratio(true_positive, predicted_total)
    recall = _ratio(true_positive, support)
    f1 = _ratio(2 * true_positive, predicted_total + support)
    return ClassMetrics(precision, recall, f1, support)


def per_class_metrics(y_true: Sequence[str], y_pred: Sequence[str], labels: Sequence[str]) -> dict[str, ClassMetrics]:
    """Precisão, recall e F1 de cada classe de `labels`; classe sem previsão ou sem exemplo fica com 0.0."""
    matrix = confusion_matrix(y_true, y_pred, labels)
    return {label: _class_metrics(matrix, index) for index, label in enumerate(labels)}


def review_rate(reviewed: Sequence[bool]) -> float:
    """Fração dos pedidos encaminhados à revisão humana."""
    if not reviewed:
        raise ValueError("A amostra está vazia")
    return sum(reviewed) / len(reviewed)


def automatic_coverage(reviewed: Sequence[bool]) -> float:
    """Fração dos pedidos que o robô resolve sozinho (o complemento da taxa de revisão)."""
    return 1.0 - review_rate(reviewed)


def automatic_accuracy(y_true: Sequence[str], y_pred: Sequence[str], reviewed: Sequence[bool]) -> float | None:
    """Acerto só entre os pedidos respondidos sem revisão; `None` se nenhum foi respondido sozinho."""
    _check_same_size(y_true, y_pred)
    _check_same_size(y_true, reviewed)
    answered = [(real, predicted) for real, predicted, sent in zip(y_true, y_pred, reviewed, strict=True) if not sent]
    if not answered:
        return None
    return sum(real == predicted for real, predicted in answered) / len(answered)
