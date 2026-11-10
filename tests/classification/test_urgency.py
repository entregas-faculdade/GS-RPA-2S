"""Testes de `is_urgent`: léxico real, palavra inteira, normalização e falha segura."""

from pathlib import Path

import pandas as pd
import pytest

from triage.classification import urgency
from triage.classification.urgency import is_urgent

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "labeled" / "requests_labeled.csv"
# Pedidos urgent=1 que o léxico nunca cobriu (anteriores ao léxico de saúde): vão à revisão por outros gatilhos.
KNOWN_UNDETECTED_IDS = {"L031", "L052", "L125", "L131", "L150", "L178"}


@pytest.mark.parametrize(
    "text",
    [
        "Estou em risco de vida, preciso de ajuda",
        "Sofro VIOLÊNCIA doméstica em casa",
        "ele me ameaçou ontem",
        "quero me matar",
        "minha casa teve deslizamento",
    ],
)
def test_urgent_texts_are_detected(text: str) -> None:
    assert is_urgent(text) is True


@pytest.mark.parametrize("text", ["onde tiro minha CNH?", "segunda via do IPTU", "armário novo da prefeitura"])
def test_ordinary_texts_are_not_urgent(text: str) -> None:
    assert is_urgent(text) is False


def test_term_matches_whole_words_only(tmp_path: Path) -> None:
    lexicon = tmp_path / "terms.json"
    lexicon.write_text('["arma"]', encoding="utf-8")

    assert is_urgent("vi uma arma na rua", lexicon) is True
    assert is_urgent("o armazem fechou", lexicon) is False


def test_lexicon_accents_are_folded(tmp_path: Path) -> None:
    lexicon = tmp_path / "terms.json"
    lexicon.write_text('["emergência"]', encoding="utf-8")

    assert is_urgent("é uma EMERGENCIA", lexicon) is True


def test_missing_lexicon_is_urgent_and_logs_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("ERROR", logger="triage.classification"):
        assert is_urgent("onde tiro minha CNH?", tmp_path / "missing.json") is True

    assert "Léxico de urgência" in caplog.text


@pytest.mark.parametrize("content", ["{not json", '{"a": 1}', "[]", '[1, ""]'])
def test_invalid_lexicon_is_urgent(tmp_path: Path, content: str) -> None:
    lexicon = tmp_path / "terms.json"
    lexicon.write_text(content, encoding="utf-8")

    assert is_urgent("onde tiro minha CNH?", lexicon) is True


def test_lexicon_is_loaded_once(tmp_path: Path) -> None:
    lexicon = tmp_path / "terms.json"
    lexicon.write_text('["socorro"]', encoding="utf-8")
    urgency._load_pattern.cache_clear()

    is_urgent("socorro", lexicon)
    is_urgent("outro texto", lexicon)

    assert urgency._load_pattern.cache_info().hits == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("dores no peito e falta de ar", True),
        ("meu pai teve um desmaio e precisa de ambulância", True),
        ("preciso de ajuda urgente", True),
        ("Quero renovar a CNH, é urgente", False),
        ("Quero abrir uma reclamação. Urgente obrigado.", False),
        ("preciso do IPTU com urgência de entrega", False),
        ("como tirar a segunda via do RG", False),
    ],
)
def test_health_emergency_is_urgent_and_courtesy_urgente_is_not(text: str, expected: bool) -> None:
    assert is_urgent(text) is expected


def test_labeled_dataset_urgent_column_matches_lexicon() -> None:
    dataset = pd.read_csv(DATASET_PATH, encoding="utf-8")

    mismatched = {row.id for row in dataset.itertuples() if is_urgent(row.text) != bool(row.urgent)}

    assert mismatched == KNOWN_UNDETECTED_IDS
