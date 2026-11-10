"""Contagens e higiene do conjunto rotulado sintético versionado."""

import hashlib
from pathlib import Path

import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from triage.classification.preprocessing import normalize
from triage.classification.rules import CATEGORY_RULES
from triage.classification.urgency import is_urgent
from triage.privacy import anonymize

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "labeled" / "requests_labeled.csv"
OTHER_LABEL = "other"
ORIGINAL_ROWS = 180
ORIGINAL_DIGEST = "57e0a6e129278d6574b3e29465e94c16e6d498766472e3ab6e4edafef79cfd13"
MIN_ROWS = 414
MIN_TRAIN_PER_CATEGORY = 40
TEST_PER_CATEGORY = 6
MIN_URGENT = 20
MAX_TRAIN_TEST_SIMILARITY = 0.85


@pytest.fixture(scope="module")
def dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH, encoding="utf-8")


def test_columns_and_size(dataset: pd.DataFrame) -> None:
    assert list(dataset.columns) == ["id", "text", "label", "split", "urgent"]
    assert len(dataset) >= MIN_ROWS
    assert dataset["id"].is_unique


def test_labels_are_the_nine_classes_with_minimum_train_counts(dataset: pd.DataFrame) -> None:
    assert set(dataset["label"]) == set(CATEGORY_RULES) | {OTHER_LABEL}
    train_counts = dataset[dataset["split"] == "train"]["label"].value_counts()
    assert all(count >= MIN_TRAIN_PER_CATEGORY for count in train_counts), train_counts.to_dict()


def test_urgent_flag_is_binary_with_minimum_count(dataset: pd.DataFrame) -> None:
    assert set(dataset["urgent"].unique()) <= {0, 1}
    assert dataset["urgent"].sum() >= MIN_URGENT


def test_split_is_filled_and_test_set_keeps_six_per_category(dataset: pd.DataFrame) -> None:
    assert set(dataset["split"].unique()) == {"train", "test"}
    test_counts = dataset[dataset["split"] == "test"]["label"].value_counts()
    assert set(test_counts) == {TEST_PER_CATEGORY}
    assert len(test_counts) == len(CATEGORY_RULES) + 1


def test_original_rows_are_untouched(dataset: pd.DataFrame) -> None:
    original = dataset.head(ORIGINAL_ROWS)
    assert original["id"].tolist() == [f"L{number:03d}" for number in range(1, ORIGINAL_ROWS + 1)]
    serialized = "\n".join("|".join(str(value) for value in row) for row in original.itertuples(index=False))
    assert hashlib.sha256(serialized.encode("utf-8")).hexdigest() == ORIGINAL_DIGEST
    assert (dataset.iloc[ORIGINAL_ROWS:]["split"] == "train").all()


def test_new_rows_urgent_flag_matches_the_lexicon(dataset: pd.DataFrame) -> None:
    new_rows = dataset.iloc[ORIGINAL_ROWS:]
    mismatches = [row.id for row in new_rows.itertuples() if int(is_urgent(row.text)) != row.urgent]
    assert mismatches == []


def test_train_and_test_do_not_overlap(dataset: pd.DataFrame) -> None:
    train = dataset[dataset["split"] == "train"]
    test = dataset[dataset["split"] == "test"]
    assert not set(train["id"]) & set(test["id"])
    assert not set(train["text"].str.lower().str.strip()) & set(test["text"].str.lower().str.strip())
    assert dataset["text"].str.lower().str.strip().is_unique


def test_no_train_row_is_a_near_duplicate_of_a_test_row(dataset: pd.DataFrame) -> None:
    train = dataset[dataset["split"] == "train"]
    test = dataset[dataset["split"] == "test"]
    vectorizer = TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2), sublinear_tf=True).fit(dataset["text"])
    similarity = cosine_similarity(vectorizer.transform(train["text"]), vectorizer.transform(test["text"]))
    assert similarity.max() < MAX_TRAIN_TEST_SIMILARITY


def test_no_real_personal_data(dataset: pd.DataFrame) -> None:
    assert all(sum(anonymize(text).counts.values()) == 0 for text in dataset["text"])
