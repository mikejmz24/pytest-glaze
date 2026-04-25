# tests/test_colorizer.py
"""
Unit tests for all coloring methods in LineColorizer.

These tests produce and inspect ANSI escape sequences.  The force_color
fixture in conftest.py patches _NO_COLOR=False so colors are always emitted
regardless of terminal detection.

Coverage:
  color_assert_line   — two-sided, bare, and 'is not' assertions
  color_e_line        — every dispatch branch: skip, diff, first-line,
                        context comparisons, label lines, approx table rows
"""
from pytest_glaze import LineColorizer
from tests.helpers import GREEN, BRIGHT_RED, SOFT_PEACH, strip_ansi


def has_color(text: str, code: str) -> bool:
    """Return True if text contains the given ANSI escape code (by number)."""
    return f"\033[{code}m" in text

# ── color_assert_line ─────────────────────────────────────────────────────────

class TestColorAssertLine:
    """Tests for the inline assert colorizer.

    Color convention (consistent across all line types):
      received value → bright red  (the wrong value)
      expected value → green       (the target value)
    """

    def test_received_is_red(self):
        """Received value (left of ==) must be bright red — the wrong value."""
        result = LineColorizer.color_assert_line("assert 3 == 30")
        assert BRIGHT_RED in result

    def test_expected_is_green(self):
        """Expected value (right of ==) must be green — the target value."""
        result = LineColorizer.color_assert_line("assert 3 == 30")
        assert GREEN in result

    def test_assert_keyword_is_soft_peach(self):
        result = LineColorizer.color_assert_line("assert 3 == 30")
        assert SOFT_PEACH in result

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

    def test_unparseable_falls_back_to_soft_peach(self):
        line = "got 5, expected 15"
        result = LineColorizer.color_assert_line(line)
        assert SOFT_PEACH in result
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
        assert GREEN not in result

    def test_bare_false_plain_text_preserved(self):
        assert strip_ansi(LineColorizer.color_assert_line("assert False")) == "assert False"

    def test_bare_none_value_is_bright_red(self):
        result = LineColorizer.color_assert_line("assert None")
        assert BRIGHT_RED in result

    def test_bare_variable_value_is_bright_red(self):
        result = LineColorizer.color_assert_line("assert is_valid")
        assert BRIGHT_RED in result
        assert strip_ansi(result) == "assert is_valid"

    # ── 'is not' special rendering ────────────────────────────────────────────

    def test_is_not_none_renders_not_none_as_unit(self):
        """'assert None is not None': received None is red, 'not None' is green."""
        result = LineColorizer.color_assert_line("assert None is not None")
        plain = strip_ansi(result)
        assert plain == "assert None is not None"
        assert BRIGHT_RED in result  # received None — the wrong value
        assert GREEN in result       # 'not None'   — the target condition

    def test_is_not_none_plain_text_correct(self):
        result = strip_ansi(LineColorizer.color_assert_line("assert None is not None"))
        assert result == "assert None is not None"

    def test_is_not_value_renders_not_value_as_unit(self):
        """'assert x is not y': expected must render as 'not y' in green."""
        result = strip_ansi(LineColorizer.color_assert_line("assert x is not y"))
        assert "not y" in result


# ── color_e_line: skip and diff markers ───────────────────────────────────────

