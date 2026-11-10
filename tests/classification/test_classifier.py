"""Testes de `classify`: atalho por regra única, modelo e duas regras."""

from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

from triage.classification import Classification, ModelNotAvailableError, classify
from triage.classification import classifier as classifier_module
from triage.classification.model import predict_proba


def _assert_full_probabilities(result: Classification, labels: set[str]) -> None:
    assert set(result.probabilities) == labels
    assert sum(result.probabilities.values()) == pytest.approx(1.0)


def test_single_rule_decides_the_label(sample_model: Pipeline, sample_labels: set[str]) -> None:
    result = classify("onde tiro minha CNH?", sample_model)
    assert (result.label, result.source) == ("driver_license", "rule")
    _assert_full_probabilities(result, sample_labels)


def test_without_rule_the_model_decides(sample_model: Pipeline, sample_labels: set[str]) -> None:
    result = classify("previsão do tempo amanhã", sample_model)
    assert result.source == "model"
    assert result.label == max(result.probabilities, key=result.probabilities.__getitem__)
    _assert_full_probabilities(result, sample_labels)


def test_two_rules_fall_back_to_the_model(sample_model: Pipeline, sample_labels: set[str]) -> None:
    result = classify("preciso do CPF para tirar a CNH", sample_model)
    assert result.source == "model"
    _assert_full_probabilities(result, sample_labels)


def test_rule_source_keeps_model_probabilities(sample_model: Pipeline) -> None:
    result = classify("segunda via do IPTU", sample_model)
    assert result.source == "rule"
    assert result.label == "property_tax"
    assert result.probabilities == predict_proba(sample_model, "segunda via do IPTU")


def test_classify_is_reproducible(sample_model: Pipeline) -> None:
    assert classify("quero a certidão", sample_model) == classify("quero a certidão", sample_model)


def test_classify_loads_default_model_when_none_is_given(
    sample_model: Pipeline, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(classifier_module, "load", lambda path: sample_model)
    assert classify("onde tiro minha CNH?").label == "driver_license"


def test_missing_model_raises_model_not_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(classifier_module, "DEFAULT_MODEL_PATH", tmp_path / "missing.joblib")
    with pytest.raises(ModelNotAvailableError):
        classify("onde tiro minha CNH?")
