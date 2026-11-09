"""Testes dos leitores de pedidos e da leitura de pasta."""

import logging
from pathlib import Path

import pytest

from triage.ingestion import Rejection, Request, read_folder
from triage.ingestion.models import (
    REASON_EMPTY_FILE,
    REASON_EMPTY_ID,
    REASON_INVALID_CSV,
    REASON_INVALID_JSON,
    REASON_MISSING_TEXT,
    REASON_MISSING_TEXT_COLUMN,
    REASON_TEXT_TOO_SHORT,
    REASON_TOO_LARGE,
    REASON_UNREADABLE_ENCODING,
    REASON_UNREADABLE_FILE,
)
from triage.ingestion.readers import read_csv, read_json, read_txt
from triage.ingestion.sanitizer import MAX_TEXT_LENGTH

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"
CSV_FIELD_LIMIT_BREAKER = 200_000


def _write(folder: Path, name: str, content: str | bytes) -> Path:
    path = folder / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _reasons(rejections: list[Rejection]) -> list[str]:
    return [rejection.reason for rejection in rejections]


# --- arquivos bons de cada formato ---


def test_txt_good_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "pedido-7.txt", "Quero a segunda via do documento.\n")

    requests, rejections = read_txt(path)

    assert requests == [Request("pedido-7", "Quero a segunda via do documento.", "pedido-7.txt")]
    assert rejections == []


def test_csv_good_file_with_bom_and_multiline_field(tmp_path: Path) -> None:
    path = _write(tmp_path, "p.csv", '﻿id,text\nA1,primeiro pedido\nA2,"segundo\npedido"\n')

    requests, rejections = read_csv(path)

    assert [(r.id, r.text, r.source) for r in requests] == [
        ("A1", "primeiro pedido", "p.csv#1"),
        ("A2", "segundo\npedido", "p.csv#2"),
    ]
    assert rejections == []


def test_json_list_and_single_object(tmp_path: Path) -> None:
    listed = _write(tmp_path, "l.json", '[{"id": "a", "text": "pedido um"}, {"id": 2, "text": "pedido dois"}]')
    single = _write(tmp_path, "s.json", '{"id": "x", "text": "pedido único"}')

    assert [(r.id, r.source) for r in read_json(listed)[0]] == [("a", "l.json#1"), ("2", "l.json#2")]
    assert read_json(single) == ([Request("x", "pedido único", "s.json")], [])


# --- motivos de rejeição ---


@pytest.mark.parametrize(
    ("name", "content"),
    [("v.txt", ""), ("v.txt", "  \n\t "), ("v.csv", "id,text\n"), ("v.json", "[]"), ("v.json", "   ")],
)
def test_empty_file(tmp_path: Path, name: str, content: str) -> None:
    path = _write(tmp_path, name, content)
    reader = {"txt": read_txt, "csv": read_csv, "json": read_json}[name.rsplit(".", 1)[1]]

    assert reader(path) == ([], [Rejection(name, REASON_EMPTY_FILE)])


def test_invalid_json(tmp_path: Path) -> None:
    path = _write(tmp_path, "b.json", '{"id": "x", "text": ')

    assert read_json(path) == ([], [Rejection("b.json", REASON_INVALID_JSON)])


def test_json_with_wrong_shape_or_bad_item(tmp_path: Path) -> None:
    scalar = _write(tmp_path, "n.json", "42")
    mixed = _write(tmp_path, "m.json", '[7, {"id": "ok", "text": "pedido válido"}]')

    assert read_json(scalar) == ([], [Rejection("n.json", REASON_INVALID_JSON)])
    requests, rejections = read_json(mixed)
    assert [r.id for r in requests] == ["ok"]
    assert rejections == [Rejection("m.json#1", REASON_INVALID_JSON)]


def test_json_deeply_nested_does_not_raise(tmp_path: Path) -> None:
    path = _write(tmp_path, "d.json", "[" * 100_000)

    assert read_json(path) == ([], [Rejection("d.json", REASON_INVALID_JSON)])


def test_json_item_without_text(tmp_path: Path) -> None:
    path = _write(tmp_path, "t.json", '[{"id": "a"}, {"id": "b", "text": 5}]')

    assert _reasons(read_json(path)[1]) == [REASON_MISSING_TEXT, REASON_MISSING_TEXT]


def test_csv_without_text_column(tmp_path: Path) -> None:
    path = _write(tmp_path, "c.csv", "id,mensagem\n1,algo\n")

    assert read_csv(path) == ([], [Rejection("c.csv", REASON_MISSING_TEXT_COLUMN)])


