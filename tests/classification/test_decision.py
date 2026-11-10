"""Testes de `triage_decision`: um caso por motivo, precedência, bordas e limiares configuráveis."""

from pathlib import Path

import pytest

from triage.classification import Classification, Decision, ReviewReason, triage_decision
from triage.classification import urgency
from triage.config import Settings, load_settings

SETTINGS = Settings(
    llm_enabled=False,
    llm_base_url="",
    llm_model="",
    llm_api_key="",
    log_level="INFO",
    output_dir="output",
    confidence_min=0.60,
    ambiguity_margin=0.25,
)
CALM_TEXT = "onde tiro minha CNH?"


def _classification(label: str, top: float, second: float, source: str = "model") -> Classification:
    probabilities = {"driver_license": 0.0, "property_tax": 0.0, "other": 0.0}
    probabilities[label] = top
    runner_up = next(name for name in ("property_tax", "other") if name != label)
    probabilities[runner_up] = second
    return Classification(label, probabilities, source)


def _decide(text: str, classification: Classification) -> Decision:
    return triage_decision(text, classification, SETTINGS)


def test_confident_clear_request_is_answered_automatically() -> None:
    decision = _decide(CALM_TEXT, _classification("driver_license", 0.90, 0.05))

    assert (decision.action, decision.reason) == ("auto_answer", None)
    assert decision.category == "driver_license"
    assert decision.confidence == pytest.approx(0.90)


@pytest.mark.parametrize(
    ("text", "classification", "expected"),
    [
        ("socorro, sofro violência", _classification("driver_license", 0.95, 0.02), ReviewReason.URGENT),
        (CALM_TEXT, _classification("other", 0.95, 0.02), ReviewReason.OUT_OF_CATALOG),
        (CALM_TEXT, _classification("driver_license", 0.40, 0.10), ReviewReason.LOW_CONFIDENCE),
        (CALM_TEXT, _classification("driver_license", 0.70, 0.60), ReviewReason.AMBIGUOUS),
    ],
)
def test_each_trigger_sends_the_request_to_human_review(
    text: str, classification: Classification, expected: ReviewReason
) -> None:
    decision = _decide(text, classification)

    assert decision.action == "human_review"
    assert decision.reason is expected


def test_urgent_text_goes_to_review_even_with_full_confidence() -> None:
    decision = _decide("estou em risco de vida", _classification("driver_license", 1.0, 0.0))

    assert decision.reason is ReviewReason.URGENT
    assert decision.confidence == 1.0


def test_precedence_urgent_over_out_of_catalog_over_low_confidence_over_ambiguous() -> None:
    weak_other = _classification("other", 0.30, 0.29)
    weak_service = _classification("driver_license", 0.30, 0.29)
    ambiguous_service = _classification("driver_license", 0.65, 0.60)

    assert _decide("risco de vida", weak_other).reason is ReviewReason.URGENT
    assert _decide(CALM_TEXT, weak_other).reason is ReviewReason.OUT_OF_CATALOG
    assert _decide(CALM_TEXT, weak_service).reason is ReviewReason.LOW_CONFIDENCE
    assert _decide(CALM_TEXT, ambiguous_service).reason is ReviewReason.AMBIGUOUS


def test_rule_with_timid_model_is_answered_automatically() -> None:
    timid = _classification("driver_license", 0.30, 0.29, source="rule")

    decision = _decide(CALM_TEXT, timid)

    assert (decision.action, decision.reason) == ("auto_answer", None)
    assert decision.confidence == pytest.approx(0.90)


def test_rule_floor_does_not_lower_a_higher_model_probability() -> None:
    assert _decide(CALM_TEXT, _classification("driver_license", 0.97, 0.01, "rule")).confidence == 0.97


def test_confidence_exactly_at_the_minimum_is_accepted() -> None:
    assert _decide(CALM_TEXT, _classification("driver_license", 0.60, 0.0)).reason is None
    assert _decide(CALM_TEXT, _classification("driver_license", 0.59, 0.0)).reason is ReviewReason.LOW_CONFIDENCE


def test_margin_exactly_at_the_minimum_is_accepted() -> None:
    assert _decide(CALM_TEXT, _classification("driver_license", 0.75, 0.50)).reason is None
    assert _decide(CALM_TEXT, _classification("driver_license", 0.75, 0.51)).reason is ReviewReason.AMBIGUOUS


def test_missing_lexicon_sends_to_review(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    urgency._load_pattern.cache_clear()
    monkeypatch.chdir(tmp_path)

    decision = _decide(CALM_TEXT, _classification("driver_license", 0.95, 0.01))

    urgency._load_pattern.cache_clear()
    assert (decision.action, decision.reason) == ("human_review", ReviewReason.URGENT)


def test_review_reason_values_are_the_closed_set() -> None:
    assert {reason.value for reason in ReviewReason} == {
        "low_confidence",
        "ambiguous",
        "urgent",
        "out_of_catalog",
        "invalid_input",
        "link_unavailable",
    }


def test_thresholds_default_and_environment_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("CONFIDENCE_MIN", raising=False)
    monkeypatch.delenv("AMBIGUITY_MARGIN", raising=False)
    defaults = load_settings(tmp_path / "missing.env")
    assert (defaults.confidence_min, defaults.ambiguity_margin) == (0.60, 0.15)

    monkeypatch.setenv("CONFIDENCE_MIN", "0.8")
    monkeypatch.setenv("AMBIGUITY_MARGIN", "abc")
    overridden = load_settings(tmp_path / "missing.env")
    assert (overridden.confidence_min, overridden.ambiguity_margin) == (0.8, 0.15)
