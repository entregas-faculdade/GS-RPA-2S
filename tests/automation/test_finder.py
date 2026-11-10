"""Localizador de fontes: só entradas aprovadas, pontuação e folga, limiares e determinismo (catálogo fake, sem rede)."""

import dataclasses
from collections.abc import Callable

import pytest

from triage.automation.catalog import ServiceEntry
from triage.automation.finder import FinderMatch, ServiceFinder
from triage.config import Settings

SETTINGS = Settings(
    llm_enabled=False,
    llm_base_url="",
    llm_model="",
    llm_api_key="",
    log_level="INFO",
    output_dir="output",
    finder_min_score=0.20,
    finder_margin=0.10,
)

MakeEntry = Callable[..., ServiceEntry]


@pytest.fixture
def entries(make_entry: MakeEntry) -> list[ServiceEntry]:
    return [
        make_entry("ipva", area="tax", keywords=("ipva", "imposto do carro"), display_name="IPVA", agency="Sefaz"),
        make_entry(
            "cnh",
            area="vehicles",
            keywords=("cnh", "carteira de motorista"),
            display_name="Carteira de habilitação",
            agency="Detran",
        ),
        make_entry(
            "vaccination",
            area="health",
            keywords=("vacina", "calendario de vacinacao"),
            display_name="Vacinação",
            agency="Ministério da Saúde",
        ),
    ]


def _with(settings: Settings, **overrides: float) -> Settings:
    return dataclasses.replace(settings, **overrides)


@pytest.mark.parametrize(
    ("text", "expected_id"),
    [
        ("quero pagar o ipva do meu carro", "ipva"),
        ("QUERO RENOVAR A CNH", "cnh"),
        ("Preciso da carteira de motorista", "cnh"),
        ("qual o calendário de vacinação das crianças?", "vaccination"),
    ],
)
def test_finds_the_entry_that_matches_the_request(entries: list[ServiceEntry], text: str, expected_id: str) -> None:
    match = ServiceFinder(entries, SETTINGS).find(text)

    assert match is not None
    assert match.entry.id == expected_id
    assert match.score > 0
    assert match.margin > 0


def test_returns_the_entry_itself_and_nothing_else(entries: list[ServiceEntry]) -> None:
    match = ServiceFinder(entries, SETTINGS).find("quero pagar o ipva")

    assert match is not None
    assert match.entry is entries[0]
    assert {field.name for field in dataclasses.fields(FinderMatch)} == {"entry", "score", "margin"}


@pytest.mark.parametrize("text", ["como fazer um bolo de cenoura", "asdf qwer zxcv", "oi"])
def test_unrelated_text_finds_nothing(entries: list[ServiceEntry], text: str) -> None:
    assert ServiceFinder(entries, SETTINGS).find(text) is None


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "[CPF] [TELEFONE] [EMAIL]", "!!! ???"])
def test_empty_or_termless_text_finds_nothing(entries: list[ServiceEntry], text: str) -> None:
    finder = ServiceFinder(entries, _with(SETTINGS, finder_min_score=0.0, finder_margin=0.0))

    assert finder.find(text) is None
    assert finder.best(text) is None


def test_tie_between_entries_of_different_areas_is_rejected_by_margin(make_entry: MakeEntry) -> None:
    twins = [
        make_entry("a_tax", area="tax", keywords=("licenca",), display_name="Licença", agency="Órgão"),
        make_entry("b_city", area="city", keywords=("licenca",), display_name="Licença", agency="Órgão"),
    ]
    finder = ServiceFinder(twins, SETTINGS)

    best = finder.best("preciso de uma licença")

    assert best is not None
    assert best.margin == pytest.approx(0.0)
    assert finder.find("preciso de uma licença") is None


def test_a_single_entry_has_the_whole_score_as_margin(make_entry: MakeEntry) -> None:
    only = make_entry("ipva", keywords=("ipva",), display_name="IPVA", agency="Sefaz")

    match = ServiceFinder([only], SETTINGS).find("ipva")

    assert match is not None
    assert match.margin == pytest.approx(match.score)


def test_score_below_the_minimum_finds_nothing(entries: list[ServiceEntry]) -> None:
    strict = _with(SETTINGS, finder_min_score=0.99)

    assert ServiceFinder(entries, strict).find("quero pagar o ipva do meu carro") is None


def test_margin_below_the_threshold_finds_nothing(entries: list[ServiceEntry]) -> None:
    strict = _with(SETTINGS, finder_margin=0.99)

    assert ServiceFinder(entries, strict).find("quero pagar o ipva do meu carro") is None


def test_thresholds_are_inclusive(entries: list[ServiceEntry]) -> None:
    best = ServiceFinder(entries, SETTINGS).best("quero pagar o ipva do meu carro")
    assert best is not None
    exact = _with(SETTINGS, finder_min_score=best.score, finder_margin=best.margin)

    assert ServiceFinder(entries, exact).find("quero pagar o ipva do meu carro") is not None


def test_best_ignores_the_thresholds(entries: list[ServiceEntry]) -> None:
    strict = _with(SETTINGS, finder_min_score=1.0, finder_margin=1.0)
    finder = ServiceFinder(entries, strict)

    assert finder.find("quero pagar o ipva") is None
    assert finder.best("quero pagar o ipva") is not None


def test_candidate_entries_are_never_found(entries: list[ServiceEntry], make_entry: MakeEntry) -> None:
    candidate = make_entry("passport", status="candidate", keywords=("passaporte",), display_name="Passaporte")
    finder = ServiceFinder([*entries, candidate], SETTINGS)

    assert finder.find("quero tirar o passaporte") is None


def test_catalog_without_approved_entries_finds_nothing(make_entry: MakeEntry) -> None:
    only_candidates = [make_entry("ipva", status="candidate", keywords=("ipva",), display_name="IPVA")]

    assert ServiceFinder([], SETTINGS).find("ipva") is None
    assert ServiceFinder(only_candidates, SETTINGS).find("ipva") is None
    assert ServiceFinder(only_candidates, SETTINGS).best("ipva") is None


def test_entry_order_does_not_change_the_result(entries: list[ServiceEntry]) -> None:
    texts = ["quero pagar o ipva", "renovar a cnh", "vacina das crianças", "imposto do carro e cnh"]
    forward = ServiceFinder(entries, SETTINGS)
    backward = ServiceFinder(list(reversed(entries)), SETTINGS)

    for text in texts:
        assert forward.best(text) == backward.best(text)


def test_same_text_gives_the_same_result(entries: list[ServiceEntry]) -> None:
    finder = ServiceFinder(entries, SETTINGS)

    first = finder.best("quero pagar o ipva do carro")

    assert finder.best("quero pagar o ipva do carro") == first
    assert ServiceFinder(entries, SETTINGS).best("quero pagar o ipva do carro") == first


def test_accepts_any_iterable_of_entries(entries: list[ServiceEntry]) -> None:
    match = ServiceFinder(iter(entries), SETTINGS).find("quero pagar o ipva")

    assert match is not None
    assert match.entry.id == "ipva"
