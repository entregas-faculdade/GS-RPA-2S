"""Testes estruturais do notebook de evidências entregue (`entrega-gs/evidencias/evidence.ipynb`).

Só leem o arquivo (sem rede, sem executar o notebook): conferem que ele foi entregue executado de ponta a ponta,
sem erro, sem chave nem caminho absoluto, e que traz as seções e as evidências que o enunciado pede.
"""

import re
from pathlib import Path

import nbformat
import pytest

NOTEBOOK_PATH = Path(__file__).resolve().parent.parent / "entrega-gs" / "evidencias" / "evidence.ipynb"
MIN_QUESTIONS = 15
SECTION_KEYWORDS = ("lote", "perguntas", "catálogo de interações", "métricas", "falhas", "limites")
FORBIDDEN_PATH_MARKERS = ("C:\\Users", "C:\\\\Users", "C:/Users", "/Users/", "/home/")  # com e sem escape do JSON
KEY_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgsk_[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{8,}"),
    re.compile(r"LLM_API_KEY\s*=\s*\S+"),
)
DOTENV_AT_ROOT = re.compile(r"load_settings\([^)]*dotenv_path\s*=\s*ENV_FILE\b")
ENV_FILE_AT_ROOT = re.compile(r"ENV_FILE\s*=\s*ROOT\s*/\s*[\"']\.env[\"']")
QUESTIONS_COUNT = re.compile(r"Perguntas processadas:\s*(\d+)")
USED_LLM_COUNT = re.compile(r"used_llm verdadeiro:\s*(\d+)")
LLM_TOPIC_COUNT = re.compile(r"topic_source=llm\):\s*(\d+)")


@pytest.fixture(scope="module")
def notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK_PATH, as_version=4)


@pytest.fixture(scope="module")
def raw_text() -> str:
    return NOTEBOOK_PATH.read_text(encoding="utf-8")


def _code_cells(notebook: nbformat.NotebookNode) -> list:
    return [cell for cell in notebook.cells if cell.cell_type == "code"]


def _single_output_text(output: nbformat.NotebookNode) -> str:
    """Texto de uma saída: o fluxo, ou o `text/plain` de um resultado ou exibição; outras saídas não têm texto."""
    if output.output_type == "stream":
        return output.text
    if "data" in output:
        return output.data.get("text/plain", "")
    return ""


def _output_text(notebook: nbformat.NotebookNode) -> str:
    """Todo o texto das saídas salvas (fluxos, resultados e exibições)."""
    outputs = [output for cell in _code_cells(notebook) for output in cell.outputs]
    return "\n".join(_single_output_text(output) for output in outputs)


def _last_count(pattern: re.Pattern[str], text: str) -> int:
    found = pattern.findall(text)
    return int(found[-1]) if found else 0


def test_file_is_a_valid_notebook(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)


def test_every_code_cell_was_executed_in_order(notebook: nbformat.NotebookNode) -> None:
    counts = [cell.execution_count for cell in _code_cells(notebook)]

    assert counts == list(range(1, len(counts) + 1))


def test_saved_outputs_exist(notebook: nbformat.NotebookNode) -> None:
    with_output = [cell for cell in _code_cells(notebook) if cell.outputs]

    assert len(with_output) >= len(_code_cells(notebook)) // 2


def test_no_error_output_or_traceback(notebook: nbformat.NotebookNode, raw_text: str) -> None:
    error_outputs = [out for cell in _code_cells(notebook) for out in cell.outputs if out.output_type == "error"]

    assert error_outputs == []
    assert "Traceback" not in raw_text


def test_no_absolute_user_path(raw_text: str) -> None:
    found = [marker for marker in FORBIDDEN_PATH_MARKERS if marker in raw_text]

    assert found == []


def test_no_api_key_pattern(raw_text: str) -> None:
    found = [pattern.pattern for pattern in KEY_PATTERNS if pattern.search(raw_text)]

    assert found == []


def test_dotenv_is_loaded_from_the_project_root(notebook: nbformat.NotebookNode) -> None:
    sources = [cell.source for cell in _code_cells(notebook)]

    assert any(
        DOTENV_AT_ROOT.search(source) and ENV_FILE_AT_ROOT.search(source) and "os.chdir(ROOT)" in source
        for source in sources
    )


def test_no_cell_prints_the_environment(notebook: nbformat.NotebookNode) -> None:
    sources = "\n".join(cell.source for cell in _code_cells(notebook))

    assert "os.environ" not in sources
    assert not re.search(r"print\(\s*settings\s*\)", sources)


@pytest.mark.parametrize("keyword", SECTION_KEYWORDS)
def test_expected_section_exists(notebook: nbformat.NotebookNode, keyword: str) -> None:
    headings = [
        line.lower()
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#")
    ]

    assert any(keyword in heading for heading in headings)


def test_question_test_has_at_least_the_minimum_questions(notebook: nbformat.NotebookNode) -> None:
    assert _last_count(QUESTIONS_COUNT, _output_text(notebook)) >= MIN_QUESTIONS


def test_output_shows_the_real_llm_was_used(notebook: nbformat.NotebookNode) -> None:
    text = _output_text(notebook)

    assert _last_count(USED_LLM_COUNT, text) >= 1
    assert _last_count(LLM_TOPIC_COUNT, text) >= 1
