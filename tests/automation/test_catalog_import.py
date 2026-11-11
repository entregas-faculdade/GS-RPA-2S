"""Importador da planilha da base enriquecida: leitura nos dois formatos de texto, mapeamento, status, determinismo e o JSON do repositório."""

import json
import zipfile
from collections.abc import Callable
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from triage.automation.allowlist import is_allowed, load_allowed_suffixes
from triage.automation.catalog import (
    KIND_SERVICE,
    ServiceEntry,
    load_catalog,
    parse_entry,
)
from triage.automation.catalog_import import (
    CatalogImportError,
    ImportConfig,
    ImportOptions,
    ImportReport,
    convert_rows,
    find_pairs,
    format_report,
    import_xlsx,
    load_import_config,
    read_xlsx_rows,
    write_catalog_json,
)

HEADER = [
    "ID",
    "Esfera / Órgão",
    "Macro-Categoria",
    "Finalidade / Descrição do Serviço",
    "URL Oficial",
    "Palavras-Chave / Intents (NLP)",
    "Tipo de Interação / Notas RPA",
]
NOTES = "Playwright com User-Agent rotativo"
MUNICIPAL = ["M02", "Secretaria da Fazenda", "Tributos", "Segunda Via de IPTU", "https://www.prefeitura.sp.gov.br/iptu", "iptu,  2 via , iptu,,boleto", NOTES]
STATE = ["S07", "Fazenda SP", "Tributos Estaduais", "Consulta de IPVA", "https://portal.fazenda.sp.gov.br/ipva", "ipva", NOTES]
FEDERAL = ["F01", "Governo Federal", "Institucional", "Portal de Autenticação", "https://sso.acesso.gov.br", "login gov", NOTES]
SYNTHETIC_CATEGORY = ["M99", "Órgão X", "Categoria Inexistente", "Serviço qualquer", "https://www.prefeitura.sp.gov.br/x", "x", NOTES]
OUTSIDE_ALLOWLIST = ["M14", "CET", "Trânsito", "Defesa de multa", "https://www.exemplo-fora.com.br", "multa", NOTES]
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _column(index: int) -> str:
    return "ABCDEFGHIJ"[index]


def _sheet_xml(rows: list[list[str]], shared: list[str] | None) -> str:
    """Planilha mínima; célula vazia é omitida (como o Excel faz) e o texto vai em `sharedStrings` ou `inlineStr`."""
    lines = []
    for number, row in enumerate(rows, start=1):
        cells = []
        for index, text in enumerate(row):
            if not text:
                continue
            ref = f"{_column(index)}{number}"
            if shared is None:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>')
            else:
                shared.append(text)
                cells.append(f'<c r="{ref}" t="s"><v>{len(shared) - 1}</v></c>')
        lines.append(f'<row r="{number}">{"".join(cells)}</row>')
    return f'<worksheet xmlns="{SHEET_NS}"><sheetData>{"".join(lines)}</sheetData></worksheet>'


def _write_xlsx(path: Path, rows: list[list[str]], use_shared_strings: bool) -> Path:
    shared: list[str] | None = [] if use_shared_strings else None
    sheet = _sheet_xml(rows, shared)
    workbook = f'<workbook xmlns="{SHEET_NS}" xmlns:r="{REL_NS}"><sheets><sheet name="A" sheetId="1" r:id="rId1"/></sheets></workbook>'
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
        if shared is not None:
            items = "".join(f"<si><t>{escape(text)}</t></si>" for text in shared)
            archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{SHEET_NS}">{items}</sst>')
    return path


@pytest.fixture
def config() -> ImportConfig:
    return load_import_config()


@pytest.fixture
def options() -> ImportOptions:
    return ImportOptions("2026-11-11", frozenset({"gov.br"}), "planilha.xlsx")


@pytest.fixture
def convert(
    tmp_path: Path, config: ImportConfig, options: ImportOptions
) -> Callable[..., ImportReport]:
    def run(*data_rows: list[str], shared: bool = True) -> ImportReport:
        xlsx = _write_xlsx(tmp_path / "base.xlsx", [HEADER, *data_rows], shared)
        return import_xlsx(xlsx, config, options)

    return run


@pytest.mark.parametrize("use_shared_strings", [True, False])
def test_reads_both_text_formats_and_keeps_empty_cells_in_place(tmp_path: Path, use_shared_strings: bool) -> None:
    row = ["M02", "Fazenda", "", "Nome", "https://a.gov.br", "", NOTES]
    xlsx = _write_xlsx(tmp_path / "base.xlsx", [HEADER, row], use_shared_strings)

    rows = read_xlsx_rows(xlsx)

    assert rows[0][0] == 2
    values = rows[0][1]
    assert values["id"] == "M02"
    assert values["macro-categoria"] == ""
    assert values["finalidade / descricao do servico"] == "Nome"
    assert values["palavras-chave / intents (nlp)"] == ""


