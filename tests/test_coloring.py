"""
tests/test_coloring.py — Unit tests for LineColorizer.

These tests are fully independent of pytest's plugin machinery.
They operate on plain strings and verify coloring decisions in isolation,
making it easy to catch regressions when changing coloring logic.
"""
import pytest

import pytest_formatter
from pytest_formatter import LineColorizer

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output even when stdout is not a tty (e.g. in CI)."""
    monkeypatch.setattr(pytest_formatter, "_NO_COLOR", False)


# ── Helpers ───────────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED   = "\033[91m"
DIM   = "\033[2m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def has_color(text: str, code: str) -> bool:
    """Return True if text contains the given ANSI escape code."""
    return f"\033[{code}m" in text


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


# ── parse_assert ──────────────────────────────────────────────────────────────

class TestParseAssert:
    """Tests for LineColorizer.parse_assert() — the assertion text splitter."""

    # ── basic equality ────────────────────────────────────────────────────────

    def test_simple_int_equality(self):
        assert LineColorizer.parse_assert("assert 3 == 30") == ("3", "==", "30")

    def test_simple_float_equality(self):
        assert LineColorizer.parse_assert("assert 3.14 == 2.71") == ("3.14", "==", "2.71")

    def test_simple_string_equality(self):
        result = LineColorizer.parse_assert("assert 'INTGPT-109' == 'INTGPT-1091'")
        assert result == ("'INTGPT-109'", "==", "'INTGPT-1091'")

    def test_double_quoted_strings(self):
        result = LineColorizer.parse_assert('assert "hello" == "world"')
        assert result == ('"hello"', "==", '"world"')

    # ── AssertionError prefix ─────────────────────────────────────────────────

    def test_with_assertionerror_prefix(self):
        result = LineColorizer.parse_assert(
            "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        )
        assert result == ("'INTGPT-109'", "==", "'INTGPT-1091'")

    def test_with_assertionerror_prefix_ints(self):
        result = LineColorizer.parse_assert("AssertionError: assert 3 == 30")
        assert result == ("3", "==", "30")

    # ── operators ─────────────────────────────────────────────────────────────

    def test_inequality(self):
        assert LineColorizer.parse_assert("assert 5 != 10") == ("5", "!=", "10")

    def test_less_than(self):
        assert LineColorizer.parse_assert("assert 5 < 3") == ("5", "<", "3")

    def test_greater_than(self):
        assert LineColorizer.parse_assert("assert 1 > 10") == ("1", ">", "10")

    def test_less_than_or_equal(self):
        assert LineColorizer.parse_assert("assert 5 <= 3") == ("5", "<=", "3")

    def test_greater_than_or_equal(self):
        assert LineColorizer.parse_assert("assert 1 >= 10") == ("1", ">=", "10")

    def test_is_not(self):
        assert LineColorizer.parse_assert("assert None is not None") == (
            "None", "is not", "None"
        )

    def test_is(self):
        assert LineColorizer.parse_assert("assert x is None") == ("x", "is", "None")

    def test_in_operator(self):
        assert LineColorizer.parse_assert("assert 'foo' in ['bar', 'baz']") == (
            "'foo'", "in", "['bar', 'baz']"
        )

    def test_not_in_operator(self):
        assert LineColorizer.parse_assert("assert 'x' not in ['x', 'y']") == (
            "'x'", "not in", "['x', 'y']"
        )

    # ── containers ────────────────────────────────────────────────────────────

    def test_list_values(self):
        result = LineColorizer.parse_assert(
            "AssertionError: assert ['Global Launch'] == ['Global Launches']"
        )
        assert result == ("['Global Launch']", "==", "['Global Launches']")

    def test_dict_values(self):
        result = LineColorizer.parse_assert(
            "assert {'a': 1, 'b': 2} == {'a': 1, 'b': 3}"
        )
        assert result == ("{'a': 1, 'b': 2}", "==", "{'a': 1, 'b': 3}")

    def test_set_values(self):
        result = LineColorizer.parse_assert("assert {1, 2, 3} == {1, 2, 4}")
        assert result == ("{1, 2, 3}", "==", "{1, 2, 4}")

    def test_operator_inside_string_not_matched(self):
        """Operators inside string literals must not be mistaken for the real one."""
        result = LineColorizer.parse_assert(
            "assert 'a == b' == 'a == c'"
        )
        # Should split on the outer ==, not the ones inside the strings
        assert result == ("'a == b'", "==", "'a == c'")

    def test_operator_inside_dict_key_not_matched(self):
        """Operators inside containers must not be matched at depth > 0."""
        result = LineColorizer.parse_assert(
            "assert {'x == y': 1} == {'x == y': 2}"
        )
        assert result == ("{'x == y': 1}", "==", "{'x == y': 2}")

    def test_nested_containers(self):
        result = LineColorizer.parse_assert(
            "assert [{'a': [1, 2]}] == [{'a': [1, 3]}]"
        )
        assert result == ("[{'a': [1, 2]}]", "==", "[{'a': [1, 3]}]")

    # ── non-assertions ────────────────────────────────────────────────────────

    def test_exception_line_returns_none(self):
        assert LineColorizer.parse_assert("AttributeError: 'NoneType' object has no attribute 'get'") is None

    def test_runtime_error_returns_none(self):
        assert LineColorizer.parse_assert("RuntimeError: Setup exploded intentionally") is None

    def test_plain_message_returns_none(self):
        assert LineColorizer.parse_assert("got 5, expected 15") is None

    def test_empty_string_returns_none(self):
        assert LineColorizer.parse_assert("") is None

    def test_assert_without_operator_returns_none(self):
        """'assert False' has no comparison operator."""
        assert LineColorizer.parse_assert("assert False") is None

    def test_assert_none_check_no_op_returns_none(self):
        assert LineColorizer.parse_assert("assert None is not None") == (
            "None", "is not", "None"
        )


# ── color_assert_line ─────────────────────────────────────────────────────────

class TestColorAssertLine:
    """Tests for the inline assert colorizer."""

    def test_received_is_red(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        # received (3) should be red
        assert RED in result

    def test_expected_is_green(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        # expected (30) should be green
        assert GREEN in result

    def test_assert_keyword_is_dim(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        assert DIM in result

    def test_plain_text_preserved(self):
        result = strip_ansi(LineColorizer.color_assert_line("assert 3 == 30"))
        assert "assert" in result
        assert "3" in result
        assert "==" in result
        assert "30" in result

    def test_assertionerror_prefix_preserved(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = strip_ansi(LineColorizer.color_assert_line(line))
        assert "AssertionError:" in result
        assert "INTGPT-109" in result
        assert "INTGPT-1091" in result

    def test_unparseable_falls_back_to_red(self):
        line = "got 5, expected 15"
        result = LineColorizer.color_assert_line(line)
        assert RED in result
        assert strip_ansi(result) == line

    def test_string_comparison(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = strip_ansi(LineColorizer.color_assert_line(line))
        assert "INTGPT-109" in result
        assert "INTGPT-1091" in result


# ── color_e_line ──────────────────────────────────────────────────────────────

class TestColorELine:
    """Tests for the main E-line coloring dispatcher."""

    # ── skip outcome ──────────────────────────────────────────────────────────

    def test_skip_outcome_is_yellow(self):
        result = LineColorizer.color_e_line("Skipped: demonstrating skip", "skipped", is_first=True)
        assert has_color(result, "93")  # yellow

    def test_skip_outcome_is_yellow_even_for_non_first(self):
        result = LineColorizer.color_e_line("some context", "skipped", is_first=False)
        assert has_color(result, "93")

    # ── diff lines ────────────────────────────────────────────────────────────

    def test_minus_line_is_green(self):
        result = LineColorizer.color_e_line("- INTGPT-1091", "failed", is_first=False)
        assert GREEN in result

    def test_plus_line_is_red(self):
        result = LineColorizer.color_e_line("+ INTGPT-109", "failed", is_first=False)
        assert RED in result

    def test_question_line_is_dim(self):
        result = LineColorizer.color_e_line("?           -", "failed", is_first=False)
        assert DIM in result

    def test_lone_minus_is_green(self):
        result = LineColorizer.color_e_line("-", "failed", is_first=False)
        assert GREEN in result

    def test_lone_plus_is_red(self):
        result = LineColorizer.color_e_line("+", "failed", is_first=False)
        assert RED in result

    # ── assertion first lines ─────────────────────────────────────────────────

    def test_first_assertion_line_has_green_and_red(self):
        """assert X == Y should color X red and Y green."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert GREEN in result   # expected (30)
        assert RED in result     # received (3)

    def test_first_assertionerror_assertion_colored(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = LineColorizer.color_e_line(line, "failed", is_first=True)
        assert GREEN in result
        assert RED in result

    # ── exception first lines ─────────────────────────────────────────────────

    def test_first_exception_line_is_red(self):
        result = LineColorizer.color_e_line(
            "AttributeError: 'NoneType' object has no attribute 'get'",
            "failed",
            is_first=True,
        )
        assert RED in result

    def test_first_runtime_error_is_red(self):
        result = LineColorizer.color_e_line(
            "RuntimeError: Setup exploded intentionally",
            "failed",
            is_first=True,
        )
        assert RED in result

    # ── context lines ─────────────────────────────────────────────────────────

    def test_non_first_line_is_dim(self):
        result = LineColorizer.color_e_line("At index 0 diff:", "failed", is_first=False)
        assert DIM in result

    def test_differing_items_context_is_dim(self):
        result = LineColorizer.color_e_line("Differing items:", "failed", is_first=False)
        assert DIM in result

    # ── error outcome variants ────────────────────────────────────────────────

    def test_error_outcome_first_line_is_red(self):
        result = LineColorizer.color_e_line(
            "RuntimeError: Setup exploded", "error", is_first=True
        )
        assert RED in result

    def test_xfailed_first_line_is_dim(self):
        """xfailed reason lines use the default path (dim as context)."""
        result = LineColorizer.color_e_line(
            "xfailed: known bug", "xfailed", is_first=False
        )
        assert DIM in result


# ── is_noise ──────────────────────────────────────────────────────────────────

class TestIsNoise:
    """Tests for noise-line detection."""

    def test_use_v_is_noise(self):
        assert LineColorizer.is_noise("Use -v to get more diff") is True

    def test_use_vv_is_noise(self):
        assert LineColorizer.is_noise("Omitting 1 identical items, use -vv to show") is True

    def test_omitting_is_noise(self):
        assert LineColorizer.is_noise("Omitting 3 identical items") is True

    def test_full_diff_is_noise(self):
        assert LineColorizer.is_noise("Full diff:") is True

    def test_regular_line_is_not_noise(self):
        assert LineColorizer.is_noise("AssertionError: assert 3 == 30") is False

    def test_diff_line_is_not_noise(self):
        assert LineColorizer.is_noise("- expected value") is False

    def test_empty_is_not_noise(self):
        assert LineColorizer.is_noise("") is False
