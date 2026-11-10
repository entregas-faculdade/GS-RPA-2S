"""Testes da anonimização de CPF, telefone e e-mail (dados sintéticos)."""

import pytest

from triage.privacy import anonymize
from triage.privacy.validators import is_valid_cpf

# CPF gerado por algoritmo (sintético).
VALID_CPF = "52998224725"
PUNCTUATED_CPF = "529.982.247-25"


def _counts(cpf: int = 0, phone: int = 0, email: int = 0) -> dict[str, int]:
    extra_keys = ("name", "address", "postal_code", "rg", "date", "document")
    return {"cpf": cpf, "phone": phone, "email": email, **dict.fromkeys(extra_keys, 0)}


@pytest.mark.parametrize(
    ("raw", "marker", "counts"),
    [
        (f"cpf {PUNCTUATED_CPF} ok", "[CPF]", _counts(cpf=1)),
        (f"cpf {VALID_CPF} ok", "[CPF]", _counts(cpf=1)),
        ("tel (11) 91234-5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel 11912345678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel +55 11 91234-5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel 3234-5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel (11) 91234 5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel (11) 3234 5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel +55 11 91234 5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("tel +55 (11) 3234-5678 ok", "[TELEFONE]", _counts(phone=1)),
        ("cpf 529982247-25 ok", "[CPF]", _counts(cpf=1)),
        ("cpf 529.982.24725 ok", "[CPF]", _counts(cpf=1)),
        ("cpf 529.98224725 ok", "[CPF]", _counts(cpf=1)),
        ("mail usuario@exemplo.com ok", "[EMAIL]", _counts(email=1)),
    ],
)
def test_positive_cases_are_replaced(raw: str, marker: str, counts: dict[str, int]) -> None:
    result = anonymize(raw)
    assert marker in result.text
    assert result.counts == counts


def test_several_pii_in_same_text() -> None:
    result = anonymize(f"meu cpf {PUNCTUATED_CPF} tel (11) 91234-5678 a@exemplo.com")
    assert result.text == "meu cpf [CPF] tel [TELEFONE] [EMAIL]"
    assert result.counts == _counts(cpf=1, phone=1, email=1)


@pytest.mark.parametrize(
    "raw",
    [
        "protocolo 12345678901 aberto",
        "protocolo 11111111111 aberto",
        "protocolo 529982247-26 aberto",
        "protocolo 529.982.24726 aberto",
        "protocolo 529.98224726 aberto",
        "ano 2024 1234 e senha 1234 5678",
        "em 2024 paguei R$ 1.234,56 de taxa",
        "valor de R$ 150,00 em 03/2025",
        "preciso renovar a identidade",
    ],
)
def test_negative_cases_stay_unchanged(raw: str) -> None:
    result = anonymize(raw)
    assert result.text == raw
    assert result.counts == _counts()


def test_idempotent() -> None:
    once = anonymize(f"cpf {PUNCTUATED_CPF} {VALID_CPF} (11) 91234-5678 a@exemplo.com 12345678901 529982247-25 529.98224725 (11) 91234 5678 +55 11 91234 5678")
    twice = anonymize(once.text)
    assert twice.text == once.text
    assert twice.counts == _counts()


def test_cpf_validator() -> None:
    assert is_valid_cpf(VALID_CPF)
    assert is_valid_cpf(PUNCTUATED_CPF)
    assert not is_valid_cpf("12345678901")
    assert not is_valid_cpf("11111111111")
    assert not is_valid_cpf("123")