def test_header_is_matched_without_accent_or_case(tmp_path: Path, config: ImportConfig, options: ImportOptions) -> None:
    header = [name.upper().replace("Ó", "O") for name in HEADER]
    xlsx = _write_xlsx(tmp_path / "base.xlsx", [header, MUNICIPAL], True)

    assert len(import_xlsx(xlsx, config, options).records) == 1


def test_missing_file_not_a_zip_and_missing_column_raise_clear_errors(
    tmp_path: Path, config: ImportConfig, options: ImportOptions
) -> None:
    not_zip = tmp_path / "ruim.xlsx"
    not_zip.write_text("texto", encoding="utf-8")
    without_column = _write_xlsx(tmp_path / "sem-coluna.xlsx", [HEADER[:-1], MUNICIPAL[:-1]], True)

    with pytest.raises(CatalogImportError, match="ilegível"):
        read_xlsx_rows(tmp_path / "ausente.xlsx")
    with pytest.raises(CatalogImportError, match="ilegível"):
        read_xlsx_rows(not_zip)
    with pytest.raises(CatalogImportError, match="sem as colunas"):
        import_xlsx(without_column, config, options)


def test_zip_without_a_sheet_raises(tmp_path: Path) -> None:
    empty = tmp_path / "vazio.xlsx"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{SHEET_NS}"><sheets/></workbook>')

    with pytest.raises(CatalogImportError, match="sem nenhuma aba"):
        read_xlsx_rows(empty)


def test_maps_one_record_of_each_scope(convert: Callable[..., ImportReport]) -> None:
    report = convert(MUNICIPAL, STATE, FEDERAL)

    municipal, state, federal = report.records
    assert (municipal["id"], municipal["scope"], municipal["coverage"]) == ("xl_m02", "municipal", "Município de São Paulo")
    assert (state["id"], state["scope"], state["coverage"]) == ("xl_s07", "state", "Estado de São Paulo")
    assert (federal["id"], federal["scope"], federal["coverage"]) == ("xl_f01", "federal", "Brasil")
    assert municipal["display_name"] == "Segunda Via de IPTU"
    assert municipal["agency"] == "Secretaria da Fazenda"
    assert municipal["links"] == [{"label": "Segunda Via de IPTU", "url": "https://www.prefeitura.sp.gov.br/iptu"}]
    assert (municipal["phones"], municipal["category"], municipal["verified_on"]) == ([], None, "2026-11-11")
    assert "content" not in municipal
    assert all(parse_entry(record).status == "approved" for record in report.records)


def test_area_comes_from_the_table_and_unknown_category_falls_to_city_with_a_notice(
    convert: Callable[..., ImportReport],
) -> None:
    report = convert(STATE, FEDERAL, SYNTHETIC_CATEGORY)

    assert [record["area"] for record in report.records] == ["tax", "city", "city"]
    assert report.default_area == [("xl_m99", "Categoria Inexistente")]


def test_kind_is_portal_only_when_the_purpose_starts_with_portal(convert: Callable[..., ImportReport]) -> None:
    report = convert(MUNICIPAL, FEDERAL)

    assert [record["kind"] for record in report.records] == [KIND_SERVICE, "portal"]


def test_keywords_are_trimmed_without_blanks_or_repeats(convert: Callable[..., ImportReport]) -> None:
    (record,) = convert(MUNICIPAL).records

    assert record["keywords"] == ["iptu", "2 via", "boleto"]


def test_rpa_notes_stay_out_of_instructions_and_only_go_to_the_source_note(convert: Callable[..., ImportReport]) -> None:
    (record,) = convert(MUNICIPAL).records

    assert NOTES not in record["instructions"]
    assert "content" not in record
    assert NOTES in record["source_note"]
    assert "planilha.xlsx" in record["source_note"]
    assert "linha 2" in record["source_note"]
    assert record["instructions"] == "Secretaria da Fazenda: Segunda Via de IPTU. Acesse a página oficial para ver como fazer."


def test_rows_without_id_url_or_with_repeated_id_are_ignored_and_reported(convert: Callable[..., ImportReport]) -> None:
    no_id = ["", *MUNICIPAL[1:]]
    no_url = ["M03", *MUNICIPAL[1:4], "", *MUNICIPAL[5:]]
    repeated = ["m02", *STATE[1:]]

    report = convert(MUNICIPAL, no_id, no_url, repeated, FEDERAL)

    assert [record["id"] for record in report.records] == ["xl_m02", "xl_f01"]
    assert report.rows_read == 5
    assert dict(report.ignored) == {"linha 3": "linha sem ID", "M03": "linha sem URL", "m02": "ID repetido"}


