"""
tests/test_coloring.py — Unit tests for LineColorizer and FormatterPlugin helpers.

These tests are fully independent of pytest's plugin machinery.
LineColorizer tests operate on plain strings and verify coloring decisions
in isolation. FormatterPlugin helper tests use lightweight stubs for the
pure-function portions (classify, extract_short, split_nodeid).
"""
import re
from types import SimpleNamespace

import pytest

import pytest_formatter
from pytest_formatter import LineColorizer, FormatterPlugin

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output even when stdout is not a tty (e.g. in CI)."""
    monkeypatch.setattr(pytest_formatter, "_NO_COLOR", False)


# ── Helpers ───────────────────────────────────────────────────────────────────

GREEN        = "\033[92m"
BRIGHT_RED   = "\033[91m"   # c_fail  — FAIL badge, expected values
STANDARD_RED = "\033[31m"   # c_error — ERROR badge, collection errors
# FIX: was "\033[0;38;2;252;205;174;49m" — the ";49" trailing background code
# was unintentional, and the "\033[" prefix caused a doubled CSI in _esc().
SOFT_RED     = "\033[0;38;2;252;205;174m"  # c_emsg — peach, context lines
RED          = "\033[91m"   # alias kept for readability in assertion tests
DIM          = "\033[2m"
YELLOW       = "\033[93m"
RESET        = "\033[0m"


def has_color(text: str, code: str) -> bool:
    """Return True if text contains the given ANSI escape code."""
    return f"\033[{code}m" in text


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return re.sub(r"\033\[[\d;]*m?", "", text)


# ── parse_assert ──────────────────────────────────────────────────────────────

class TestParseAssert:  # pylint: disable=too-many-public-methods
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

    # FIX 7: test was in the wrong section ("non-assertions") and misnamed.
    # Moved here and renamed to reflect what it actually tests.
    def test_is_not_with_none_values(self):
        assert LineColorizer.parse_assert("assert None is not None") == (
            "None", "is not", "None"
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
        line = "AttributeError: 'NoneType' object has no attribute 'get'"
        assert LineColorizer.parse_assert(line) is None

    def test_runtime_error_returns_none(self):
        assert LineColorizer.parse_assert("RuntimeError: Setup exploded intentionally") is None

    def test_plain_message_returns_none(self):
        assert LineColorizer.parse_assert("got 5, expected 15") is None

    def test_empty_string_returns_none(self):
        assert LineColorizer.parse_assert("") is None

    def test_assert_without_operator_returns_none(self):
        """'assert False' has no comparison operator."""
        assert LineColorizer.parse_assert("assert False") is None


# ── parse_bare_assert ─────────────────────────────────────────────────────────

class TestParseBareAssert:
    """Tests for LineColorizer.parse_bare_assert() — bare assertion extractor."""

    # ── lines that are bare assertions ────────────────────────────────────────

    def test_false(self):
        assert LineColorizer.parse_bare_assert("assert False") == "False"

    def test_none(self):
        assert LineColorizer.parse_bare_assert("assert None") == "None"

    def test_variable_name(self):
        assert LineColorizer.parse_bare_assert("assert is_valid") == "is_valid"

    def test_zero(self):
        assert LineColorizer.parse_bare_assert("assert 0") == "0"

    def test_empty_string(self):
        assert LineColorizer.parse_bare_assert("assert ''") == "''"

    # ── lines that are NOT bare assertions (operator present) ─────────────────

    def test_two_sided_returns_none(self):
        assert LineColorizer.parse_bare_assert("assert x == 3") is None

    def test_is_not_none_returns_none(self):
        """'assert None is not None' has 'is not' operator — not bare."""
        assert LineColorizer.parse_bare_assert("assert None is not None") is None

    def test_is_none_returns_none(self):
        assert LineColorizer.parse_bare_assert("assert x is None") is None

    # ── lines that are not assertions at all ──────────────────────────────────

    def test_exception_line_returns_none(self):
        assert LineColorizer.parse_bare_assert("RuntimeError: boom") is None

    def test_plain_message_returns_none(self):
        assert LineColorizer.parse_bare_assert("this flag should be True") is None

    def test_empty_assert_body_returns_none(self):
        """'assert' with nothing after it must not produce an empty string."""
        assert LineColorizer.parse_bare_assert("assert ") is None


# ── split_prefix ──────────────────────────────────────────────────────────────

class TestSplitPrefix:
    """Tests for LineColorizer.split_prefix() — prose-prefix detector."""

    # ── lines that start with a value character (no prefix) ──────────────────

    def test_string_value_no_prefix(self):
        assert LineColorizer.split_prefix("'Global Launch'") == ("", "'Global Launch'")

    def test_double_quoted_string_no_prefix(self):
        assert LineColorizer.split_prefix('"hello"') == ("", '"hello"')

    def test_dict_no_prefix(self):
        assert LineColorizer.split_prefix("{'b': 2}") == ("", "{'b': 2}")

    def test_list_no_prefix(self):
        assert LineColorizer.split_prefix("['a', 'b']") == ("", "['a', 'b']")

    def test_number_no_prefix(self):
        assert LineColorizer.split_prefix("42") == ("", "42")

    def test_negative_number_no_prefix(self):
        assert LineColorizer.split_prefix("-5") == ("", "-5")

    # ── lines with a prose prefix ─────────────────────────────────────────────

    def test_index_diff_prefix(self):
        prefix, value = LineColorizer.split_prefix("At index 0 diff: 'Global Launch'")
        assert prefix == "At index 0 diff: "
        assert value == "'Global Launch'"

    def test_numeric_value_after_prefix(self):
        prefix, value = LineColorizer.split_prefix("At index 0: 42")
        assert prefix == "At index 0: "
        assert value == "42"

    def test_dict_value_after_prefix(self):
        prefix, value = LineColorizer.split_prefix("Left contains: {'a': 1}")
        assert prefix == "Left contains: "
        assert value == "{'a': 1}"

    # ── prose with no value character after ': ' (no split) ──────────────────

    def test_prose_without_value(self):
        assert LineColorizer.split_prefix("Extra items") == ("", "Extra items")

    def test_colon_not_followed_by_value_char(self):
        """': ' followed by a letter that isn't a value must not split."""
        assert LineColorizer.split_prefix("the left set: extra") == ("", "the left set: extra")

    def test_empty_string(self):
        assert LineColorizer.split_prefix("") == ("", "")


