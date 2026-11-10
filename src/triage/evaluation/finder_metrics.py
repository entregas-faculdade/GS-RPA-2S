"""Métricas puras do localizador de fontes: cobertura, acerto entre os que devolveram fonte e falso positivo.

Recebem o `id` esperado de cada pedido (`NO_SOURCE` quando nenhuma fonte aprovada o atende) e o `id` devolvido
(`None` quando o localizador não devolveu fonte). Não leem arquivo nem catálogo, então se testam com exemplos conhecidos.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from triage.automation.finder import FinderMatch

NO_SOURCE = "none"


@dataclass(frozen=True)
class FinderScores:
    """Resultado de um conjunto de pedidos; `None` onde não há base de cálculo (ninguém respondido, nenhum `none`)."""

    size: int
    coverage: float
    answered_accuracy: float | None
    false_positive_rate: float | None


@dataclass(frozen=True)
class ThresholdRow:
    """O resultado para um par de limiares."""

    min_score: float
    margin: float
    scores: FinderScores


def _check_same_size(expected: Sequence[str], predicted: Sequence[object]) -> None:
    if len(expected) != len(predicted):
        raise ValueError(f"Listas de tamanhos diferentes: {len(expected)} e {len(predicted)}")
    if not expected:
        raise ValueError("A amostra está vazia")


def coverage(predicted: Sequence[str | None]) -> float:
    """Fração dos pedidos para os quais o localizador devolveu uma fonte."""
    if not predicted:
        raise ValueError("A amostra está vazia")
    return sum(found is not None for found in predicted) / len(predicted)


def answered_accuracy(expected: Sequence[str], predicted: Sequence[str | None]) -> float | None:
    """Acerto entre os que devolveram fonte (fonte devolvida a um pedido `none` conta como erro); `None` se nenhum."""
    _check_same_size(expected, predicted)
    answered = [(real, found) for real, found in zip(expected, predicted, strict=True) if found is not None]
    if not answered:
        return None
    return sum(real == found for real, found in answered) / len(answered)


def false_positive_rate(expected: Sequence[str], predicted: Sequence[str | None]) -> float | None:
    """Fração dos pedidos `none` para os quais o localizador devolveu uma fonte; `None` se a amostra não tem `none`."""
    _check_same_size(expected, predicted)
    unanswerable = [found for real, found in zip(expected, predicted, strict=True) if real == NO_SOURCE]
    if not unanswerable:
        return None
    return sum(found is not None for found in unanswerable) / len(unanswerable)


def score_finder(expected: Sequence[str], predicted: Sequence[str | None]) -> FinderScores:
    """As três métricas de uma vez, com o tamanho da amostra."""
    _check_same_size(expected, predicted)
    return FinderScores(
        size=len(expected),
        coverage=coverage(predicted),
        answered_accuracy=answered_accuracy(expected, predicted),
        false_positive_rate=false_positive_rate(expected, predicted),
    )


def predictions_at(matches: Sequence[FinderMatch | None], min_score: float, margin: float) -> list[str | None]:
    """O `id` que o localizador devolveria com estes limiares, a partir das melhores entradas sem limiar.

    Mesma regra de `ServiceFinder.find`: abaixo do limiar de pontuação ou de folga, não há fonte.
    """
    return [
        match.entry.id if match is not None and match.score >= min_score and match.margin >= margin else None
        for match in matches
    ]


def threshold_table(
    expected: Sequence[str],
    matches: Sequence[FinderMatch | None],
    min_scores: Sequence[float],
    margins: Sequence[float],
) -> list[ThresholdRow]:
    """Uma linha por par `(min_score, margin)`, na ordem `min_score` e depois `margin`."""
    _check_same_size(expected, matches)
    return [
        ThresholdRow(min_score, margin, score_finder(expected, predictions_at(matches, min_score, margin)))
        for min_score in min_scores
        for margin in margins
    ]
