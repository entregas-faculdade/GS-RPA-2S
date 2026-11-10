"""Métricas do localizador com amostras de resultado conhecido, e a integridade do conjunto rotulado."""

import csv
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest

from triage.automation.catalog import ServiceEntry, approved_only, load_catalog
from triage.automation.finder import FinderMatch
from triage.classification.preprocessing import fold
from triage.evaluation.finder_metrics import (
    NO_SOURCE,
    FinderScores,
    answered_accuracy,
    coverage,
    false_positive_rate,
    predictions_at,
    score_finder,
    threshold_table,
)

FINDER_CSV = Path("data") / "labeled" / "finder_requests.csv"
CLASSIFICATION_CSV = Path("data") / "labeled" / "requests_labeled.csv"

EXPECTED = ["a", "b", NO_SOURCE, NO_SOURCE, "c", NO_SOURCE]
PREDICTED = ["a", "x", None, "a", None, None]


def test_coverage_counts_the_requests_that_got_a_source() -> None:
    assert coverage(PREDICTED) == pytest.approx(3 / 6)
    assert coverage([None, None]) == 0.0
    assert coverage(["a", "b"]) == 1.0


def test_answered_accuracy_counts_hits_among_the_answered() -> None:
    # respondidos: a (certo), x (errado), a para `none` (errado)
    assert answered_accuracy(EXPECTED, PREDICTED) == pytest.approx(1 / 3)


def test_answered_accuracy_is_none_when_nothing_was_answered() -> None:
    assert answered_accuracy(["a", NO_SOURCE], [None, None]) is None


def test_false_positive_rate_counts_sources_given_to_none_requests() -> None:
    # três pedidos `none`; um deles recebeu fonte
    assert false_positive_rate(EXPECTED, PREDICTED) == pytest.approx(1 / 3)


def test_false_positive_rate_perfect_and_total() -> None:
    assert false_positive_rate([NO_SOURCE, NO_SOURCE], [None, None]) == 0.0
    assert false_positive_rate([NO_SOURCE, NO_SOURCE], ["a", "b"]) == 1.0


def test_false_positive_rate_is_none_without_none_requests() -> None:
    assert false_positive_rate(["a", "b"], ["a", None]) is None


def test_score_finder_bundles_the_three_metrics_and_the_size() -> None:
    assert score_finder(EXPECTED, PREDICTED) == FinderScores(
        size=6,
        coverage=pytest.approx(0.5),
        answered_accuracy=pytest.approx(1 / 3),
        false_positive_rate=pytest.approx(1 / 3),
    )


@pytest.mark.parametrize(
    "call",
    [
        lambda: coverage([]),
        lambda: answered_accuracy([], []),
        lambda: false_positive_rate([], []),
        lambda: score_finder([], []),
        lambda: threshold_table([], [], [0.1], [0.1]),
    ],
)
def test_empty_sample_raises(call: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="vazia"):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: answered_accuracy(["a"], ["a", "b"]),
        lambda: false_positive_rate(["a", "b"], ["a"]),
        lambda: score_finder(["a"], []),
        lambda: threshold_table(["a"], [None, None], [0.1], [0.1]),
    ],
)
def test_different_sizes_raise(call: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        call()


def _entry(entry_id: str) -> ServiceEntry:
    return ServiceEntry(
        id=entry_id,
        category=None,
        kind="portal",
        scope="federal",
        coverage="Brasil",
        area="tax",
        display_name=entry_id,
        agency="Órgão",
        instructions="Orientação.",
        keywords=(entry_id,),
        links=(),
        phones=(),
        source_note="fonte",
        verified_on="2026-11-09",
        status="approved",
    )


@pytest.fixture
def matches() -> list[FinderMatch | None]:
    return [
        FinderMatch(_entry("a"), score=0.60, margin=0.40),
        FinderMatch(_entry("b"), score=0.30, margin=0.05),
        FinderMatch(_entry("c"), score=0.10, margin=0.10),
        None,
    ]


def test_predictions_apply_both_thresholds(matches: list[FinderMatch | None]) -> None:
    assert predictions_at(matches, 0.0, 0.0) == ["a", "b", "c", None]
    assert predictions_at(matches, 0.20, 0.0) == ["a", "b", None, None]
    assert predictions_at(matches, 0.0, 0.10) == ["a", None, "c", None]
    assert predictions_at(matches, 0.30, 0.05) == ["a", "b", None, None]


def test_threshold_table_has_one_row_per_pair_in_order(matches: list[FinderMatch | None]) -> None:
    expected = ["a", "b", NO_SOURCE, NO_SOURCE]

    rows = threshold_table(expected, matches, [0.0, 0.5], [0.0, 0.1])

    assert [(row.min_score, row.margin) for row in rows] == [(0.0, 0.0), (0.0, 0.1), (0.5, 0.0), (0.5, 0.1)]
    loose, _, strict, _ = rows
    assert loose.scores.coverage == pytest.approx(3 / 4)
    assert loose.scores.false_positive_rate == pytest.approx(1 / 2)
    assert strict.scores.coverage == pytest.approx(1 / 4)
    assert strict.scores.false_positive_rate == 0.0


def _rows() -> list[dict[str, str]]:
    with FINDER_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _approved() -> dict[str, ServiceEntry]:
    return {entry.id: entry for entry in approved_only(load_catalog())}


def test_labeled_set_has_the_columns_and_unique_ids() -> None:
    rows = _rows()

    assert list(rows[0]) == ["id", "text", "expected_id", "split"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))


def test_labeled_set_meets_the_minimums() -> None:
    rows = _rows()
    approved = _approved()
    real = [row for row in rows if row["expected_id"] != NO_SOURCE]
    covered_areas = {approved[row["expected_id"]].area for row in real}

    assert len(rows) >= 60
    assert len(real) >= 36
    assert len({row["expected_id"] for row in real}) >= 12
    assert {"health", "education", "vehicles", "city"} <= covered_areas
    assert len(rows) - len(real) >= 16


def test_expected_ids_are_approved_entries_or_none() -> None:
    approved = _approved()

    for row in _rows():
        assert row["expected_id"] == NO_SOURCE or row["expected_id"] in approved, row["id"]


def test_split_is_train_or_test_with_both_kinds_of_request_in_each() -> None:
    rows = _rows()
    by_split = Counter((row["split"], row["expected_id"] == NO_SOURCE) for row in rows)

    assert {row["split"] for row in rows} == {"train", "test"}
    assert all(by_split[(split, is_none)] >= 8 for split in ("train", "test") for is_none in (True, False))


def test_no_text_repeats_the_classification_set_or_is_a_bare_keyword() -> None:
    with CLASSIFICATION_CSV.open(encoding="utf-8", newline="") as handle:
        classification = {fold(row["text"]).strip() for row in csv.DictReader(handle)}
    keywords = {fold(keyword).strip() for entry in _approved().values() for keyword in entry.keywords}

    for row in _rows():
        text = fold(row["text"]).strip()
        assert text not in classification, row["id"]
        assert text not in keywords, row["id"]
