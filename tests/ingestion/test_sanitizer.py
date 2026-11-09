"""Testes da sanitização e da validação de pedidos."""

import pytest

from triage.ingestion.models import REASON_EMPTY_ID, REASON_TEXT_TOO_SHORT, Rejection, Request
from triage.ingestion.sanitizer import MAX_TEXT_LENGTH, MIN_TEXT_LENGTH, TextTooLargeError, sanitize, validate


def test_script_block_is_removed_with_its_content() -> None:
    assert sanitize("antes <script>alert(1)</script> depois") == "antes depois"


def test_unclosed_script_removes_everything_after_it() -> None:
    assert sanitize("antes <script>alert(1) e o resto") == "antes"


def test_script_with_uppercase_and_attributes_is_removed() -> None:
    assert "alert" not in sanitize('x <SCRIPT type="text/javascript">alert(1)</SCRIPT> y')


def test_other_tags_lose_only_the_marker() -> None:
    assert sanitize("<p>olá <b>mundo</b></p>") == "olá mundo"


def test_html_comment_is_removed() -> None:
    assert sanitize("a <!-- escondido --> b") == "a b"


def test_comparison_is_not_mistaken_for_a_tag() -> None:
    assert sanitize("2 < 3 e 5 > 4") == "2 < 3 e 5 > 4"


def test_control_characters_are_removed_but_newline_and_tab_survive_as_whitespace() -> None:
    assert sanitize("a\x00b\x07c\nd\te") == "abc\nd e"


def test_control_char_inside_tag_name_does_not_evade_the_filter() -> None:
    assert sanitize("x <scr\x00ipt>alert(1)</script> y") == "x y"


def test_unicode_is_normalized_to_nfkc() -> None:
    assert sanitize("＜script＞alert(1)＜/script＞ok") == "ok"


@pytest.mark.parametrize(
    "payload",
    ["' OR '1'='1", "' or '1'='1'", "x; -- y", "x;-- y"],
)
def test_sql_injection_sequences_are_neutralized(payload: str) -> None:
    result = sanitize(f"antes {payload} depois")

    assert "'1'='1" not in result.replace(" ", "")
    assert "--" not in result
    assert result.startswith("antes") and result.endswith("depois")


def test_whitespace_is_collapsed() -> None:
    assert sanitize("  muitos     espaços \n\n\n\n aqui  ") == "muitos espaços\n\naqui"


def test_text_at_the_limit_is_accepted() -> None:
    assert len(sanitize("a" * MAX_TEXT_LENGTH)) == MAX_TEXT_LENGTH


def test_text_over_the_limit_raises_too_large() -> None:
    with pytest.raises(TextTooLargeError):
        sanitize("a" * (MAX_TEXT_LENGTH + 1))


def test_validate_accepts_a_good_request() -> None:
    assert validate(Request("1", "pedido válido", "f.txt")) is None


@pytest.mark.parametrize("request_id", ["", "   "])
def test_validate_rejects_empty_id(request_id: str) -> None:
    assert validate(Request(request_id, "pedido válido", "f.txt")) == Rejection("f.txt", REASON_EMPTY_ID)


def test_validate_rejects_text_shorter_than_minimum() -> None:
    short_text = "a" * (MIN_TEXT_LENGTH - 1)

    assert validate(Request("1", short_text, "f.txt")) == Rejection("f.txt", REASON_TEXT_TOO_SHORT)
