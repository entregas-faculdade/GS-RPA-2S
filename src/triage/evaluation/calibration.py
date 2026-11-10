"""Calibração dos limiares por validação cruzada estratificada, só sobre o conjunto de treino.

As funções são puras: o treino do modelo entra por injeção (`fit_predict`), então a lógica se testa sem
sklearn. A decisão de cada pedido é a do robô (`triage_decision`), para a tabela de limiares refletir o que
o robô de fato faria, e nunca se usa o conjunto de teste para escolher limiar.
"""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from sklearn.base import clone
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from triage.classification.classifier import SOURCE_MODEL, SOURCE_RULE, Classification
from triage.classification.decision import ACTION_HUMAN_REVIEW, triage_decision
from triage.classification.rules import match_categories
from triage.config import Settings
from triage.evaluation.metrics import automatic_accuracy, automatic_coverage

DEFAULT_FOLDS = 5
RANDOM_STATE = 42

FitPredict = Callable[[Sequence[str], Sequence[str], Sequence[str]], list[dict[str, float]]]


@dataclass(frozen=True)
class ThresholdRow:
    """Cobertura automática e acurácia entre os respondidos para um par de limiares."""

    confidence_min: float
    ambiguity_margin: float
    coverage: float
    accuracy: float | None


def _check_same_size(first: Sequence[object], second: Sequence[object]) -> None:
    if len(first) != len(second):
        raise ValueError(f"Listas de tamanhos diferentes: {len(first)} e {len(second)}")
    if not first:
        raise ValueError("A amostra está vazia")


def clone_fit_predict(template: Pipeline) -> FitPredict:
    """Treina uma cópia não treinada de `template` (mesmos hiperparâmetros) e devolve as probabilidades."""

    def fit_predict(
        train_texts: Sequence[str], train_labels: Sequence[str], test_texts: Sequence[str]
    ) -> list[dict[str, float]]:
        fitted = clone(template).fit(list(train_texts), list(train_labels))
        rows = fitted.predict_proba(list(test_texts))
        return [{label: float(value) for label, value in zip(fitted.classes_, row, strict=True)} for row in rows]

    return fit_predict


def out_of_fold_probabilities(
    texts: Sequence[str], labels: Sequence[str], fit_predict: FitPredict, folds: int = DEFAULT_FOLDS
) -> list[dict[str, float]]:
    """Probabilidades de cada texto vindas de um modelo que não o viu no treino (validação cruzada).

    Estratificada em `folds` partes, com semente fixa; a saída segue a ordem de `texts`. Levanta
    `ValueError` com entrada vazia, tamanhos diferentes ou classe com menos exemplos que partes.
    """
    _check_same_size(texts, labels)
    smallest = min(Counter(labels).values())
    if smallest < folds:
        raise ValueError(f"Classe com {smallest} exemplos não cabe em {folds} partes")
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE)
    result: list[dict[str, float]] = [{} for _ in texts]
    for train_index, test_index in splitter.split(list(texts), list(labels)):
        predicted = fit_predict(
            [texts[i] for i in train_index], [labels[i] for i in train_index], [texts[i] for i in test_index]
        )
        for position, probabilities in zip(test_index, predicted, strict=True):
            result[position] = probabilities
    return result


def classifications_from_probabilities(
    texts: Sequence[str], probabilities: Sequence[dict[str, float]]
) -> list[Classification]:
    """Monta a `Classification` que `classify` devolveria: regra única decide; senão, o modelo."""
    _check_same_size(texts, probabilities)
    result = []
    for text, scores in zip(texts, probabilities, strict=True):
        matched = match_categories(text)
        if len(matched) == 1:
            (label,) = matched
            result.append(Classification(label, scores, SOURCE_RULE))
        else:
            result.append(Classification(max(scores, key=scores.__getitem__), scores, SOURCE_MODEL))
    return result


def threshold_table(
    texts: Sequence[str],
    y_true: Sequence[str],
    classifications: Sequence[Classification],
    settings_grid: Sequence[Settings],
) -> list[ThresholdRow]:
    """Para cada `Settings` da grade, a cobertura automática e a acurácia entre os respondidos sozinhos."""
    _check_same_size(texts, y_true)
    _check_same_size(texts, classifications)
    if not settings_grid:
        raise ValueError("A grade de limiares está vazia")
    rows = []
    for settings in settings_grid:
        decisions = [triage_decision(text, found, settings) for text, found in zip(texts, classifications, strict=True)]
        reviewed = [decision.action == ACTION_HUMAN_REVIEW for decision in decisions]
        predicted = [found.label for found in classifications]
        rows.append(
            ThresholdRow(
                settings.confidence_min,
                settings.ambiguity_margin,
                automatic_coverage(reviewed),
                automatic_accuracy(y_true, predicted, reviewed),
            )
        )
    return rows


def confidence_grid(base: Settings, thresholds: Sequence[float]) -> list[Settings]:
    """Uma cópia de `base` por valor de `CONFIDENCE_MIN` (a folga de ambiguidade não muda)."""
    return [replace(base, confidence_min=value) for value in thresholds]


def margin_grid(base: Settings, margins: Sequence[float]) -> list[Settings]:
    """Uma cópia de `base` por valor de `AMBIGUITY_MARGIN` (o mínimo de confiança não muda)."""
    return [replace(base, ambiguity_margin=value) for value in margins]


def mean_confidence_by_outcome(
    texts: Sequence[str],
    y_true: Sequence[str],
    classifications: Sequence[Classification],
    settings: Settings,
) -> tuple[float | None, float | None]:
    """Confiança média dos acertos e dos erros (`None` quando não há acerto ou não há erro)."""
    _check_same_size(texts, y_true)
    _check_same_size(texts, classifications)
    hits: list[float] = []
    errors: list[float] = []
    for text, real, found in zip(texts, y_true, classifications, strict=True):
        confidence = triage_decision(text, found, settings).confidence
        (hits if found.label == real else errors).append(confidence)
    return _mean(hits), _mean(errors)


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None
