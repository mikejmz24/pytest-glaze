"""
pytest_glaze/_colorizer.py — Line coloring logic.

Fully independent of pytest internals — operates on plain strings.
Depends only on _colors and _types.
"""
from __future__ import annotations
import re

from typing import Optional, Tuple

from pytest_glaze._colors import (
    c_emsg, c_fail, c_pass, c_skip,
)


class LineColorizer:
    """
    All E-line coloring decisions, extracted for unit testability.

    Fully independent of pytest internals — operates on plain strings.
    The key feature is parse_assert(), which splits 'assert X op Y' so
    X (received) can be colored red and Y (expected) green, matching the
    +/- diff coloring on subsequent lines.
    """

    # Operators ordered longest-first to prevent partial matches
    # (e.g. "is not" must be tried before "is", "not in" before "in")
    _CMP_OPS: Tuple[str, ...] = (
        "is not", "not in",
        "==", "!=", "<=", ">=",
        "is", "in",
        "<", ">",
    )

    # E lines that add no value in compact output.
    _NOISE: Tuple[str, ...] = (
        "Use -v to get more diff",
        "use -vv to show",
        "Omitting",
        "Full diff:",
    )

    # Characters that begin a Python value expression.
    # Used to distinguish real values from prose words when checking whether
    # an operator match is meaningful (e.g. the 'in' in 'Extra items in the
    # left set:' must not be treated as a comparison operator).
    VALUE_STARTERS: frozenset = frozenset("\"'([{-0123456789")

    # Label-prefixed E-lines emitted by pytest plugins (e.g. pytest-approx).
    # Maps the exact label string (including the trailing space) to the color
    # function that should be applied to the value that follows it.
    #
    # Semantic choice (intentionally inverted from the assert-line convention):
    #   Obtained → c_fail (red)   — the wrong value, the one that caused the failure
    #   Expected → c_pass (green) — the target value, what the test demanded
    _LABEL_COLORS: Tuple[Tuple[str, object], ...] = (
        ("Obtained: ", c_fail),
        ("Expected: ", c_pass),
    )

    @classmethod
    def parse_approx_table_row(cls, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse a pytest-approx pipe-separated table data row.

        Matches the per-element rows emitted for list and dict approx failures::

            '0     | 0.30000000000000004 | 0.4 ± 1.0e-09'
            'x     | 1.0                 | 2.0 ± 1.0e-09'

        Returns ``(index_col, obtained_col, expected_col)`` where each value
        includes its original surrounding whitespace so the caller can preserve
        column alignment when applying colors.

        Returns ``None`` for header rows, lines with wrong pipe count, or
        lines where the obtained column is empty after stripping.
        """
        if text.count("|") != 2:
            return None
        idx_col, obt_col, exp_col = text.split("|")
        obtained_stripped = obt_col.strip()
        if not obtained_stripped:
            return None
        if not (obtained_stripped[0].isdigit() or obtained_stripped[0] == "-"):
            return None
        return idx_col, obt_col, exp_col

    @classmethod
    def split_prefix(cls, text: str) -> Tuple[str, str]:
        """
        Separate a human-readable prose prefix from a Python value expression.

        Scans left-to-right for the first ': ' immediately followed by a
        VALUE_STARTERS character. Everything up to and including that ': ' is
        the prefix; everything after is the value.

        Examples::

            'At index 0 diff: \\'Global Launch\\''
                → ('At index 0 diff: ', '\\'Global Launch\\'')

            '\\'Global Launch\\''   → ('', '\\'Global Launch\\'')
            'Extra items'         → ('', 'Extra items')
        """
        if not text or text[0] in cls.VALUE_STARTERS:
            return "", text
        i = 0
        while i < len(text) - 2:
            if text[i] == ":" and text[i + 1] == " " and text[i + 2] in cls.VALUE_STARTERS:
                return text[: i + 2], text[i + 2:]
            i += 1
        return "", text

    @classmethod
    def parse_assert(cls, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse an assertion line into (received, operator, expected).

        Handles::

            'assert 3 == 30'
            'AssertionError: assert X == Y'
            'assert None is not None'
            'assert "foo" in ["bar", "baz"]'

        Returns None if the text is not a recognisable assertion.
        """
        body = text
        if body.startswith("AssertionError: "):
            body = body[len("AssertionError: "):]
        if not body.startswith("assert "):
            return None
        inner = body[len("assert "):]
        result = cls._find_op(inner)
        if result is None:
            return None
        pos, op = result
        received = inner[:pos].strip()
        expected = inner[pos + len(f" {op} "):].strip()
        return received, op, expected

    @classmethod
    def parse_bare_assert(cls, text: str) -> Optional[str]:
        """
        Parse ``assert VALUE`` where there is no comparison operator.

        Returns the bare value string, or ``None`` if the line has an operator,
        is not an assertion, or the inner expression is empty.

        Examples::

            'assert False'              → 'False'
            'assert None is not None'   → None  (has operator)
            'RuntimeError: boom'        → None  (not an assertion)
        """
        body = text
        if body.startswith("AssertionError: "):
            body = body[len("AssertionError: "):]
        if not body.startswith("assert "):
            return None
        inner = body[len("assert "):].strip()
        if not inner or cls._find_op(inner) is not None:
            return None
        return inner

    @classmethod
    def _find_op(cls, text: str) -> Optional[Tuple[int, str]]:
        """
        Scan text for the first comparison operator at bracket/quote depth 0.

        Returns (position, operator) or None.
        Tracks bracket pairs and string literals so operators inside them
        are not mistakenly matched.
        """
        depth = 0
        in_str: Optional[str] = None
        i = 0

        while i < len(text):
            ch = text[i]

            if in_str is not None:
                if ch == in_str and (i == 0 or text[i - 1] != "\\"):
                    in_str = None
                i += 1
                continue

            if ch in ('"', "'"):
                in_str = ch
                i += 1
                continue

            if ch in "([{":
                depth += 1
                i += 1
                continue

            if ch in ")]}":
                depth -= 1
                i += 1
                continue

            if depth == 0:
                for op in cls._CMP_OPS:
                    pattern = f" {op} "
                    if text[i: i + len(pattern)] == pattern:
                        return i, op

            i += 1

        return None

    @classmethod
    def parse_comparison(cls, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse 'X op Y' without requiring an 'assert' prefix.

        Used for context lines like: {'b': 2} != {'b': 999}
        Returns (received, operator, expected) or None.

        Returns None when the apparent operands are prose words rather than
        Python value expressions, preventing false positives.
        """
        result = cls._find_op(text)
        if result is None:
            return None
        pos, op = result
        received = text[:pos].strip()
        expected = text[pos + len(f" {op} "):].strip()
        if not received or not expected:
            return None
        _, received_value = cls.split_prefix(received)
        if not received_value or received_value[0] not in cls.VALUE_STARTERS:
            return None
        if expected[0] not in cls.VALUE_STARTERS:
            return None
        return received, op, expected

    @classmethod
    def color_assert_line(cls, text: str) -> str:
        """
        Color assertion lines, dispatching on the form of the assertion.

        Color convention:
          received value → bright red  (c_fail) — the wrong value
          expected value → green       (c_pass) — the target value

        Two-sided (``assert X op Y``):
            ``assert`` + op → soft red; received (X) → red; expected (Y) → green.

        Bare (``assert VALUE`` with no operator):
            ``assert`` → soft red; VALUE → bright red.

        Unrecognised lines fall back to uniform soft red.
        """
        parsed = cls.parse_assert(text)
        if parsed is not None:
            received, op, expected = parsed
            prefix = c_emsg("AssertionError: ") if text.startswith("AssertionError: ") else ""
            if op == "is not":
                colored_op       = c_emsg(" is ")
                colored_expected = c_pass(f"not {expected}")
            else:
                colored_op       = c_emsg(f" {op} ")
                colored_expected = c_pass(expected)
            return (
                prefix
                + c_emsg("assert ")
                + c_fail(received)
                + colored_op
                + colored_expected
            )

        bare = cls.parse_bare_assert(text)
        if bare is not None:
            prefix = c_emsg("AssertionError: ") if text.startswith("AssertionError: ") else ""
            return prefix + c_emsg("assert ") + c_fail(bare)

        return c_emsg(text)

    @classmethod
    def color_e_line(cls, line: str, outcome: str, is_first: bool) -> str:
        """
        Dispatch coloring for one E line based on content and context.

        Color convention:
          received / obtained → bright red  — the wrong value
          expected            → green       — the target value

        Rules (in priority order):
          skipped outcome      → yellow
          starts with '- '     → green   (expected content)
          starts with '+ '     → red     (received content)
          starts with '? '     → soft red
          assertion line       → received red, expected green
          context + comparison → received red, expected green
          label line           → Obtained: red / Expected: green
          approx table row     → obtained column red, expected column green
          any other line       → soft red
        """
        colored = cls._color_diff_line(line, outcome)
        if colored is not None:
            return colored
        if is_first or line.startswith("assert ") or line.startswith("AssertionError: assert "):
            return cls.color_assert_line(line)
        parsed = cls.parse_comparison(line)
        if parsed is not None:
            received, op, expected = parsed
            prefix, value = cls.split_prefix(received)
            return c_emsg(prefix) + c_fail(value) + c_emsg(f" {op} ") + c_pass(expected)
        colored = cls._color_label_line(line) or cls._color_approx_row(line)
        return colored if colored is not None else c_emsg(line)

    @classmethod
    def is_noise(cls, line: str) -> bool:
        """Return True if the line adds no value and should be suppressed."""
        if any(noise in line for noise in cls._NOISE):
            return True
        if line.startswith("?") and all(c in " -+^" for c in line[1:]):
            return True
        return False


    @classmethod
    def _color_approx_row(cls, line: str) -> Optional[str]:
        """Color a pipe-separated approx table row. Returns None if not a table row."""
        table = cls.parse_approx_table_row(line)
        if table is None:
            return None
        idx_col, obt_col, exp_col = table

        def _color_col(col: str, color_fn) -> str:  # type: ignore[type-arg]
            stripped = col.strip()
            leading  = col[: len(col) - len(col.lstrip())]
            trailing = col[len(col.rstrip()):]
            return c_emsg(leading) + color_fn(stripped) + c_emsg(trailing)

        return (
            c_emsg(idx_col)
            + c_emsg("|")
            + _color_col(obt_col, c_fail)
            + c_emsg("|")
            + _color_col(exp_col, c_pass)
        )


    @classmethod
    def _color_label_line(cls, line: str) -> Optional[str]:
        """Color Obtained:/Expected: label lines. Returns None if not a label line."""
        for label, color_fn in cls._LABEL_COLORS:
            if line.startswith(label):
                return c_emsg(label) + color_fn(line[len(label):])  # type: ignore[operator]
        return None


    @classmethod
    def _color_diff_line(cls, line: str, outcome: str) -> Optional[str]:
        """Color diff prefix lines and skipped outcome. Returns None if not applicable."""
        if outcome == "skipped":
            return c_skip(line)
        if line.startswith("- ") or line == "-":
            return c_pass(line)
        if line.startswith("+ ") or line == "+":
            return c_fail(line)
        if line.startswith("? "):
            return c_emsg(line)
        return None

    @staticmethod
    def sanitize(text: str) -> str:
        """Strip ANSI escape sequences from untrusted input (test names, messages).
        
        Prevents malicious test names from injecting terminal control sequences
        into the formatter output.
        """
        return re.sub(r"\033\[[\d;]*[a-zA-Z]", "", text)
