"""Testes de treino, persistência e probabilidades do modelo."""

from collections.abc import Callable
from pathlib import Path

import joblib
import pytest
from sklearn.pipeline import Pipeline

from triage.classification.model import (
    ModelNotAvailableError,
    load,
    predict_proba,
    save,
    train,
)


def test_train_and_predict_on_small_sample(sample_model: Pipeline, sample_labels: set[str]) -> None:
    probabilities = predict_proba(sample_model, "quero tirar o rg")
    assert set(probabilities) == sample_labels
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert max(probabilities, key=probabilities.__getitem__) == "id_card"


def test_train_uses_only_train_split(tmp_path: Path, write_sample_csv: Callable[..., Path]) -> None:
    csv_path = write_sample_csv(tmp_path / "sample.csv", ("T001,texto so de teste,test_only_label,test,0",))
    assert "test_only_label" not in train(csv_path).classes_


def test_train_is_reproducible(tmp_path: Path, write_sample_csv: Callable[..., Path]) -> None:
    csv_path = write_sample_csv(tmp_path / "sample.csv")
    first = predict_proba(train(csv_path), "preciso do titulo")
    second = predict_proba(train(csv_path), "preciso do titulo")
    assert first == second


def test_train_rejects_csv_without_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("id,text\n1,oi\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colunas"):
        train(csv_path)


def test_train_rejects_csv_without_train_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "only_test.csv"
    csv_path.write_text("id,text,label,split,urgent\nT001,oi,other,test,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="train"):
        train(csv_path)


def test_save_and_load_roundtrip(sample_model: Pipeline, tmp_path: Path) -> None:
    path = tmp_path / "nested" / "classifier.joblib"
    save(sample_model, path)
    assert predict_proba(load(path), "zona eleitoral") == predict_proba(sample_model, "zona eleitoral")


def test_load_missing_file_raises_model_not_available(tmp_path: Path) -> None:
    with pytest.raises(ModelNotAvailableError):
        load(tmp_path / "missing.joblib")


def test_load_corrupted_file_raises_model_not_available(tmp_path: Path) -> None:
    path = tmp_path / "corrupted.joblib"
    path.write_bytes(b"isto nao e um modelo")
    with pytest.raises(ModelNotAvailableError):
        load(path)


def test_load_object_without_predict_proba_raises_model_not_available(tmp_path: Path) -> None:
    path = tmp_path / "wrong.joblib"
    joblib.dump({"not": "a model"}, path)
    with pytest.raises(ModelNotAvailableError, match="predict_proba"):
        load(path)