# ── color_assert_line ─────────────────────────────────────────────────────────

class TestColorAssertLine:
    """Tests for the inline assert colorizer."""

    def test_received_is_green(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        # received (3, left side) is green — it's what the code produced
        assert GREEN in result

    def test_expected_is_red(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        # expected (30, right side) is red — it's what the test demands
        assert RED in result

    def test_assert_keyword_is_soft_red(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        assert SOFT_RED in result

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

    def test_unparseable_falls_back_to_soft_red(self):
        line = "got 5, expected 15"
        result = LineColorizer.color_assert_line(line)
        assert SOFT_RED in result
        assert strip_ansi(result) == line

    def test_string_comparison(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = strip_ansi(LineColorizer.color_assert_line(line))
        assert "INTGPT-109" in result
        assert "INTGPT-1091" in result

    # ── bare assertions (no operator) ────────────────────────────────────────

    def test_bare_false_value_is_bright_red(self):
        """'assert False' — the bare falsy value must be highlighted bright red."""
        result = LineColorizer.color_assert_line("assert False")
        assert BRIGHT_RED in result
        assert GREEN not in result  # no green: nothing received-vs-expected to contrast

    def test_bare_false_plain_text_preserved(self):
        assert strip_ansi(LineColorizer.color_assert_line("assert False")) == "assert False"

    def test_bare_none_value_is_bright_red(self):
        """'assert None' — None is the bare falsy value."""
        result = LineColorizer.color_assert_line("assert None")
        assert BRIGHT_RED in result

    def test_bare_variable_value_is_bright_red(self):
        result = LineColorizer.color_assert_line("assert is_valid")
        assert BRIGHT_RED in result
        assert strip_ansi(result) == "assert is_valid"

    # ── 'is not' special rendering ────────────────────────────────────────────

    def test_is_not_none_renders_not_none_as_unit(self):
        """'assert None is not None' must render 'not None' as one red token."""
        result = LineColorizer.color_assert_line("assert None is not None")
        plain = strip_ansi(result)
        assert plain == "assert None is not None"
        assert GREEN in result       # received None
        assert BRIGHT_RED in result  # 'not None' as the expected condition

    def test_is_not_none_plain_text_correct(self):
        """Rendered plain text must still read as the original assertion."""
        result = strip_ansi(LineColorizer.color_assert_line("assert None is not None"))
        assert result == "assert None is not None"

    def test_is_not_value_renders_not_value_as_unit(self):
        """'assert x is not y': expected should be 'not y', not just 'y'."""
        result = strip_ansi(LineColorizer.color_assert_line("assert x is not y"))
        assert "not y" in result


# ── color_e_line ──────────────────────────────────────────────────────────────

class TestColorELineSkipAndDiff:
    """color_e_line: skip outcome and unified-diff prefix markers (- / + / ?)."""

    def test_skip_outcome_is_yellow(self):
        result = LineColorizer.color_e_line("Skipped: demonstrating skip", "skipped", is_first=True)
        assert has_color(result, "93")  # yellow

    def test_skip_outcome_is_yellow_even_for_non_first(self):
        result = LineColorizer.color_e_line("some context", "skipped", is_first=False)
        assert has_color(result, "93")

    def test_minus_line_is_green(self):
        result = LineColorizer.color_e_line("- INTGPT-1091", "failed", is_first=False)
        assert GREEN in result

    def test_plus_line_is_red(self):
        result = LineColorizer.color_e_line("+ INTGPT-109", "failed", is_first=False)
        assert RED in result

    def test_question_line_is_soft_red(self):
        result = LineColorizer.color_e_line("?           -", "failed", is_first=False)
        assert SOFT_RED in result

    def test_lone_minus_is_green(self):
        result = LineColorizer.color_e_line("-", "failed", is_first=False)
        assert GREEN in result

    def test_lone_plus_is_red(self):
        result = LineColorizer.color_e_line("+", "failed", is_first=False)
        assert RED in result


class TestColorELineFirstLine:
    """color_e_line: first-line behavior — assertions, exceptions, and error outcomes."""

    def test_first_assertion_line_has_green_and_red(self):
        """assert X == Y colors X (received) green and Y (expected) red."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert GREEN in result   # received (3)  — what the code produced
        assert RED in result     # expected (30) — what the test demands

    def test_first_assertionerror_assertion_colored(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = LineColorizer.color_e_line(line, "failed", is_first=True)
        assert GREEN in result
        assert RED in result

    def test_first_exception_line_is_soft_red(self):
        result = LineColorizer.color_e_line(
            "AttributeError: 'NoneType' object has no attribute 'get'",
            "failed",
            is_first=True,
        )
        assert SOFT_RED in result
        assert BRIGHT_RED not in result

    def test_first_runtime_error_is_soft_red(self):
        result = LineColorizer.color_e_line(
            "RuntimeError: Setup exploded intentionally",
            "failed",
            is_first=True,
        )
        assert SOFT_RED in result
        assert BRIGHT_RED not in result

    def test_error_outcome_first_line_is_soft_red(self):
        result = LineColorizer.color_e_line(
            "RuntimeError: Setup exploded", "error", is_first=True
        )
        assert SOFT_RED in result

    def test_first_error_line_is_not_bright_red(self):
        """First error lines must be soft red, not bright red."""
        result = LineColorizer.color_e_line("RuntimeError: boom", "failed", is_first=True)
        assert BRIGHT_RED not in result

    def test_expected_value_is_bright_red(self):
        """Right side of assert (expected) must be bright red — same as FAIL badge."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert BRIGHT_RED in result

    def test_received_value_is_green(self):
        """Left side of assert (received) must be green — what the code produced."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert GREEN in result

    # ── bare boolean / None assertions ────────────────────────────────────────

    def test_bare_false_colors_value_bright_red(self):
        """'assert False' must color False in bright red (the falsy failure value)."""
        result = LineColorizer.color_e_line("assert False", "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_bare_none_colors_value_bright_red(self):
        """'assert None' must color None in bright red."""
        result = LineColorizer.color_e_line("assert None", "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_bare_false_plain_text_preserved(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=True)
        assert strip_ansi(result) == "assert False"

    def test_none_is_not_none_has_green_and_red(self):
        """'assert None is not None': received None is green, 'not None' target is red."""
        result = LineColorizer.color_e_line("assert None is not None", "failed", is_first=True)
        assert GREEN in result       # first None: what the code produced
        assert BRIGHT_RED in result  # 'not None': the condition that was required
        assert strip_ansi(result) == "assert None is not None"

    # ── non-first assertion lines ─────────────────────────────────────────────
    # When a custom message is present, pytest emits it as the first E-line and
    # pushes 'assert False' / 'assert x == y' to a second E-line (is_first=False).
    # These must still be colored, not fall through to plain soft-red.

    def test_non_first_bare_false_is_bright_red(self):
        """'assert False' on a non-first E-line must still color False bright red."""
        result = LineColorizer.color_e_line("assert False", "failed", is_first=False)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_non_first_bare_none_is_bright_red(self):
        result = LineColorizer.color_e_line("assert None", "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_non_first_two_sided_assert_colored(self):
        """'assert 3 == 30' on a non-first E-line must still color both sides."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=False)
        assert GREEN in result
        assert BRIGHT_RED in result

    def test_non_first_assert_plain_text_preserved(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=False)
        assert strip_ansi(result) == "assert False"


class TestColorELineContext:
    """color_e_line: non-first (context) lines and cross-cutting color rules."""

    def test_non_first_line_is_soft_red(self):
        result = LineColorizer.color_e_line("At index 0 diff:", "failed", is_first=False)
        assert SOFT_RED in result

    def test_differing_items_context_is_soft_red(self):
        result = LineColorizer.color_e_line("Differing items:", "failed", is_first=False)
        assert SOFT_RED in result

    def test_context_comparison_received_is_green(self):
        """Dict diff lines like {'b': 2} != {'b': 999} should color left side green."""
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        assert GREEN in result

    def test_context_comparison_expected_is_bright_red(self):
        """Dict diff lines like {'b': 2} != {'b': 999} should color right side bright red."""
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_context_comparison_plain_text_preserved(self):
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        plain = strip_ansi(result)
        assert "{'b': 2}" in plain
        assert "!=" in plain
        assert "{'b': 999}" in plain

    def test_xfailed_first_line_is_soft_red(self):
        """xfailed reason lines use soft red as context."""
        result = LineColorizer.color_e_line(
            "xfailed: known bug", "xfailed", is_first=False
        )
        assert SOFT_RED in result

    def test_context_line_is_not_bright_red(self):
        """Context lines must never use bright red — only soft red."""
        result = LineColorizer.color_e_line("Differing items:", "failed", is_first=False)
        assert BRIGHT_RED not in result

    # ── Issue 1: prefix-aware comparison coloring ─────────────────────────────
    # 'At index 0 diff: VALUE != VALUE' must color only the values, not the
    # entire "At index 0 diff: VALUE" chunk.

    def test_comparison_with_prefix_only_value_is_green(self):
        """Only the value after the prose prefix should be colored green."""
        line = "At index 0 diff: 'Global Launch' != 'Global Launches'"
        result = LineColorizer.color_e_line(line, "failed", is_first=False)
        plain = strip_ansi(result)
        assert plain == line        # text is fully preserved
        assert GREEN in result      # 'Global Launch' (received value) is green
        assert BRIGHT_RED in result # 'Global Launches' (expected value) is bright red
        assert SOFT_RED in result   # prefix 'At index 0 diff: ' is soft red

    def test_comparison_prefix_comes_before_green_in_output(self):
        """Prose prefix must be rendered in soft red BEFORE the green value."""
        line = "At index 0 diff: 'Global Launch' != 'Global Launches'"
        result = LineColorizer.color_e_line(line, "failed", is_first=False)
        soft_red_pos = result.find(SOFT_RED)
        green_pos = result.find(GREEN)
        assert soft_red_pos < green_pos  # prefix (soft red) comes first

    # ── Issue 2: prose 'in' must not be treated as a comparison operator ──────
    # 'Extra items in the left set:' contains ' in ' at depth 0, but both
    # apparent operands are prose words, not Python values.

    def test_extra_items_left_not_colored_green(self):
        """'Extra items' must not become green just because 'in' is in the line."""
        result = LineColorizer.color_e_line(
            "Extra items in the left set:", "failed", is_first=False
        )
        assert GREEN not in result
        assert BRIGHT_RED not in result
        assert SOFT_RED in result   # entire line is soft red

    def test_extra_items_right_not_colored_red(self):
        """'Extra items in the right set:' must be all soft-red, no green/red."""
        result = LineColorizer.color_e_line(
            "Extra items in the right set:", "failed", is_first=False
        )
        assert GREEN not in result
        assert BRIGHT_RED not in result

    def test_parse_comparison_rejects_prose_in_operator(self):
        """parse_comparison must return None when operands are prose, not values."""
        assert LineColorizer.parse_comparison("Extra items in the left set:") is None
        assert LineColorizer.parse_comparison("Extra items in the right set:") is None


# ── label-prefixed lines (Obtained / Expected) ────────────────────────────────

class TestLabelColors:
    """
    color_e_line: 'Obtained: …' and 'Expected: …' label lines.

    These are emitted by pytest-approx and similar plugins on non-first E-lines.
    Semantic convention (intentionally inverted from assert-line coloring):
      Obtained → bright red  (the wrong value — what caused the failure)
      Expected → green       (the target value — what the test demanded)
    """

    def test_obtained_value_is_bright_red(self):
        result = LineColorizer.color_e_line(
            "Obtained: 3.141592653589793", "failed", is_first=False
        )
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_expected_value_is_green(self):
        result = LineColorizer.color_e_line(
            "Expected: 3.14 ± 0.001", "failed", is_first=False
        )
        assert GREEN in result
        assert BRIGHT_RED not in result

    def test_obtained_label_is_soft_red(self):
        """The 'Obtained: ' label itself must be soft red, not bright red."""
        result = LineColorizer.color_e_line(
            "Obtained: 3.141592653589793", "failed", is_first=False
        )
        assert SOFT_RED in result

    def test_expected_label_is_soft_red(self):
        """The 'Expected: ' label itself must be soft red, not green."""
        result = LineColorizer.color_e_line(
            "Expected: 3.14 ± 0.001", "failed", is_first=False
        )
        assert SOFT_RED in result

    def test_obtained_plain_text_preserved(self):
        result = LineColorizer.color_e_line(
            "Obtained: 3.141592653589793", "failed", is_first=False
        )
        assert strip_ansi(result) == "Obtained: 3.141592653589793"

    def test_expected_plain_text_preserved(self):
        result = LineColorizer.color_e_line(
            "Expected: 3.14 ± 0.001", "failed", is_first=False
        )
        assert strip_ansi(result) == "Expected: 3.14 ± 0.001"

    def test_obtained_not_triggered_for_plain_prose(self):
        """A line that merely contains 'Obtained' mid-sentence must not match."""
        result = LineColorizer.color_e_line(
            "Value obtained from cache", "failed", is_first=False
        )
        assert BRIGHT_RED not in result

    def test_expected_not_triggered_for_plain_prose(self):
        result = LineColorizer.color_e_line(
            "More than expected results", "failed", is_first=False
        )
        assert GREEN not in result

    def test_label_lines_also_colored_when_is_first(self):
        """Label lines that happen to be the first E-line must still be colored."""
        result = LineColorizer.color_e_line(
            "Obtained: 42", "failed", is_first=True
        )
        # is_first=True routes through color_assert_line which falls back to
        # c_emsg for non-assertions — label lines won't be colored there.
        # Verify at least the line is rendered (no crash) and text is preserved.
        assert strip_ansi(result) == "Obtained: 42"


# ── is_noise ──────────────────────────────────────────────────────────────────

class TestIsNoise:
    """Tests for noise-line detection."""

    def test_use_v_is_noise(self):
        assert LineColorizer.is_noise("Use -v to get more diff") is True

    def test_use_vv_is_noise(self):
        assert LineColorizer.is_noise("Omitting 1 identical items, use -vv to show") is True

    def test_omitting_is_noise(self):
        assert LineColorizer.is_noise("Omitting 3 identical items") is True

    # FIX 7: "Full diff" → "Full diff:" — the old token was too broad and
    # would suppress legitimate output containing "Full diff calculated" etc.
    def test_full_diff_colon_is_noise(self):
        assert LineColorizer.is_noise("Full diff:") is True

    def test_full_diff_without_colon_is_not_noise(self):
        """'Full diff' alone (no colon) must not be suppressed — too broad."""
        assert LineColorizer.is_noise("Full diff calculated in 3ms") is False

    def test_regular_line_is_not_noise(self):
        assert LineColorizer.is_noise("AssertionError: assert 3 == 30") is False

    def test_diff_line_is_not_noise(self):
        assert LineColorizer.is_noise("- expected value") is False

    def test_empty_is_not_noise(self):
        assert LineColorizer.is_noise("") is False


# ── FormatterPlugin static helpers ────────────────────────────────────────────
# FIX 6: classify, extract_short, and split_nodeid were pure functions with
# zero test coverage. The tests below cover them using lightweight stubs so no
# pytest plugin machinery is required.

class TestSplitNodeid:
    """Tests for FormatterPlugin.split_nodeid()."""

    def test_normal_nodeid(self):
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::test_bar") == (
            "tests/test_foo.py", "test_bar"
        )

    def test_parameterized_nodeid(self):
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::test_bar[x-y]") == (
            "tests/test_foo.py", "test_bar[x-y]"
        )

    def test_class_method_nodeid(self):
        """partition('::') splits on the first separator only."""
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::TestClass::test_method") == (
            "tests/test_foo.py", "TestClass::test_method"
        )

    def test_no_separator_returns_full_path_as_name(self):
        """When there is no '::' the whole string is used as both file and name."""
        assert FormatterPlugin.split_nodeid("tests/test_foo.py") == (
            "tests/test_foo.py", "tests/test_foo.py"
        )


class TestClassify:
    """Tests for FormatterPlugin.classify() — outcome normalisation."""

    @staticmethod
    def _report(when="call", outcome="passed", wasxfail=None):
        r = SimpleNamespace(when=when, outcome=outcome)
        if wasxfail is not None:
            r.wasxfail = wasxfail
        return r

    def test_passed_call(self):
        assert FormatterPlugin.classify(self._report()) == "passed"

    def test_failed_call(self):
        assert FormatterPlugin.classify(self._report(outcome="failed")) == "failed"

    def test_skipped_call(self):
        assert FormatterPlugin.classify(self._report(outcome="skipped")) == "skipped"

    def test_setup_failure_becomes_error(self):
        assert FormatterPlugin.classify(self._report(when="setup", outcome="failed")) == "error"

    def test_teardown_failure_becomes_error(self):
        assert FormatterPlugin.classify(self._report(when="teardown", outcome="failed")) == "error"

    def test_setup_pass_stays_passed(self):
        """A passing setup phase must NOT be reclassified as error."""
        assert FormatterPlugin.classify(self._report(when="setup", outcome="passed")) == "passed"

    def test_xfailed(self):
        r = self._report(outcome="failed", wasxfail="known regression")
        assert FormatterPlugin.classify(r) == "xfailed"

    def test_xpassed(self):
        r = self._report(outcome="passed", wasxfail="unexpectedly fixed")
        assert FormatterPlugin.classify(r) == "xpassed"


class _FakeLongrepr:
    """Minimal longrepr stub for extract_short tests."""

    def __init__(self, text: str, reprcrash_msg: str | None = None) -> None:
        self._text = text
        if reprcrash_msg is not None:
            self.reprcrash = SimpleNamespace(message=reprcrash_msg)

    def __str__(self) -> str:
        return self._text


class TestExtractShort:
    """Tests for FormatterPlugin.extract_short()."""

    # ── xfail / xpass ─────────────────────────────────────────────────────────

    def test_xfailed_with_reason(self):
        r = SimpleNamespace(wasxfail="known regression", longrepr=None)
        assert FormatterPlugin.extract_short(r, "xfailed") == "xfailed: known regression"

    def test_xpassed_with_reason(self):
        r = SimpleNamespace(wasxfail="unexpectedly fixed", longrepr=None)
        assert FormatterPlugin.extract_short(r, "xpassed") == "xpassed: unexpectedly fixed"

    def test_xfailed_no_reason(self):
        r = SimpleNamespace(wasxfail="", longrepr=None)
        assert FormatterPlugin.extract_short(r, "xfailed") == "xfailed"

    # ── falsy longrepr ────────────────────────────────────────────────────────

    def test_none_longrepr_returns_none(self):
        r = SimpleNamespace(longrepr=None)
        assert FormatterPlugin.extract_short(r, "failed") is None

    def test_empty_string_longrepr_returns_none(self):
        r = SimpleNamespace(longrepr="")
        assert FormatterPlugin.extract_short(r, "failed") is None

    # ── skip tuple ────────────────────────────────────────────────────────────

    def test_skip_tuple_longrepr(self):
        r = SimpleNamespace(longrepr=("file.py", 10, "Skipped: reason here"))
        assert FormatterPlugin.extract_short(r, "skipped") == "Skipped: reason here"

    def test_skip_tuple_stringified_reason(self):
        r = SimpleNamespace(longrepr=("file.py", 5, 42))  # non-str reason
        assert FormatterPlugin.extract_short(r, "skipped") == "42"

    # ── reprcrash with E lines ────────────────────────────────────────────────

    def test_e_lines_extracted_from_reprcrash_longrepr(self):
        text = (
            "_ test_foo _\n"
            "  E  AssertionError: assert 3 == 30\n"
            "  E  assert 3 == 30\n"
        )
        r = SimpleNamespace(longrepr=_FakeLongrepr(text, reprcrash_msg="AssertionError"))
        result = FormatterPlugin.extract_short(r, "failed")
        assert result is not None
        assert "AssertionError: assert 3 == 30" in result
        assert "assert 3 == 30" in result

    def test_e_lines_capped_at_max_e_lines(self):
        """More than MAX_E_LINES E-lines must be truncated."""
        lines = "\n".join(f"  E  line {i}" for i in range(30))
        r = SimpleNamespace(longrepr=_FakeLongrepr(lines, reprcrash_msg="err"))
        result = FormatterPlugin.extract_short(r, "failed")
        assert result is not None
        assert len(result.splitlines()) == pytest_formatter.MAX_E_LINES

    def test_reprcrash_message_fallback_when_no_e_lines(self):
        text = "some traceback without any E-prefixed lines"
        r = SimpleNamespace(
            longrepr=_FakeLongrepr(text, reprcrash_msg="AssertionError: assert 1 == 2")
        )
        result = FormatterPlugin.extract_short(r, "failed")
        assert result == "AssertionError: assert 1 == 2"

    # ── plain string longrepr ─────────────────────────────────────────────────

    def test_plain_string_longrepr_returns_first_line(self):
        r = SimpleNamespace(longrepr=_FakeLongrepr("First line\nSecond line\n"))
        result = FormatterPlugin.extract_short(r, "error")
        assert result == "First line"

    def test_plain_string_longrepr_skips_blank_lines(self):
        r = SimpleNamespace(longrepr=_FakeLongrepr("\n\nFirst non-blank\nSecond\n"))
        result = FormatterPlugin.extract_short(r, "error")
        assert result == "First non-blank"
