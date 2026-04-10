# tests/test_parsers.py
"""
Unit tests for all pure-parsing methods in LineColorizer.

These tests operate on plain Python strings and return plain Python objects
(tuples, strings, bools, None).  No ANSI escape codes are produced or
checked here — that belongs in test_colorizer.py.

Coverage:
  parse_assert        — operator-aware assertion splitter
  parse_bare_assert   — bare 'assert VALUE' extractor
  split_prefix        — prose-prefix / value-body separator
  parse_approx_table_row — pipe-delimited approx table row detector
  is_noise            — noise-line suppression filter
"""
from pytest_formatter import LineColorizer


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

    def test_is_not_with_none_values(self):
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
        result = LineColorizer.parse_assert("assert 'a == b' == 'a == c'")
        assert result == ("'a == b'", "==", "'a == c'")

    def test_operator_inside_dict_key_not_matched(self):
        """Operators inside containers must not be matched at depth > 0."""
        result = LineColorizer.parse_assert("assert {'x == y': 1} == {'x == y': 2}")
        assert result == ("{'x == y': 1}", "==", "{'x == y': 2}")

    def test_nested_containers(self):
        result = LineColorizer.parse_assert("assert [{'a': [1, 2]}] == [{'a': [1, 3]}]")
        assert result == ("[{'a': [1, 2]}]", "==", "[{'a': [1, 3]}]")

    # ── non-assertions ────────────────────────────────────────────────────────

    def test_exception_line_returns_none(self):
        assert LineColorizer.parse_assert(
            "AttributeError: 'NoneType' object has no attribute 'get'"
        ) is None

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


# ── parse_approx_table_row ────────────────────────────────────────────────────

class TestParseApproxTableRow:
    """Tests for LineColorizer.parse_approx_table_row() — pipe-table detector."""

    def test_parse_int_index_row(self):
        row = "0     | 0.30000000000000004 | 0.4 ± 1.0e-09"
        result = LineColorizer.parse_approx_table_row(row)
        assert result is not None
        _, obt, exp = result
        assert obt.strip() == "0.30000000000000004"
        assert exp.strip() == "0.4 ± 1.0e-09"

    def test_parse_str_index_row(self):
        row = "x     | 1.0                 | 2.0 ± 1.0e-09"
        result = LineColorizer.parse_approx_table_row(row)
        assert result is not None
        _, obt, exp = result
        assert obt.strip() == "1.0"
        assert exp.strip() == "2.0 ± 1.0e-09"

    def test_parse_negative_obtained(self):
        """Negative obtained value must still be recognised as a data row."""
        row = "0     | -1.5                | 0.0 ± 1.0e-09"
        assert LineColorizer.parse_approx_table_row(row) is not None

    def test_header_row_returns_none(self):
        """'Index | Obtained | Expected' is the header — must not be parsed as data."""
        assert LineColorizer.parse_approx_table_row("Index | Obtained            | Expected") is None

    def test_non_table_line_returns_none(self):
        assert LineColorizer.parse_approx_table_row("comparison failed") is None
        assert LineColorizer.parse_approx_table_row("Max absolute difference: 0.1") is None
        assert LineColorizer.parse_approx_table_row("assert 1.0 == 2.0 ± 0.02") is None

    def test_wrong_pipe_count_returns_none(self):
        assert LineColorizer.parse_approx_table_row("a | b") is None          # 1 pipe
        assert LineColorizer.parse_approx_table_row("a | b | c | d") is None  # 3 pipes


# ── is_noise ──────────────────────────────────────────────────────────────────

class TestIsNoise:
    """Tests for noise-line detection."""

    def test_use_v_is_noise(self):
        assert LineColorizer.is_noise("Use -v to get more diff") is True

    def test_use_vv_is_noise(self):
        assert LineColorizer.is_noise("Omitting 1 identical items, use -vv to show") is True

    def test_omitting_is_noise(self):
        assert LineColorizer.is_noise("Omitting 3 identical items") is True

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


# ── parse_comparison (tested indirectly — regression guards) ──────────────────

class TestParseComparisonRejects:
    """Guards against false operator matches in prose lines.
    parse_comparison is tested more thoroughly via color_e_line in test_colorizer.py;
    these tests cover the value-gate logic in isolation."""

    def test_rejects_prose_in_operator(self):
        """'Extra items in the left set:' must not match — 'in' is prose, not a value."""
        assert LineColorizer.parse_comparison("Extra items in the left set:") is None
        assert LineColorizer.parse_comparison("Extra items in the right set:") is None

    def test_accepts_value_comparison(self):
        """{'b': 2} != {'b': 999} is a real comparison and must parse."""
        result = LineColorizer.parse_comparison("{'b': 2} != {'b': 999}")
        assert result is not None
        received, op, expected = result
        assert op == "!="
        assert "{'b': 2}" in received
        assert "{'b': 999}" in expected
