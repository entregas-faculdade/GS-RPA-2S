"""Testes da normalização de texto."""

import pytest

from triage.classification.preprocessing import PT_BR_STOPWORDS, fold, normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("RENOVAÇÃO da CNH", "renovacao cnh"),
        ("Título de eleitor, 2ª via!", "titulo eleitor 2a via"),
        ("   muitos    espaços\te\nquebras  ", "muitos espacos quebras"),
        ("como faço o iptu?", "faco iptu"),
        ("", ""),
        ("de da do", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_normalize_is_deterministic_and_idempotent() -> None:
    raw = "Preciso renovar a CNH, é urgente!"
    assert normalize(raw) == normalize(raw)
    assert normalize(normalize(raw)) == normalize(raw)


def test_normalize_drops_anonymization_markers() -> None:
    assert normalize("meu cpf [CPF] e tel [TELEFONE] e [EMAIL]") == "cpf tel"


def test_fold_keeps_punctuation_but_drops_accents_and_markers() -> None:
    assert fold("Cadúnico [CPF]?") == "cadunico  ?"


def test_stopwords_are_unaccented_lowercase() -> None:
    assert all(word == fold(word) for word in PT_BR_STOPWORDS)
