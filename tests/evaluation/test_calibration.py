"""Testes da calibração por validação cruzada, com amostras pequenas de resultado conhecido."""

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from triage.classification.classifier import SOURCE_MODEL, SOURCE_RULE, Classification
from triage.classification.model import train
from triage.config import Settings
from triage.evaluation.calibration import (
    ThresholdRow,
    classifications_from_probabilities,
    clone_fit_predict,
    confidence_grid,
    margin_grid,
    mean_confidence_by_outcome,
    out_of_fold_probabilities,
    threshold_table,
)

SETTINGS = Settings(
    llm_enabled=False, llm_base_url="", llm_model="", llm_api_key="", log_level="INFO", output_dir="output"
)
NO_MARGIN = replace(SETTINGS, ambiguity_margin=0.0)
NEUTRAL_TEXT = "texto sem termo de urgência nem atalho"
LABELS = ["a"] * 5 + ["b"] * 5


def _constant_fit_predict(
    train_texts: Sequence[str], train_labels: Sequence[str], test_texts: Sequence[str]
) -> list[dict[str, float]]:
    return [{"a": 0.7, "b": 0.3} for _ in test_texts]


def _classification(label: str, top: float) -> Classification:
    other = "b" if label == "a" else "a"
    return Classification(label, {label: top, other: 1 - top}, SOURCE_MODEL)


def test_out_of_fold_returns_one_entry_per_text_in_order() -> None:
    texts = [f"t{index}" for index in range(10)]
    seen: list[list[str]] = []

    def fit_predict(
        train_texts: Sequence[str], train_labels: Sequence[str], test_texts: Sequence[str]
    ) -> list[dict[str, float]]:
        seen.append(list(test_texts))
        return [{"a": float(text[1:]) / 10, "b": 0.0} for text in test_texts]

    result = out_of_fold_probabilities(texts, LABELS, fit_predict, folds=5)
    assert [entry["a"] for entry in result] == pytest.approx([index / 10 for index in range(10)])
    assert sorted(text for part in seen for text in part) == sorted(texts)
    assert all(len(part) == 2 for part in seen)


def test_out_of_fold_never_trains_on_the_texts_it_predicts() -> None:
    texts = [f"t{index}" for index in range(10)]

    def fit_predict(
        train_texts: Sequence[str], train_labels: Sequence[str], test_texts: Sequence[str]
    ) -> list[dict[str, float]]:
        assert not set(train_texts) & set(test_texts)
        return [{"a": 0.5, "b": 0.5} for _ in test_texts]

    out_of_fold_probabilities(texts, LABELS, fit_predict, folds=5)


def test_out_of_fold_rejects_empty_and_mismatched_input() -> None:
    with pytest.raises(ValueError, match="vazia"):
        out_of_fold_probabilities([], [], _constant_fit_predict)
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        out_of_fold_probabilities(["x"], ["a", "b"], _constant_fit_predict)


def test_out_of_fold_rejects_class_smaller_than_folds() -> None:
    with pytest.raises(ValueError, match="não cabe"):
        out_of_fold_probabilities(["a1", "a2", "b1"], ["a", "a", "b"], _constant_fit_predict, folds=2)


def test_clone_fit_predict_uses_the_template_without_changing_it(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    lines = [
        "id,text,label,split,urgent",
        "1,renovar a cnh vencida,driver_license,train,0",
        "2,segunda via do iptu,property_tax,train,0",
        "3,carteira de motorista nova,driver_license,train,0",
        "4,parcelar imposto do imovel,property_tax,train,0",
    ]
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    template = train(csv_path)
    texts = ["renovar a cnh vencida", "segunda via do iptu"]
    labels = ["driver_license", "property_tax"]
    predicted = clone_fit_predict(template)(texts, labels, ["renovar a cnh"])
    assert set(predicted[0]) == set(labels)
    assert predicted[0]["driver_license"] > predicted[0]["property_tax"]
    assert set(template.classes_) == set(labels)


def test_classifications_use_rule_only_when_exactly_one_matches() -> None:
    probabilities = [{"id_card": 0.2, "driver_license": 0.8}] * 3
    texts = ["preciso do rg", "pedido sem atalho", "rg e cnh no mesmo pedido"]
    found = classifications_from_probabilities(texts, probabilities)
    assert [(item.label, item.source) for item in found] == [
        ("id_card", SOURCE_RULE),
        ("driver_license", SOURCE_MODEL),
        ("driver_license", SOURCE_MODEL),
    ]


def test_classifications_reject_empty_and_mismatched_input() -> None:
    with pytest.raises(ValueError, match="vazia"):
        classifications_from_probabilities([], [])
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        classifications_from_probabilities(["x"], [])


def test_threshold_table_known_case() -> None:
    texts = [NEUTRAL_TEXT] * 4
    y_true = ["a", "a", "b", "b"]
    found = [_classification("a", 0.9), _classification("a", 0.5), _classification("a", 0.7), _classification("b", 0.55)]
    rows = threshold_table(texts, y_true, found, confidence_grid(NO_MARGIN, [0.40, 0.60, 0.80]))
    assert rows == [
        ThresholdRow(0.40, 0.0, 1.0, 0.75),
        ThresholdRow(0.60, 0.0, 0.5, 0.5),
        ThresholdRow(0.80, 0.0, 0.25, 1.0),
    ]


def test_threshold_table_margin_grid_and_inclusive_limits() -> None:
    texts = [NEUTRAL_TEXT]
    found = [_classification("a", 0.75)]
    rows = threshold_table(texts, ["a"], found, margin_grid(SETTINGS, [0.25, 0.50, 0.51]))
    assert [row.coverage for row in rows] == [1.0, 1.0, 0.0]
    assert rows[2].accuracy is None


def test_threshold_table_sends_other_and_urgent_to_review() -> None:
    other = Classification("other", {"other": 0.95, "a": 0.05}, SOURCE_MODEL)
    rows = threshold_table(
        [NEUTRAL_TEXT, "estou com dor no peito"], ["other", "a"], [other, _classification("a", 0.95)], [SETTINGS]
    )
    assert rows[0].coverage == 0.0


def test_threshold_table_rejects_empty_and_mismatched_input() -> None:
    with pytest.raises(ValueError, match="vazia"):
        threshold_table([], [], [], [SETTINGS])
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        threshold_table([NEUTRAL_TEXT], ["a", "b"], [_classification("a", 0.9)], [SETTINGS])
    with pytest.raises(ValueError, match="grade"):
        threshold_table([NEUTRAL_TEXT], ["a"], [_classification("a", 0.9)], [])


def test_mean_confidence_splits_hits_and_errors() -> None:
    texts = [NEUTRAL_TEXT] * 3
    found = [_classification("a", 0.9), _classification("a", 0.7), _classification("b", 0.6)]
    hits, errors = mean_confidence_by_outcome(texts, ["a", "b", "b"], found, SETTINGS)
    assert hits == pytest.approx(0.75)
    assert errors == pytest.approx(0.7)


def test_mean_confidence_is_none_without_hits_or_errors() -> None:
    texts = [NEUTRAL_TEXT]
    assert mean_confidence_by_outcome(texts, ["a"], [_classification("a", 0.9)], SETTINGS) == (pytest.approx(0.9), None)
    assert mean_confidence_by_outcome(texts, ["b"], [_classification("a", 0.9)], SETTINGS) == (None, pytest.approx(0.9))


def test_mean_confidence_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="vazia"):
        mean_confidence_by_outcome([], [], [], SETTINGS)
