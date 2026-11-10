"""Testes de `is_urgent`: léxico real, palavra inteira, normalização e falha segura."""

from pathlib import Path

import pytest

from triage.classification import urgency
from triage.classification.urgency import is_urgent


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