class TestColorELineSkipAndDiff:
    """color_e_line: skip outcome and unified-diff prefix markers (- / + / ?)."""

    def test_skip_outcome_is_yellow(self):
        result = LineColorizer.color_e_line("Skipped: demonstrating skip", "skipped", is_first=True)
        assert has_color(result, "93")

    def test_skip_outcome_is_yellow_even_for_non_first(self):
        result = LineColorizer.color_e_line("some context", "skipped", is_first=False)
        assert has_color(result, "93")

    def test_minus_line_is_green(self):
        """'-' lines carry expected content — must be green."""
        result = LineColorizer.color_e_line("- INTGPT-1091", "failed", is_first=False)
        assert GREEN in result

    def test_plus_line_is_bright_red(self):
        """'+' lines carry received content — must be red."""
        result = LineColorizer.color_e_line("+ INTGPT-109", "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_question_line_is_soft_peach(self):
        result = LineColorizer.color_e_line("?           -", "failed", is_first=False)
        assert SOFT_PEACH in result

    def test_lone_minus_is_green(self):
        result = LineColorizer.color_e_line("-", "failed", is_first=False)
        assert GREEN in result

    def test_lone_plus_is_bright_red(self):
        result = LineColorizer.color_e_line("+", "failed", is_first=False)
        assert BRIGHT_RED in result


# ── color_e_line: first-line behavior ────────────────────────────────────────

class TestColorELineFirstLine:
    """color_e_line: first-line behavior — assertions, exceptions, and error outcomes."""

    def test_first_assertion_line_has_green_and_red(self):
        """assert X == Y: received (X) is red, expected (Y) is green."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert BRIGHT_RED in result  # received 3  — the wrong value
        assert GREEN in result       # expected 30 — the target value

    def test_first_assertionerror_assertion_colored(self):
        line = "AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'"
        result = LineColorizer.color_e_line(line, "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN in result

    def test_first_exception_line_is_soft_peach(self):
        result = LineColorizer.color_e_line(
            "AttributeError: 'NoneType' object has no attribute 'get'",
            "failed", is_first=True,
        )
        assert SOFT_PEACH in result
        assert BRIGHT_RED not in result

    def test_first_runtime_error_is_soft_peach(self):
        result = LineColorizer.color_e_line(
            "RuntimeError: Setup exploded intentionally", "failed", is_first=True,
        )
        assert SOFT_PEACH in result
        assert BRIGHT_RED not in result

    def test_error_outcome_first_line_is_soft_peach(self):
        result = LineColorizer.color_e_line("RuntimeError: Setup exploded", "error", is_first=True)
        assert SOFT_PEACH in result

    def test_first_error_line_is_not_bright_red(self):
        """Exception first-lines must be soft red, never bright red."""
        result = LineColorizer.color_e_line("RuntimeError: boom", "failed", is_first=True)
        assert BRIGHT_RED not in result

    def test_received_value_is_bright_red(self):
        """Left side of assert (received) must be bright red — the wrong value."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert BRIGHT_RED in result

    def test_expected_value_is_green(self):
        """Right side of assert (expected) must be green — the target value."""
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=True)
        assert GREEN in result

    # ── bare boolean / None assertions ────────────────────────────────────────

    def test_bare_false_colors_value_bright_red(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_bare_none_colors_value_bright_red(self):
        result = LineColorizer.color_e_line("assert None", "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_bare_false_plain_text_preserved(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=True)
        assert strip_ansi(result) == "assert False"

    def test_none_is_not_none_has_green_and_red(self):
        """'assert None is not None': received None is red, 'not None' target is green."""
        result = LineColorizer.color_e_line("assert None is not None", "failed", is_first=True)
        assert BRIGHT_RED in result
        assert GREEN in result
        assert strip_ansi(result) == "assert None is not None"

    # ── non-first assertion lines ─────────────────────────────────────────────
    # When a custom message is present, pytest emits it first and pushes
    # 'assert VALUE' to a second E-line (is_first=False). These must still
    # be colored, not fall through to plain soft-red.

    def test_non_first_bare_false_is_bright_red(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=False)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_non_first_bare_none_is_bright_red(self):
        result = LineColorizer.color_e_line("assert None", "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_non_first_two_sided_assert_colored(self):
        result = LineColorizer.color_e_line("assert 3 == 30", "failed", is_first=False)
        assert GREEN in result
        assert BRIGHT_RED in result

    def test_non_first_assert_plain_text_preserved(self):
        result = LineColorizer.color_e_line("assert False", "failed", is_first=False)
        assert strip_ansi(result) == "assert False"


# ── color_e_line: context (non-first) lines ───────────────────────────────────

class TestColorELineContext:
    """color_e_line: non-first (context) lines and cross-cutting color rules."""

    def test_non_first_line_is_soft_peach(self):
        result = LineColorizer.color_e_line("At index 0 diff:", "failed", is_first=False)
        assert SOFT_PEACH in result

    def test_differing_items_context_is_soft_peach(self):
        result = LineColorizer.color_e_line("Differing items:", "failed", is_first=False)
        assert SOFT_PEACH in result

    def test_context_comparison_received_is_bright_red(self):
        """Dict diff: {'b': 2} != {'b': 999} — received (left) is bright red."""
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_context_comparison_expected_is_green(self):
        """Dict diff: {'b': 2} != {'b': 999} — expected (right) is green."""
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        assert GREEN in result

    def test_context_comparison_plain_text_preserved(self):
        result = LineColorizer.color_e_line("{'b': 2} != {'b': 999}", "failed", is_first=False)
        plain = strip_ansi(result)
        assert "{'b': 2}" in plain
        assert "!=" in plain
        assert "{'b': 999}" in plain

    def test_xfailed_first_line_is_soft_peach(self):
        result = LineColorizer.color_e_line("xfailed: known bug", "xfailed", is_first=False)
        assert SOFT_PEACH in result

    def test_context_line_is_not_bright_red(self):
        """Prose context lines must never use bright red."""
        result = LineColorizer.color_e_line("Differing items:", "failed", is_first=False)
        assert BRIGHT_RED not in result

    def test_comparison_with_prefix_only_value_is_red(self):
        """Only the value after the prose prefix should be colored red (received)."""
        line = "At index 0 diff: 'Global Launch' != 'Global Launches'"
        result = LineColorizer.color_e_line(line, "failed", is_first=False)
        assert strip_ansi(result) == line
        assert BRIGHT_RED in result  # 'Global Launch' (received) is red
        assert GREEN in result       # 'Global Launches' (expected) is green
        assert SOFT_PEACH in result    # prefix 'At index 0 diff: ' is soft red

    def test_comparison_prefix_comes_before_red_in_output(self):
        """Prose prefix (soft red) must appear before the received value (bright red)."""
        line = "At index 0 diff: 'Global Launch' != 'Global Launches'"
        result = LineColorizer.color_e_line(line, "failed", is_first=False)
        assert result.find(SOFT_PEACH) < result.find(BRIGHT_RED)

    def test_extra_items_left_not_colored(self):
        """'Extra items in the left set:' — prose 'in' must not trigger comparison."""
        result = LineColorizer.color_e_line(
            "Extra items in the left set:", "failed", is_first=False
        )
        assert GREEN not in result
        assert BRIGHT_RED not in result
        assert SOFT_PEACH in result

    def test_extra_items_right_not_colored(self):
        result = LineColorizer.color_e_line(
            "Extra items in the right set:", "failed", is_first=False
        )
        assert GREEN not in result
        assert BRIGHT_RED not in result


# ── color_e_line: Obtained / Expected label lines ─────────────────────────────

class TestLabelColors:
    """color_e_line: 'Obtained: …' and 'Expected: …' label lines from pytest-approx."""

    def test_obtained_value_is_bright_red(self):
        result = LineColorizer.color_e_line("Obtained: 3.141592653589793", "failed", is_first=False)
        assert BRIGHT_RED in result
        assert GREEN not in result

    def test_expected_value_is_green(self):
        result = LineColorizer.color_e_line("Expected: 3.14 ± 0.001", "failed", is_first=False)
        assert GREEN in result
        assert BRIGHT_RED not in result

    def test_obtained_label_is_soft_peach(self):
        """The 'Obtained: ' label itself must be soft red, not bright red."""
        result = LineColorizer.color_e_line("Obtained: 3.141592653589793", "failed", is_first=False)
        assert SOFT_PEACH in result

    def test_expected_label_is_soft_peach(self):
        result = LineColorizer.color_e_line("Expected: 3.14 ± 0.001", "failed", is_first=False)
        assert SOFT_PEACH in result

    def test_obtained_plain_text_preserved(self):
        result = LineColorizer.color_e_line("Obtained: 3.141592653589793", "failed", is_first=False)
        assert strip_ansi(result) == "Obtained: 3.141592653589793"

    def test_expected_plain_text_preserved(self):
        result = LineColorizer.color_e_line("Expected: 3.14 ± 0.001", "failed", is_first=False)
        assert strip_ansi(result) == "Expected: 3.14 ± 0.001"

    def test_obtained_not_triggered_for_plain_prose(self):
        """Mid-sentence 'Obtained' must not trigger label matching."""
        result = LineColorizer.color_e_line("Value obtained from cache", "failed", is_first=False)
        assert BRIGHT_RED not in result

    def test_expected_not_triggered_for_plain_prose(self):
        result = LineColorizer.color_e_line("More than expected results", "failed", is_first=False)
        assert GREEN not in result

    def test_label_lines_also_rendered_when_is_first(self):
        """Label line as first E-line: routes through color_assert_line fallback — no crash."""
        result = LineColorizer.color_e_line("Obtained: 42", "failed", is_first=True)
        assert strip_ansi(result) == "Obtained: 42"


# ── color_e_line: approx table rows ──────────────────────────────────────────

class TestApproxTableRowColors:
    """color_e_line: coloring of pipe-delimited approx table data rows.

    Data rows: obtained column = bright red, expected column = green.
    Header row: stays soft red (no false highlights).
    Whitespace padding preserved for visual alignment.
    """

    def test_data_row_obtained_is_bright_red(self):
        row = "0     | 0.30000000000000004 | 0.4 ± 1.0e-09"
        result = LineColorizer.color_e_line(row, "failed", is_first=False)
        assert BRIGHT_RED in result

    def test_data_row_expected_is_green(self):
        row = "0     | 0.30000000000000004 | 0.4 ± 1.0e-09"
        result = LineColorizer.color_e_line(row, "failed", is_first=False)
        assert GREEN in result

    def test_data_row_plain_text_preserved(self):
        row = "0     | 0.30000000000000004 | 0.4 ± 1.0e-09"
        assert strip_ansi(LineColorizer.color_e_line(row, "failed", is_first=False)) == row

    def test_data_row_str_index(self):
        """Dict key index (string) must also produce correct colors."""
        row = "x     | 1.0                 | 2.0 ± 1.0e-09"
        result = LineColorizer.color_e_line(row, "failed", is_first=False)
        assert BRIGHT_RED in result
        assert GREEN in result

    def test_data_row_unicode_tolerance(self):
        """±-symbol in expected must not break parsing or coloring."""
        row = "1     | 3.3000000000000003  | 3.4 ± 1.0e-09"
        result = LineColorizer.color_e_line(row, "failed", is_first=False)
        assert BRIGHT_RED in result
        assert GREEN in result
        assert strip_ansi(result) == row

    def test_header_row_is_soft_peach_only(self):
        """Header must stay soft red — no false green or bright red."""
        header = "Index | Obtained            | Expected"
        result = LineColorizer.color_e_line(header, "failed", is_first=False)
        assert SOFT_PEACH in result
        assert GREEN not in result
        assert BRIGHT_RED not in result

    def test_header_row_plain_text_preserved(self):
        header = "Index | Obtained            | Expected"
        assert strip_ansi(LineColorizer.color_e_line(header, "failed", is_first=False)) == header