def test_row_with_unknown_scope_prefix_is_ignored(convert: Callable[..., ImportReport]) -> None:
    report = convert(["X01", *MUNICIPAL[1:]])

    assert report.records == []
    assert "prefixo do ID" in report.ignored[0][1]


def test_fully_blank_rows_are_not_counted(convert: Callable[..., ImportReport]) -> None:
    assert convert(MUNICIPAL, [""] * 7).rows_read == 1


def test_host_outside_the_allowlist_becomes_candidate_with_the_reason(convert: Callable[..., ImportReport]) -> None:
    report = convert(OUTSIDE_ALLOWLIST, MUNICIPAL)

    outside, inside = report.records
    assert (outside["status"], inside["status"]) == ("candidate", "approved")
    assert "exemplo-fora.com.br" in outside["source_note"]
    assert report.candidates == [("xl_m14", "domínio fora da allowlist")]


def test_output_is_deterministic_in_both_text_formats(
    tmp_path: Path, config: ImportConfig, options: ImportOptions
) -> None:
    outputs = []
    for use_shared_strings in (True, False):
        xlsx = _write_xlsx(tmp_path / f"{use_shared_strings}.xlsx", [HEADER, MUNICIPAL, STATE, FEDERAL], use_shared_strings)
        for run in range(2):
            out = tmp_path / f"out-{use_shared_strings}-{run}.json"
            write_catalog_json(import_xlsx(xlsx, config, options).records, out)
            outputs.append(out.read_bytes())

    assert len(set(outputs)) == 1
    assert outputs[0].endswith(b"}\n]\n")
    assert "Município".encode() in outputs[0]


def test_pairs_only_for_the_same_normalized_link(convert: Callable[..., ImportReport], make_entry: Callable[..., ServiceEntry]) -> None:
    report = convert(MUNICIPAL, STATE)
    same_link = make_entry("old_iptu", links=(("IPTU", "https://prefeitura.sp.gov.br/iptu/"),))
    same_host_only = make_entry("old_other", links=(("Outro", "https://www.prefeitura.sp.gov.br/outro"),))

    pairs = find_pairs(report.records, [same_link, same_host_only])

    assert [(pair.imported_id, pair.existing_id) for pair in pairs] == [("xl_m02", "old_iptu")]


def test_report_lists_counts_reasons_and_pairs_without_personal_data(
    convert: Callable[..., ImportReport], make_entry: Callable[..., ServiceEntry]
) -> None:
    report = convert(MUNICIPAL, ["", *STATE[1:]], OUTSIDE_ALLOWLIST)
    pair_entry = make_entry("old_iptu", links=(("IPTU", MUNICIPAL[4]),))

    text = format_report(report, find_pairs(report.records, [pair_entry]), Path("saida.json"))

    assert "Linhas lidas: 3" in text
    assert "Registros gerados: 2 (em saida.json)" in text
    assert "Ignoradas: 1" in text
    assert "linha sem ID" in text
    assert "xl_m14: domínio fora da allowlist" in text
    assert "xl_m02 x old_iptu" in text


def test_import_config_with_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(CatalogImportError, match="indisponível"):
        load_import_config(tmp_path / "ausente.json")


def test_convert_rows_with_no_rows_returns_an_empty_report(config: ImportConfig, options: ImportOptions) -> None:
    assert convert_rows([], config, options).records == []


def test_the_four_new_suffixes_are_in_the_allowlist_with_a_reason() -> None:
    records = json.loads((Path("data") / "allowed_domains.json").read_text(encoding="utf-8"))
    reasons = {record["suffix"]: record["reason"] for record in records}

    for suffix in ("cetsp.com.br", "sptrans.com.br", "sabesp.com.br", "desenvolvesp.com.br"):
        assert reasons[suffix].strip()
        assert is_allowed(f"https://www.{suffix}/pagina", load_allowed_suffixes())
    assert not is_allowed("https://cetsp.com.br.evil.com", load_allowed_suffixes())


def test_repository_sp_expanded_loads_with_the_72_ids_and_nothing_rejected(caplog: pytest.LogCaptureFixture) -> None:
    path = Path("data") / "catalog.d" / "sp_expanded.json"
    expected_ids = {f"xl_{prefix}{number:02d}" for prefix, total in (("m", 27), ("s", 21), ("f", 24)) for number in range(1, total + 1)}

    with caplog.at_level("ERROR", logger="triage.automation"):
        entries = [entry for entry in load_catalog() if entry.id.startswith("xl_")]

    assert {entry.id for entry in entries} == expected_ids
    assert len(entries) == len(json.loads(path.read_text(encoding="utf-8"))) == 72
    assert not caplog.records
    assert all(entry.status == "approved" and not entry.content and not entry.phones for entry in entries)
