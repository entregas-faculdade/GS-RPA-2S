"""Localizador de fontes: só entradas aprovadas, pontuação e folga, limiares e determinismo (catálogo fake, sem rede)."""

import csv
import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from triage.automation.catalog import ServiceEntry, approved_only, load_catalog
from triage.automation.finder import FinderMatch, ServiceFinder
from triage.classification.preprocessing import normalize
from triage.config import Settings

FINDER_CSV = Path("data") / "labeled" / "finder_requests.csv"

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


def test_top_candidates_are_ranked_by_score_and_limited(entries: list[ServiceEntry]) -> None:
    finder = ServiceFinder(entries, SETTINGS)
    text = "quero pagar o ipva do carro e a vacina"

    ranked = finder.top_candidates(text, 2)

    assert len(ranked) == 2
    assert ranked[0].id == finder.best(text).entry.id
    assert len(finder.top_candidates("ipva cnh vacina", 1)) == 1


def test_top_candidates_ignore_the_thresholds_but_skip_zero_scores(entries: list[ServiceEntry]) -> None:
    finder = ServiceFinder(entries, _with(SETTINGS, finder_min_score=1.0, finder_margin=1.0))

    assert [entry.id for entry in finder.top_candidates("ipva", 5)] == ["ipva"]


@pytest.mark.parametrize(("text", "limit"), [("", 5), ("   ", 5), ("zzz qqq", 5), ("ipva", 0)])
def test_top_candidates_empty_cases(entries: list[ServiceEntry], text: str, limit: int) -> None:
    assert ServiceFinder(entries, SETTINGS).top_candidates(text, limit) == ()


def test_top_candidates_never_include_candidate_entries(entries: list[ServiceEntry], make_entry: MakeEntry) -> None:
    candidate = make_entry("passport", status="candidate", keywords=("passaporte",), display_name="Passaporte")
    finder = ServiceFinder([*entries, candidate], SETTINGS)

    assert finder.top_candidates("quero o passaporte", 5) == ()


def test_the_content_of_an_entry_is_searchable(make_entry: MakeEntry) -> None:
    plain = make_entry("plain", keywords=("tema",), display_name="Tema geral", agency="Órgão A")
    with_content = make_entry(
        "detailed",
        keywords=("outro tema",),
        display_name="Outro tema",
        agency="Órgão B",
        content="Para trocar o hodometro adulterado procure a vistoria veicular obrigatoria.",
    )
    finder = ServiceFinder([plain, with_content], SETTINGS)

    match = finder.find("meu hodometro esta adulterado")

    assert match is not None
    assert match.entry.id == "detailed"
    assert ServiceFinder([plain, dataclasses.replace(with_content, content="")], SETTINGS).best("hodometro adulterado") is None


def _legacy_best(entries: list[ServiceEntry], text: str) -> tuple[str, float, float] | None:
    """Referência: o localizador de antes do `content` (documento = keywords + nome + órgão), montado à parte."""
    approved = sorted(approved_only(entries), key=lambda entry: entry.id)
    documents = [" ".join((*entry.keywords, entry.display_name, entry.agency)) for entry in approved]
    vectorizer = TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2), sublinear_tf=True)
    matrix = vectorizer.fit_transform(documents)
    query = vectorizer.transform([text])
    if query.nnz == 0:
        return None
    scores = matrix.dot(query.T).toarray().ravel().tolist()
    best = scores.index(max(scores))
    margin = scores[best] - max(scores[:best] + scores[best + 1 :], default=0.0)
    return approved[best].id, scores[best], margin


def test_without_content_scores_are_identical_to_the_previous_finder_on_the_labeled_requests() -> None:
    entries = load_catalog(extra_dir=None)
    assert all(entry.content == "" for entry in entries)
    finder = ServiceFinder(entries, SETTINGS)
    with FINDER_CSV.open(encoding="utf-8", newline="") as handle:
        texts = [row["text"] for row in csv.DictReader(handle)]
    assert len(texts) == 96

    for text in texts:
        expected = _legacy_best(entries, text)
        actual = finder.best(text)
        if expected is None:
            assert actual is None, text
            continue
        assert actual is not None, text
        assert (actual.entry.id, actual.score, actual.margin) == (expected[0], pytest.approx(expected[1]), pytest.approx(expected[2])), text
