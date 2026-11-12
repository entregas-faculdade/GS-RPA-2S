"""Testes da anonimização de nome, endereço, CEP, RG, data e documentos (pessoas e dados fictícios)."""

import csv
import logging
from pathlib import Path

import pytest

from triage.privacy import anonymize, names
from triage.privacy.anonymizer import COUNT_KEYS

LABELED_CSV = Path(__file__).resolve().parents[2] / "data" / "labeled" / "requests_labeled.csv"
MIN_FIRST_NAMES = 300


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Meu nome é Jose carlos de andrade", "Meu nome é [NOME]"),
        ("Me chamo Ana, moro na Av. Paulista 1000 apto 52", "Me chamo [NOME], moro na [ENDERECO]"),
        ("Sou Maria da Silva Souza e preciso da segunda via do RG", "Sou [NOME] e preciso da segunda via do RG"),
        ("RG 12.345.678-9", "RG [RG]"),
        ("nascido em 12/03/1985", "nascido em [DATA]"),
        ("CEP 01310-100", "CEP [CEP]"),
        ("título de eleitor 1234 5678 9012", "título de eleitor [DOCUMENTO]"),
        ("Rua das Flores, 123", "[ENDERECO]"),
        ("joão pereira precisa renovar a cnh", "[NOME] precisa renovar a cnh"),
    ],
)
def test_required_cases(raw: str, expected: str) -> None:
    assert anonymize(raw).text == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Quero saber sobre o Bolsa Família e o Cadastro Único",
        "Preciso da Receita Federal e da Justiça Eleitoral",
        "Moro em São Paulo, na região do Ipiranga",
        "Meu protocolo é 2024/0001 e a taxa é de R$ 120,50",
        "Quero renovar minha CNH",
        "Preciso do RG",
        "Sou aposentado e quero saber do INSS",
        "Há um buraco na rua em frente à escola",
        "dia 12/03",
        "o buraco na rua da minha casa piorou",
        "BURACO NA RUA EM FRENTE AO MERCADO",
        "Moro em Santa Maria, perto de João Pessoa",
        "passaporte vencido e cnpj da empresa",
        "matrícula 2024/0001 e valor de 03/2025",
        "rua em frente à escola",
        "a rua da minha casa",
        "A Rua está sem iluminação",
        "A rua está sem iluminação há 3 dias",
        "moro nesta rua há 10 anos",
        "a rua ficou alagada 2 vezes esta semana",
        "Na rua da escola passam 20 ônibus por dia",
        "o buraco na rua de casa tem 2 metros",
        "avenida lotada 3 horas",
        "quero reclamar da rua que está esburacada há 15 dias",
        "rua sem asfalto desde 2020",
        "Preciso de 2 vias da certidão na rua",
    ],
)
def test_negative_cases_stay_unchanged(raw: str) -> None:
    result = anonymize(raw)
    assert result.text == raw
    assert not any(result.counts.values())


# (texto fictício, saída esperada) — nomes e endereços inventados.
FICTITIOUS_CASES = [
    ("meu nome é carlos eduardo pereira", "meu nome é [NOME]"),
    ("MEU NOME É FERNANDA LIMA", "MEU NOME É [NOME]"),
    ("meu nome completo é Rita de Cássia Alves, preciso do iptu", "meu nome completo é [NOME], preciso do iptu"),
    ("meu nome e joana dark", "meu nome e [NOME]"),
    ("me chamo Pedro Henrique e quero a cnh", "me chamo [NOME] e quero a cnh"),
    ("chamo-me Luiza Helena dos Santos", "chamo-me [NOME]"),
    ("Nome: Gustavo Ramos", "Nome: [NOME]"),
    ("nome completo: bruna souza lima, cpf pendente", "nome completo: [NOME], cpf pendente"),
    ("nome do pai: Raimundo Nonato", "nome do pai: [NOME]"),
    ("Sr. Antônio Barbosa pede a segunda via", "Sr. [NOME] pede a segunda via"),
    ("A Dra. Helena Duarte solicitou o documento", "A Dra. [NOME] solicitou o documento"),
    ("falei com o senhor Marcos Vieira ontem", "falei com o senhor [NOME] ontem"),
    ("preciso da certidão de Beatriz Moraes", "preciso da certidão de [NOME]"),
    ("quem consegue ajudar o Rodrigo com o iptu?", "quem consegue ajudar o [NOME] com o iptu?"),
    ("camila precisa renovar a cnh", "[NOME] precisa renovar a cnh"),
    ("Ana", "[NOME]"),
    ("Juliana Costa Ribeiro Gomes de Lima Neves quer o inss", "[NOME] quer o inss"),
    ("minha filha Larissa nasceu em 03/05/2020", "minha filha [NOME] nasceu em [DATA]"),
    ("Moro na rua das Acácias 45 bloco B", "Moro na [ENDERECO]"),
    ("moro na avenida Brasil, 300", "moro na [ENDERECO]"),
    ("MORO NA RUA DAS PALMEIRAS 12", "MORO NA [ENDERECO]"),
    ("alameda Santos 20 apartamento 7", "[ENDERECO]"),
    ("Travessa do Comércio, s/n", "[ENDERECO]"),
    ("Praça da Sé 100", "[ENDERECO]"),
    ("Rodovia dos Bandeirantes km", "[ENDERECO] km"),
    ("Estrada Velha de Campinas, 1500 casa 3", "[ENDERECO]"),
    ("Largo São Francisco 9", "[ENDERECO]"),
    ("R. Sete de Setembro 50", "[ENDERECO]"),
    ("rua Quinze de Novembro, no 88, apto 12", "[ENDERECO]"),
    ("CEP: 01310100 e RG nº 12345678X", "CEP: [CEP] e RG nº [RG]"),
    ("rg 1234567", "rg [RG]"),
    ("o rg é 5.432.109-X", "o rg é [RG]"),
    ("sou o 9.876.543-2 na lista", "sou o [RG] na lista"),
    ("cnpj 12.345.678/0001-95", "cnpj [DOCUMENTO]"),
    ("CNH 12345678901", "CNH [DOCUMENTO]"),
    ("cartão SUS: 123 4567 8901 2345", "cartão SUS: [DOCUMENTO]"),
    ("nis 123.45678.90-1", "nis [DOCUMENTO]"),
    ("passaporte AB e 123456789", "passaporte AB e 123456789"),
    ("nasci em 12-03-1985 e 01.02.2000", "nasci em [DATA] e [DATA]"),
    ("data 1985-03-12", "data [DATA]"),
]


