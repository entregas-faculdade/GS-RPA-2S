from triage.storage import request_hash


def test_hash_is_sha256_hex() -> None:
    assert len(request_hash("texto")) == 64


def test_hash_ignores_case_and_extra_whitespace() -> None:
    assert request_hash("  Preciso   de\num  Documento ") == request_hash("preciso de um documento")


def test_hash_ignores_unicode_composition() -> None:
    assert request_hash("cidadão") == request_hash("cidadão")


def test_hash_differs_for_different_text() -> None:
    assert request_hash("um pedido") != request_hash("outro pedido")
