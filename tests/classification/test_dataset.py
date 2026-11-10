"""Contagens e higiene do conjunto rotulado sintético versionado."""

from pathlib import Path

import pandas as pd
import pytest

from triage.classification.rules import CATEGORY_RULES
from triage.privacy import anonymize

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "labeled" / "requests_labeled.csv"
OTHER_LABEL = "other"
MIN_ROWS = 160
MIN_PER_CATEGORY = 15
MIN_OTHER = 20
MIN_URGENT = 10
TRAIN_SHARE = 0.70
SHARE_TOLERANCE = 0.02


@pytest.fixture(scope="module")
def dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, encoding="utf-8")


def test_columns_and_size(dataset: pd.DataFrame) -> None:
    assert list(dataset.columns) == ["id", "text", "label", "split", "urgent"]
    assert len(dataset) >= MIN_ROWS
    assert dataset["id"].is_unique


def test_labels_are_the_nine_classes_with_minimum_counts(dataset: pd.DataFrame) -> None:
    counts = dataset["label"].value_counts()
    assert set(counts.index) == set(CATEGORY_RULES) | {OTHER_LABEL}
    assert all(counts[label] >= MIN_PER_CATEGORY for label in CATEGORY_RULES)
    assert counts[OTHER_LABEL] >= MIN_OTHER


def test_urgent_flag_is_binary_with_minimum_count(dataset: pd.DataFrame) -> None:
    assert set(dataset["urgent"].unique()) <= {0, 1}
    assert dataset["urgent"].sum() >= MIN_URGENT


def test_split_is_filled_and_stratified_70_30(dataset: pd.DataFrame) -> None:
    assert set(dataset["split"].unique()) == {"train", "test"}
    for label, rows in dataset.groupby("label"):
        train_share = (rows["split"] == "train").mean()
        assert train_share == pytest.approx(TRAIN_SHARE, abs=SHARE_TOLERANCE), label


def test_no_real_personal_data(dataset: pd.DataFrame) -> None:
    assert all(sum(anonymize(text).counts.values()) == 0 for text in dataset["text"])