def test_csv_field_over_parser_limit_is_invalid_csv(tmp_path: Path) -> None:
    path = _write(tmp_path, "g.csv", "id,text\n1," + "a" * CSV_FIELD_LIMIT_BREAKER + "\n")

    assert read_csv(path) == ([], [Rejection("g.csv", REASON_INVALID_CSV)])


def test_unreadable_encoding(tmp_path: Path) -> None:
    path = _write(tmp_path, "e.txt", b"texto \xff\xfe quebrado")

    assert read_txt(path) == ([], [Rejection("e.txt", REASON_UNREADABLE_ENCODING)])


def test_unreadable_file(tmp_path: Path) -> None:
    directory = tmp_path / "pasta.txt"
    directory.mkdir()

    assert read_txt(directory) == ([], [Rejection("pasta.txt", REASON_UNREADABLE_FILE)])


def test_too_large_text_is_rejected_per_record(tmp_path: Path) -> None:
    big = "a" * (MAX_TEXT_LENGTH + 1)
    path = _write(tmp_path, "big.csv", f"id,text\n1,{big}\n2,pedido normal\n")

    requests, rejections = read_csv(path)

    assert [r.id for r in requests] == ["2"]
    assert rejections == [Rejection("big.csv#1", REASON_TOO_LARGE)]


def test_validation_rejections_come_from_the_readers(tmp_path: Path) -> None:
    path = _write(tmp_path, "v.csv", "id,text\n,pedido sem id\n2,<b></b>\n")

    assert _reasons(read_csv(path)[1]) == [REASON_EMPTY_ID, REASON_TEXT_TOO_SHORT]


def test_request_text_comes_sanitized(tmp_path: Path) -> None:
    path = _write(tmp_path, "h.txt", "oi <script>alert(1)</script>mundo\x00")

    assert read_txt(path)[0][0].text == "oi mundo"


# --- pasta ---


def test_mixed_folder_returns_partial_result_without_raising(tmp_path: Path) -> None:
    _write(tmp_path, "ok.txt", "pedido bom")
    _write(tmp_path, "vazio.txt", "")
    _write(tmp_path, "quebrado.json", "{")
    _write(tmp_path, "mix.csv", "id,text\n1,pedido do csv\n")

    requests, rejections = read_folder(tmp_path)

    assert sorted(r.source for r in requests) == ["mix.csv#1", "ok.txt"]
    assert sorted(_reasons(rejections)) == [REASON_EMPTY_FILE, REASON_INVALID_JSON]


def test_folder_is_not_recursive_and_warns_about_unsupported_extension(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write(tmp_path, "ok.TXT", "pedido bom")
    _write(tmp_path, "nota.pdf", "ignorado")
    (tmp_path / "sub").mkdir()
    _write(tmp_path / "sub", "fundo.txt", "pedido escondido")

    with caplog.at_level(logging.WARNING, logger="triage.ingestion"):
        requests, rejections = read_folder(tmp_path)

    assert [r.source for r in requests] == ["ok.TXT"]
    assert rejections == []
    assert "nota.pdf" in caplog.text


def test_missing_folder_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_folder(tmp_path / "nao-existe")


def test_logs_never_contain_the_raw_request_text(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    marker = "SEGREDO-DO-CIDADAO"
    _write(tmp_path, "ok.txt", f"pedido com {marker}")
    _write(tmp_path, "grande.txt", marker * MAX_TEXT_LENGTH)
    _write(tmp_path, "json.json", f'[{{"id": "a", "text": "<b></b>"}}, {{"id": "{marker}"}}, 3]')
    _write(tmp_path, "curto.csv", f"id,text\n{marker},ab\n")

    with caplog.at_level(logging.DEBUG):
        requests, rejections = read_folder(tmp_path)

    assert requests and rejections
    assert caplog.records
    assert marker not in caplog.text


# --- amostras versionadas ---


def test_sample_folder_has_valid_requests_and_rejections() -> None:
    requests, rejections = read_folder(SAMPLES_DIR)

    assert len(requests) > 0
    assert {
        REASON_EMPTY_FILE,
        REASON_INVALID_JSON,
        REASON_MISSING_TEXT_COLUMN,
        REASON_UNREADABLE_ENCODING,
        REASON_TOO_LARGE,
    } <= set(_reasons(rejections))
    assert all("<script" not in r.text.lower() and "\x00" not in r.text for r in requests)