FICTITIOUS_CASES += [
    ("moro na rua augusta 500", "moro na [ENDERECO]"),
    ("av paulista 1000 apto 52", "[ENDERECO]"),
    ("moro na praca sao joao 12", "moro na [ENDERECO]"),
    ("rua sao joao, 45", "[ENDERECO]"),
    ("Rua augusta 500", "[ENDERECO]"),
    ("moro na rua 7 de setembro, 12", "moro na [ENDERECO]"),
    ("mudei para a rua tres 45 centro", "mudei para a [ENDERECO] centro"),
    ("rua dos pinheiros n 200", "[ENDERECO]"),
]


@pytest.mark.parametrize(("raw", "expected"), FICTITIOUS_CASES)
def test_fictitious_cases(raw: str, expected: str) -> None:
    assert anonymize(raw).text == expected


def test_fictitious_cases_are_enough() -> None:
    assert len(FICTITIOUS_CASES) >= 20


def test_counts_have_all_nine_keys() -> None:
    result = anonymize("nome: Ana Souza, Rua Alfa Beta 1, CEP 01310-100, RG 12.345.678-9, 12/03/1985, CNH 12345678901")
    assert set(result.counts) == set(COUNT_KEYS)
    assert len(result.counts) == 9
    assert result.counts == {
        "cpf": 0,
        "phone": 0,
        "email": 0,
        "name": 1,
        "address": 1,
        "postal_code": 1,
        "rg": 1,
        "date": 1,
        "document": 1,
    }


def test_new_types_do_not_eat_each_others_digits_nor_the_phone() -> None:
    result = anonymize("tel (11) 91234-5678, CEP 01310-100, Rua das Flores 123, RG 12.345.678-9")
    assert result.text == "tel [TELEFONE], CEP [CEP], [ENDERECO], RG [RG]"
    assert result.counts["phone"] == 1


@pytest.mark.parametrize(("raw", "_expected"), FICTITIOUS_CASES)
def test_idempotent_for_new_types(raw: str, _expected: str) -> None:
    once = anonymize(raw)
    twice = anonymize(once.text)
    assert twice.text == once.text
    assert not any(twice.counts.values())


def test_anonymize_is_pure() -> None:
    raw = "Meu nome é Jose carlos de andrade, Rua das Flores 1"
    assert anonymize(raw) == anonymize(raw)


def test_first_names_list_is_large_enough_and_has_only_first_names() -> None:
    loaded = names.load_first_names(names.FIRST_NAMES_PATH)
    assert len(loaded) >= MIN_FIRST_NAMES
    assert all(" " not in name and name == name.lower() for name in loaded)


@pytest.mark.parametrize("content", [None, "não é json", '{"a": 1}', "[1, 2]"])
def test_missing_or_invalid_first_names_fail_safe(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, content: str | None
) -> None:
    path = tmp_path / "first_names.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with caplog.at_level(logging.ERROR, logger=names.logger.name):
        assert names.load_first_names(path) == frozenset()
    assert str(path) in caplog.text


def test_context_masks_names_even_without_the_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(names, "_first_names", lambda: frozenset())
    assert anonymize("Meu nome é Jose carlos de andrade").text == "Meu nome é [NOME]"
    assert anonymize("joão pereira precisa renovar a cnh").text == "joão pereira precisa renovar a cnh"


def test_labeled_csv_is_unchanged() -> None:
    with LABELED_CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 418
    assert [row["id"] for row in rows if anonymize(row["text"]).text != row["text"]] == []
