"""
pytest_formatter.py — Opinionated pytest output formatter.

Output style:

  tests/test_foo.py
    --- PASS  test_something                             0.8ms
    --- FAIL  test_other                                 1.2ms
      E  AssertionError: assert 3 == 30
    --- ERROR test_broken                                0.1ms
      E  AttributeError: 'NoneType' object has no attribute 'get'
    --- SKIP  test_ignored                               0.0ms
      E  Skipped: reason here
  => 1 passed, 1 failed, 1 error, 1 skipped

  Total: 1 passed, 1 failed, 1 error, 1 skipped  in 0.12s

Load via Makefile:
    PYTHONPATH=. pytest -p no:terminal -p pytest_formatter [TARGET]
"""
from __future__ import annotations

import io
import os
import sys
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Set in pytest_configure when --glaze is active; None otherwise.
# BDD hook functions below gate on this so they are no-ops without --glaze.
_glaze_plugin: Optional["FormatterPlugin"] = None

try:
    from _pytest._io import TerminalWriter as _PytestTerminalWriter
except ImportError:  # pragma: no cover — only missing outside a pytest install
    _PytestTerminalWriter = None  # type: ignore[assignment,misc]

# ── ANSI palette ──────────────────────────────────────────────────────────────
# Plain functions so linters don't flag unnecessary-lambda-assignment.
# Change the escape codes here to retheme everything.

_NO_COLOR = not sys.stdout.isatty() or bool(os.environ.get("NO_COLOR"))

# FIX 1: _RED_SOFT was "\033[0;38;2;252;205;174;49" — two bugs:
#   • It included a "\033[" prefix; _esc() already supplies that, so the
#     rendered escape became "\033[\033[…m" (doubled CSI).
#   • It had a trailing ";49" (default-background reset) that was unintentional.
_RED_SOFT      = "0;38;2;252;205;174"   # 24-bit peach — c_emsg / context lines
_BRIGHT_GREEN  = "92"
_BRIGHT_RED    = "91"
_BRIGHT_YELLOW = "93"
# FIX 2: Errors and failures were both using _BRIGHT_RED, making them
#   visually indistinguishable despite different semantic meanings.
#   Errors (collection failures, setup/teardown crashes) now use standard
#   red so they read as distinct from assertion-failure highlights.
_STANDARD_RED  = "31"
_GRAY          = "90"
_DIM           = "2"
_BOLD          = "1"
_BABY_BLUE  = "0;38;2;220;248;255"   # near-white bright blue — Feature
_STEEL_BLUE = "0;38;2;170;225;255"   # sky blue   — Scenario

# ── Max E-lines surfaced inline ───────────────────────────────────────────────
# FIX 8: Hard-coded limit of 6 was too low for large assertion diffs
#   (e.g. comparing big dicts/lists). Raised and named so it's easy to tune.
#   Noise filtering in _render_result provides a second layer of trimming.
MAX_E_LINES: int = 15


def _esc(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def c_pass(t: str) -> str:
    """Bright green — passing tests / received values."""
    return _esc(_BRIGHT_GREEN, t)


def c_fail(t: str) -> str:
    """Bright red — FAIL badge, expected values in assertions."""
    return _esc(_BRIGHT_RED, t)


def c_error(t: str) -> str:
    """Standard red — ERROR badge, collection errors, setup/teardown crashes."""
    return _esc(_STANDARD_RED, t)


def c_skip(t: str) -> str:
    """Bright yellow — skipped tests."""
    return _esc(_BRIGHT_YELLOW, t)


def c_xfail(t: str) -> str:
    """Gray — expected failures."""
    return _esc(_BRIGHT_RED, t)


def c_xpass(t: str) -> str:
    """Yellow — unexpected passes."""
    return _esc(_BRIGHT_YELLOW, t)


def c_emsg(t: str) -> str:
    """Peach / soft red — E-line messages, context lines, assert keywords."""
    return _esc(_RED_SOFT, t)


def c_section(t: str) -> str:
    """Gray — captured output section headers."""
    return _esc(_GRAY, t)


def c_dim(t: str) -> str:
    """Dim — metadata, timing, context lines."""
    return _esc(_DIM, t)


def c_bold(t: str) -> str:
    """Bold — totals label."""
    return _esc(_BOLD, t)

def c_bdd_feature(t: str) -> str:
    """Baby blue — BDD Feature: label and name, full line."""
    return _esc(_BABY_BLUE, t)


def c_bdd_scenario(t: str) -> str:
    """Steel blue — BDD Scenario: label and name, full line."""
    return _esc(_STEEL_BLUE, t)


# ── Outcome tables ────────────────────────────────────────────────────────────

_OUTCOME_ORDER = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")

_BADGE: Dict[str, str] = {
    "passed":  c_pass("PASS"),
    "failed":  c_fail("FAIL"),
    "error":   c_error("ERROR"),
    "skipped": c_skip("SKIP"),
    "xfailed": c_xfail("XFAIL"),
    "xpassed": c_xpass("XPASS"),
}

# Color function applied to the "---" prefix — matches the badge for each outcome.
_OUTCOME_COLOR = {
    "passed":  c_pass,
    "failed":  c_fail,
    "error":   c_error,
    "skipped": c_skip,
    "xfailed": c_xfail,
    "xpassed": c_xpass,
}

_SUMMARY_FMT = {
    "passed":  lambda n: c_pass(f"{n} passed"),
    "failed":  lambda n: c_fail(f"{n} failed"),
    "error":   lambda n: c_error(f"{n} errors"),
    "skipped": lambda n: c_skip(f"{n} skipped"),
    "xfailed": lambda n: c_xfail(f"{n} xfailed"),
    "xpassed": lambda n: c_xpass(f"{n} xpassed"),
}


# ── Domain ────────────────────────────────────────────────────────────────────


@dataclass
class TestResult:
    """Normalised result for a single test, ready for rendering."""

    nodeid:    str
    file:      str
    name:      str
    outcome:   str                       # one of _OUTCOME_ORDER
    duration:  float                     # seconds
    short_msg: Optional[str] = None      # one-liner shown on the E line
    sections:  List[Tuple[str, str]] = field(default_factory=list)

@dataclass
class _BDDStep:
    """Buffered BDD step waiting to be rendered at scenario flush time."""
    step:      Any
    outcome:   str
    duration:  float
    short_msg: Optional[str]

# ── Line coloring ─────────────────────────────────────────────────────────────

class LineColorizer:
    """
    All E-line coloring decisions, extracted for unit testability.

    Fully independent of pytest internals — operates on plain strings.
    The key feature is parse_assert(), which splits 'assert X op Y' so
    X (received) can be colored green and Y (expected) red, matching the
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
    # FIX 7: "Full diff" → "Full diff:" to avoid false positives on test
    #   output that legitimately contains the phrase "Full diff calculated" etc.
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
    #   Obtained → c_fail (red)  — the wrong value, the one that caused the failure
    #   Expected → c_pass (green)— the target value, what the test demanded
    #
    # This reads naturally as a standalone label pair: red = bad, green = goal.
    _LABEL_COLORS: Tuple[Tuple[str, object], ...] = (
        ("Obtained: ", c_fail),
        ("Expected: ", c_pass),
    )

    @classmethod
    def parse_approx_table_row(cls, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse a pytest-approx pipe-separated table **data** row.

        Matches the per-element rows emitted for list and dict approx failures::

            '0     | 0.30000000000000004 | 0.4 ± 1.0e-09'
            'x     | 1.0                 | 2.0 ± 1.0e-09'

        Returns ``(index_col, obtained_col, expected_col)`` where each value
        includes its original surrounding whitespace so the caller can preserve
        column alignment when applying colors.

        Returns ``None`` for:
          - The header row   ``'Index | Obtained  | Expected'``  — obtained column
            starts with a letter, not a digit.
          - Any line with a pipe count other than exactly 2.
          - Lines where the obtained column is empty after stripping.
        """
        if text.count("|") != 2:
            return None
        idx_col, obt_col, exp_col = text.split("|")
        obtained_stripped = obt_col.strip()
        if not obtained_stripped:
            return None
        # Discriminate data rows from the header: obtained starts with a digit
        # (or '-' for negative numbers). The header has "Obtained" (starts 'O').
        if not (obtained_stripped[0].isdigit() or obtained_stripped[0] == "-"):
            return None
        return idx_col, obt_col, exp_col

    @classmethod
    def split_prefix(cls, text: str) -> Tuple[str, str]:
        """
        Separate a human-readable prose prefix from a Python value expression.

        Scans left-to-right for the first ': ' immediately followed by a
        VALUE_STARTERS character.  Everything up to and including that ': ' is
        the prefix; everything after is the value.

        Examples::

            'At index 0 diff: \\'Global Launch\\''
                → ('At index 0 diff: ', '\\'Global Launch\\'')

            '\\'Global Launch\\''   → ('', '\\'Global Launch\\'')
            'Extra items'         → ('', 'Extra items')   # no value found
            '{\\'b\\': 2}'          → ('', '{\\'b\\': 2}')  # starts with value char
        """
        if not text or text[0] in cls.VALUE_STARTERS:
            return "", text
        i = 0
        while i < len(text) - 2:
            if text[i] == ":" and text[i + 1] == " " and text[i + 2] in cls.VALUE_STARTERS:
                return text[: i + 2], text[i + 2 :]
            i += 1
        return "", text

    @classmethod
    def parse_assert(cls, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Parse an assertion line into (received, operator, expected).

        Handles:
          'assert 3 == 30'
          'AssertionError: assert X == Y'
          'assert None is not None'
          'assert "foo" in ["bar", "baz"]'
          'assert {1, 2} == {1, 3}'

        The parser tracks bracket and quote depth so operators inside
        string literals or containers are not mistakenly matched.

        Returns None if the text is not a recognisable assertion.
        """
        # Strip optional "AssertionError: " prefix
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

        Returns the bare value string, or ``None`` if the line is not a bare
        assertion (i.e. it has an operator, is not an assertion at all, or the
        inner expression is empty after stripping).

        Examples::

            'assert False'              → 'False'
            'assert None'               → 'None'
            'assert is_valid'           → 'is_valid'
            'assert None is not None'   → None  (has operator, use parse_assert)
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
        Depth tracking:
          - Bracket pairs ()[]{}  increment / decrement depth
          - String literals ' and " are consumed so their contents are skipped

        Known limitation: triple-quoted strings ('''…''' / \"\"\"…\"\"\") are
        not handled — the parser treats each quote as starting/ending a single-
        character string literal. This is unlikely to appear in pytest repr()
        output, but worth noting if the formatter is ever extended.
        """
        depth = 0
        in_str: Optional[str] = None
        i = 0

        while i < len(text):
            ch = text[i]

            # Inside a string literal — skip until closing quote
            if in_str is not None:
                if ch == in_str and (i == 0 or text[i - 1] != "\\"):
                    in_str = None
                i += 1
                continue

            # Start of a string literal
            if ch in ('"', "'"):
                in_str = ch
                i += 1
                continue

            # Bracket depth tracking
            if ch in "([{":
                depth += 1
                i += 1
                continue

            if ch in ")]}":
                depth -= 1
                i += 1
                continue

            # Only match operators at the top level
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

        Used for context lines like:  {'b': 2} != {'b': 999}
        Returns (received, operator, expected) or None.

        ``received`` may include a prose prefix (e.g. ``'At index 0 diff:
        \\'Global Launch\\''``); callers that render it should pass it through
        :meth:`split_prefix` to isolate the actual value.

        Returns ``None`` when the apparent operands are prose words rather than
        Python value expressions.  This prevents false positives such as the
        ``in`` operator being matched in ``'Extra items in the left set:'``.
        """
        result = cls._find_op(text)
        if result is None:
            return None
        pos, op = result
        received = text[:pos].strip()
        expected = text[pos + len(f" {op} ") :].strip()
        if not received or not expected:
            return None
        # Gate on both sides being real Python value expressions.
        # Use split_prefix so a prose prefix like "At index 0 diff: " does not
        # disqualify a line that carries a genuine value after the colon.
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

        Color convention (consistent with diff lines, Obtained/Expected labels,
        and approx table rows throughout the formatter):
          received value  → bright red  (c_fail) — the wrong value
          expected value  → green       (c_pass) — the target value

        Two-sided (``assert X op Y``):
            ``assert`` + op → soft red; received (X) → red; expected (Y) → green.

        Bare (``assert VALUE`` with no operator):
            ``assert`` → soft red; VALUE → bright red.
            The value is the falsy thing that caused the failure.

        Unrecognised lines fall back to uniform soft red.

        The optional ``AssertionError: `` prefix is preserved in soft red in
        all cases.
        """
        # ── two-sided: assert X op Y ─────────────────────────────────────────
        parsed = cls.parse_assert(text)
        if parsed is not None:
            received, op, expected = parsed
            prefix = c_emsg("AssertionError: ") if text.startswith("AssertionError: ") else ""
            # 'is not' — render as 'is' + 'not VALUE' so the expected reads as
            # a natural unit ("not None") rather than repeating the same token.
            if op == "is not":
                colored_op       = c_emsg(" is ")
                colored_expected = c_pass(f"not {expected}")   # green — target condition
            else:
                colored_op       = c_emsg(f" {op} ")
                colored_expected = c_pass(expected)            # green — target value
            return (
                prefix
                + c_emsg("assert ")
                + c_fail(received)       # red   — the wrong value
                + colored_op
                + colored_expected
            )

        # ── bare: assert VALUE (no operator) ─────────────────────────────────
        bare = cls.parse_bare_assert(text)
        if bare is not None:
            prefix = c_emsg("AssertionError: ") if text.startswith("AssertionError: ") else ""
            return prefix + c_emsg("assert ") + c_fail(bare)  # red — the falsy value

        # ── fallback ──────────────────────────────────────────────────────────
        return c_emsg(text)

    @classmethod
    def color_e_line(cls, line: str, outcome: str, is_first: bool) -> str:
        """
        Dispatch coloring for one E line based on content and context.

        Color convention (applied consistently across all line types):
          received / obtained → bright red   — the wrong value
          expected            → green        — the target value

        Rules (in priority order):
          skipped outcome      → yellow
          starts with '- '     → green      (expected content — present in expected, absent in received)
          starts with '+ '     → bright red (received content — present in received, absent in expected)
          starts with '? '     → soft red   (diff caret pointer)
          assertion line       → received red, expected green (via color_assert_line)
          context + comparison → received red, expected green
          label line           → Obtained: red  /  Expected: green
          approx table row     → obtained column red, expected column green
          any other line       → soft red
        """
        if outcome == "skipped":
            return c_skip(line)
        if line.startswith("- ") or line == "-":
            return c_pass(line)
        if line.startswith("+ ") or line == "+":
            return c_fail(line)
        if line.startswith("? "):
            return c_emsg(line)
        if is_first:
            # color_assert_line already falls back to c_emsg when the line
            # is not a recognisable assertion, so no need to call parse_assert
            # here first — that would be a redundant parse and an extra return.
            return cls.color_assert_line(line)
        # Non-first assertion lines (e.g. 'assert False' appearing after the
        # AssertionError: message line) need the same treatment as first-line
        # assertions.  parse_comparison would miss them entirely.
        if line.startswith("assert ") or line.startswith("AssertionError: assert "):
            return cls.color_assert_line(line)
        parsed = cls.parse_comparison(line)
        if parsed is not None:
            received, op, expected = parsed
            prefix, value = cls.split_prefix(received)
            # prefix   → soft red  (prose description, e.g. "At index 0 diff: ")
            # value    → bright red (received — the wrong value)
            # op       → soft red
            # expected → green     (expected — the target value)
            return c_emsg(prefix) + c_fail(value) + c_emsg(f" {op} ") + c_pass(expected)
        # Label-prefixed lines from pytest plugins (e.g. "Obtained: …", "Expected: …").
        for label, color_fn in cls._LABEL_COLORS:
            if line.startswith(label):
                return c_emsg(label) + color_fn(line[len(label):])  # type: ignore[operator]
        # Pipe-separated approx table data rows: "index | obtained | expected".
        # Each column is colored individually while preserving the original
        # whitespace padding so the table alignment stays intact.
        table = cls.parse_approx_table_row(line)
        if table is not None:
            idx_col, obt_col, exp_col = table

            def _color_col(col: str, color_fn) -> str:  # type: ignore[type-arg]
                """Color just the value inside a padded column, keep spaces soft-red."""
                stripped = col.strip()
                leading  = col[: len(col) - len(col.lstrip())]
                trailing = col[len(col.rstrip()) :]
                return c_emsg(leading) + color_fn(stripped) + c_emsg(trailing)

            return (
                c_emsg(idx_col)
                + c_emsg("|")
                + _color_col(obt_col, c_fail)  # obtained → bright red
                + c_emsg("|")
                + _color_col(exp_col, c_pass)  # expected → green
            )
        return c_emsg(line)

    @classmethod
    def is_noise(cls, line: str) -> bool:
        """Return True if the line adds no value and should be suppressed."""
        if any(noise in line for noise in cls._NOISE):
            return True
        if line.startswith("?") and all(c in " -+^" for c in line[1:]):
            return True
        return False


# ── Plugin ────────────────────────────────────────────────────────────────────

class FormatterPlugin:
    """
    Drop-in replacement for pytest's default terminal reporter.

    Design decisions:
    - Failures surface inline — no need to scroll to a deferred FAILURES block.
    - Per-file => summaries give instant orientation across multi-suite runs.
    - Collection errors (bad imports, syntax) are surfaced clearly.
    - Captured stdout/stderr/logs are shown only on failing tests.
    """

    def __init__(self) -> None:
        self._results:    List[TestResult] = []
        self._t0:         float = 0.0
        self._cur_file:   Optional[str] = None
        self._file_buf:   List[TestResult] = []
        self._col_errors: List[Tuple[str, str]] = []
        # BDD state
        self._bdd_step_t0:       Dict[int, float]        = {}   # id(step) → start time
        self._bdd_handled:       set                      = set()# nodeids rendered via BDD hooks
        self._bdd_first_in_file: bool                     = True # spacing between scenarios
        self._bdd_scenario_buf:  List                     = []   # buffered Scenario header + _BDDSteps
        self._bdd_last_step_idx: int                      = -1   # index of last _BDDStep in buf
        self._bdd_scenario_names: Dict[str, str]          = {}   # nodeid → scenario name (for skips)
        self._bdd_cur_feature:   Optional[str] = None  # tracks printed feature header
        self._bdd_any_feature_printed: bool  = False
        self._bdd_pending_file:        Optional[str] = None
        self._bdd_steps_mode: bool = False # True = --bdd-steps flsg, False = compact
        self._bdd_last_was_full_step: bool = False

    # ── I/O ───────────────────────────────────────────────────────────────────

    def _p(self, text: str = "") -> None:
        print(text, flush=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def classify(report) -> str:
        """Map a raw pytest report to one of the canonical outcome strings."""
        if hasattr(report, "wasxfail"):
            return "xpassed" if report.outcome == "passed" else "xfailed"
        if report.when in ("setup", "teardown") and report.outcome == "failed":
            return "error"
        return report.outcome  # passed | failed | skipped

    @staticmethod
    def extract_short(report, outcome: str) -> Optional[str]:
        """
        Extract the most useful inline message for the E line.

        Priority:
          1. xfail/xpass reason from report.wasxfail
          2. Skip reason from the (file, lineno, reason) tuple
          3. E-prefixed assertion introspection lines from the traceback
          4. reprcrash.message as fallback
          5. First non-blank line of the string repr
        """
        if outcome in ("xfailed", "xpassed"):
            reason = getattr(report, "wasxfail", "")
            return f"{outcome}: {reason}" if reason else outcome

        lr = report.longrepr
        if not lr:
            return None

        if isinstance(lr, tuple) and len(lr) == 3:
            return str(lr[2])

        reprcrash = getattr(lr, "reprcrash", None)
        if reprcrash is not None:
            e_lines = [
                stripped[1:].strip()
                for raw in str(lr).splitlines()
                if (stripped := raw.lstrip())
                and (stripped.startswith("E ") or stripped == "E")
                and stripped[1:].strip()
            ]
            if e_lines:
                # FIX 8: was [:6] — too low for large assertion diffs.
                # Noise filtering in _render_result provides a second pass.
                return "\n".join(e_lines[:MAX_E_LINES])
            return reprcrash.message  # type: ignore[union-attr]

        return next(
            (ln.strip()[:300] for ln in str(lr).strip().splitlines() if ln.strip()),
            None,
        )

    @staticmethod
    def split_nodeid(nodeid: str) -> Tuple[str, str]:
        """'a/b.py::foo[x-y]' → ('a/b.py', 'foo[x-y]')."""
        file, sep, name = nodeid.partition("::")
        return file, (name if sep else nodeid)

    # ── File-group management ─────────────────────────────────────────────────

    def _open_file_group(self, file: str) -> None:
        """On file change: flush the previous group's summary, print new header."""
        if file == self._cur_file:
            return
        if self._cur_file is not None:
            self._flush_file_summary()
            self._p()
        self._cur_file          = file
        self._file_buf          = []
        # self._bdd_cur_feature   = None   # reset so Feature header re-prints for new file
        # self._bdd_first_in_file = True
        self._p(file)

    def _flush_file_summary(self) -> None:
        """Print the per-file '=> N passed, N failed' summary line."""
        counts: Dict[str, int] = {}
        for r in self._file_buf:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [
            _SUMMARY_FMT[o](n)
            for o in _OUTCOME_ORDER
            if (n := counts.get(o))  # pylint: disable=superfluous-parens
        ]
        self._p(f"  => {', '.join(parts) if parts else c_dim('nothing ran')}")
        # FIX 4: Reset the buffer here so the intent is explicit. _open_file_group
        # also resets it for the new file, but clearing at the flush site makes
        # the ownership clear and prevents subtle bugs if the call order changes.
        self._file_buf = []
        # self._bdd_first_in_file = True # reset spacing flag for new file

    # ── Per-result rendering ──────────────────────────────────────────────────

    def _render_result(self, r: TestResult) -> None:
        """Print one test result line, inline E lines, and captured sections."""
        # BDD scenario rendered step-by-step — flush buffered lines with
        # any xfail/xpass correction applied to the last step.
        if r.nodeid in self._bdd_handled:
            if self._bdd_pending_file:
                self._open_file_group(self._bdd_pending_file)
                self._bdd_pending_file = None
            self._bdd_flush_scenario(r.outcome, r.short_msg)
            return

        # Skipped BDD test — before_scenario never fired so buffer is empty.
        # Render a single "--- SKIP  Scenario: …" line instead of the fn name.
        if r.outcome == "skipped" and r.nodeid in self._bdd_scenario_names:
            color_fn      = _OUTCOME_COLOR["skipped"]
            badge         = _BADGE["skipped"]
            scenario_name = self._bdd_scenario_names[r.nodeid]
            self._p(f"    {color_fn('---')} {badge}  {color_fn(f'Scenario: {scenario_name}')}")
            if r.short_msg:
                colored = LineColorizer.color_e_line(r.short_msg, "skipped", is_first=True)
                self._p(f"      {c_emsg('E')}  {colored}")
            return

        # ── Normal (non-BDD) rendering ────────────────────────────────────────
        badge    = _BADGE.get(r.outcome, r.outcome.upper())
        color_fn = _OUTCOME_COLOR.get(r.outcome, c_dim)
        dur      = c_dim(f"  {r.duration * 1000:.1f}ms")
        self._p(f"  {color_fn('---')} {badge}  {r.name}{dur}")

        if r.short_msg:
            lines = [
                ln for ln in r.short_msg.splitlines()
                if not LineColorizer.is_noise(ln)
            ]
            for i, line in enumerate(lines):
                colored = LineColorizer.color_e_line(line, r.outcome, is_first=i == 0)
                self._p(f"    {c_emsg('E')}  {colored}")

        if r.outcome not in ("passed", "xfailed"):
            for section_name, content in r.sections:
                if not content.strip():
                    continue
                self._p(f"    {c_section('── ' + section_name + ' ──')}")
                for ln in content.rstrip().splitlines():
                    self._p(f"    {ln}")

# ── BDD helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_exception_msg(exc: BaseException) -> Optional[str]:
        """Concise inline message from a step exception."""
        raw = str(exc).strip()
        if not raw:
            return type(exc).__name__ or None
        if not isinstance(exc, AssertionError):
            raw = f"{type(exc).__name__}: {raw}"
        # Trim verbose StepDefinitionNotFoundError to first sentence only
        if "StepDefinitionNotFoundError" in raw and ". " in raw:
            raw = raw[:raw.index(". ") + 1]
        lines = [ln for ln in raw.splitlines() if ln.strip()][:MAX_E_LINES]
        return "\n".join(lines) or None

    def _render_bdd_step_line(self, bdd_step: _BDDStep) -> None:
        badge    = _BADGE.get(bdd_step.outcome, bdd_step.outcome.upper())
        color_fn = _OUTCOME_COLOR.get(bdd_step.outcome, c_dim)
        keyword  = getattr(bdd_step.step, "keyword", "").rstrip()
        dur      = c_dim(f"  {bdd_step.duration * 1000:.1f}ms")
        step_text = color_fn(f"{keyword} {bdd_step.step.name}")
        self._p(f"      {color_fn('---')} {badge}  {step_text}{dur}")

        if bdd_step.short_msg:
            lines = [
                ln for ln in bdd_step.short_msg.splitlines()
                if not LineColorizer.is_noise(ln)
            ]
            for i, line in enumerate(lines):
                colored = LineColorizer.color_e_line(line, bdd_step.outcome, is_first=i == 0)
                self._p(f"        {c_emsg('E')}  {colored}")

    def _bdd_flush_scenario(self, outcome: str, short_msg: Optional[str]) -> None:
        """
        Flush the buffered scenario lines, applying xfail/xpass correction
        to the last step before printing.

        For xfail: the last step was buffered as "failed" by _bdd_step_error.
                   We override it to "xfailed" so it gets the XFAIL badge.
        For xpass: the last step was buffered as "passed" by _bdd_after_step.
                   We override it to "xpassed" so it gets the XPASS badge.
        """
        if outcome in ("xfailed", "xpassed") and self._bdd_last_step_idx >= 0:
            last = self._bdd_scenario_buf[self._bdd_last_step_idx]
            if isinstance(last, _BDDStep):
                last.outcome   = outcome
                last.short_msg = short_msg  # carries the xfail reason

        # Compact mode: collapse PASS/SKIP/XFAIL/XPASS to a single scenario line
        needs_steps = outcome in ("failed", "error") or self._bdd_steps_mode
        if not needs_steps:
            # Print string items (Feature/Scenario headers, blank lines)
            # then a single compact scenario result line
            total_dur = sum(
                item.duration for item in self._bdd_scenario_buf
                if isinstance(item, _BDDStep)
            )
            # Find the scenario header string (last string before first step)
            scenario_line = next(
                (item for item in reversed(self._bdd_scenario_buf)
                 if isinstance(item, str) and "Scenario:" in item),
                None
            )

            for item in self._bdd_scenario_buf:
                if isinstance(item, str) and "Scenario:" not in item:
                    if item == "" and not self._bdd_last_was_full_step:
                        continue # <- supress blank between compact->compact
                    self._p(item)  # blank lines and Feature headers
            self._bdd_last_was_full_step = False

            if scenario_line is not None:
                badge    = _BADGE.get(outcome, outcome.upper())
                color_fn = _OUTCOME_COLOR.get(outcome, c_dim)
                dur      = c_dim(f"  {total_dur * 1000:.1f}ms")
                # Extract plain scenario name from the colored string
                plain = re.sub(r"\033\[[\d;]*m", "", scenario_line).strip()
                self._p(f"    {color_fn('---')} {badge}  {color_fn(plain)}{dur}")
        else:
            for item in self._bdd_scenario_buf:
                if isinstance(item, str):
                    self._p(item)
                else:
                    self._render_bdd_step_line(item)
            self._bdd_last_was_full_step = True # full-step scenario just ran

        self._bdd_scenario_buf  = []
        self._bdd_last_step_idx = -1

    # ── BDD delegate methods (called by module-level hooks) ───────────────────

    def _bdd_before_scenario(self, request, feature, scenario) -> None:
        # Store file for _open_file_group — called later in _render_result
        # outside pytest's capture context so self._p() is not swallowed.
        file, _ = self.split_nodeid(request.node.nodeid)
        self._bdd_pending_file = file

        feature_name = getattr(feature, "name", "")
        self._bdd_scenario_buf = []

        if feature_name and feature_name != self._bdd_cur_feature:
            if self._bdd_any_feature_printed:
                self._bdd_scenario_buf.append("")
            self._bdd_scenario_buf.append(c_bdd_feature(f"  Feature: {feature_name}"))
            self._bdd_cur_feature         = feature_name
            self._bdd_any_feature_printed = True
            self._bdd_first_in_file       = False
        elif not self._bdd_first_in_file:
            self._bdd_scenario_buf.append("")

        self._bdd_first_in_file = False
        self._bdd_scenario_buf.append(c_bdd_scenario(f"    Scenario: {scenario.name}"))
        self._bdd_last_step_idx = -1

    def _bdd_before_step(self, request, feature, scenario, step, step_func) -> None:
        # Insert a dim "Background:" label before the first background step.
        bg       = getattr(feature, "background", None)
        bg_steps = list(bg.steps) if bg and hasattr(bg, "steps") else []
        if bg_steps and step is bg_steps[0]:
            self._bdd_scenario_buf.append(f"       {c_dim('Background:')}")
        self._bdd_step_t0[id(step)] = time.monotonic()

    def _bdd_after_step(
        self, request, feature, scenario, step, step_func, step_func_args
    ) -> None:
        t0       = self._bdd_step_t0.pop(id(step), time.monotonic())
        duration = time.monotonic() - t0
        bdd_step = _BDDStep(step=step, outcome="passed", duration=duration, short_msg=None)
        self._bdd_scenario_buf.append(bdd_step)
        self._bdd_last_step_idx = len(self._bdd_scenario_buf) - 1
        self._bdd_handled.add(request.node.nodeid)

    def _bdd_step_error(
        self, request, feature, scenario, step, step_func, step_func_args, exception
    ) -> None:
        t0        = self._bdd_step_t0.pop(id(step), time.monotonic())
        duration  = time.monotonic() - t0
        outcome   = "failed" if isinstance(exception, AssertionError) else "error"
        short_msg = self._extract_exception_msg(exception)
        bdd_step  = _BDDStep(step=step, outcome=outcome, duration=duration, short_msg=short_msg)
        self._bdd_scenario_buf.append(bdd_step)
        self._bdd_last_step_idx = len(self._bdd_scenario_buf) - 1
        self._bdd_handled.add(request.node.nodeid)

    def _bdd_step_func_lookup_error(
        self, request, feature, scenario, step, exception
    ) -> None:
        t0        = self._bdd_step_t0.pop(id(step), time.monotonic())
        duration  = time.monotonic() - t0
        short_msg = self._extract_exception_msg(exception)
        bdd_step  = _BDDStep(step=step, outcome="error", duration=duration, short_msg=short_msg)
        self._bdd_scenario_buf.append(bdd_step)
        self._bdd_last_step_idx = len(self._bdd_scenario_buf) - 1
        self._bdd_handled.add(request.node.nodeid)


    # ── pytest hooks ──────────────────────────────────────────────────────────

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self) -> None:
        """Record session start time."""
        self._t0 = time.monotonic()
        self._p()

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session) -> None:
        """Print the 'collected N tests' header and index BDD scenario names."""
        n    = len(session.items)
        noun = "test" if n == 1 else "tests"
        self._p(f"{c_dim('collected')} {c_bold(str(n))} {c_dim(noun)}")
        self._p()
        # Build nodeid → scenario name map so skipped BDD tests can be
        # rendered as "--- SKIP  Scenario: …" rather than "--- SKIP  test_fn"
        for item in session.items:
            fn = getattr(item, "function", None)
            if fn is None:
                continue
            scenario_obj = getattr(fn, "__scenario__", None)
            if scenario_obj is not None:
                self._bdd_scenario_names[item.nodeid] = getattr(scenario_obj, "name", None) or str(scenario_obj)
            elif fn.__doc__:
                parts = fn.__doc__.split(": ", 1)
                if len(parts) == 2:
                    self._bdd_scenario_names[item.nodeid] = parts[1]

    @pytest.hookimpl(tryfirst=True)
    def pytest_collectreport(self, report) -> None:
        """Capture collection-phase errors: bad imports, syntax errors, etc."""
        if report.failed and report.longrepr:
            self._col_errors.append(
                (str(report.nodeid), str(report.longrepr).strip())
            )

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report) -> None:
        """Handle each test phase report and render the result line."""
        if report.when != "call" and report.outcome == "passed":
            return

        outcome    = self.classify(report)
        short_msg  = self.extract_short(report, outcome)
        file, name = self.split_nodeid(report.nodeid)

        result = TestResult(
            nodeid    = report.nodeid,
            file      = file,
            name      = name,
            outcome   = outcome,
            duration  = getattr(report, "duration", 0.0),
            short_msg = short_msg,
            sections  = list(report.sections),
        )

        self._open_file_group(file)
        self._file_buf.append(result)
        self._results.append(result)
        self._render_result(result)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self) -> None:
        """Flush the last file summary and print the global Total line."""
        # FIX 5: Was `if self._file_buf` — that guard would silently skip the
        # summary if the buffer happened to be empty (e.g. after a refactor
        # that cleared it early). Keying on _cur_file is the correct signal:
        # if we opened at least one file group, we must close it.
        if self._cur_file is not None:
            self._flush_file_summary()

        if self._col_errors:
            self._p()
            self._p(c_bold(c_error("COLLECTION ERRORS")))
            for nodeid, msg in self._col_errors:
                self._p(f"  {c_error('⚠')}  {nodeid}")
                for line in msg.splitlines():
                    self._p(f"    {c_dim(line)}")

        elapsed = time.monotonic() - self._t0
        counts: Dict[str, int] = {}
        for r in self._results:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [
            _SUMMARY_FMT[o](n)
            for o in _OUTCOME_ORDER
            if (n := counts.get(o))  # pylint: disable=superfluous-parens
        ]
        summary = ", ".join(parts) if parts else c_dim("no tests ran")
        self._p()
        self._p(f"{c_bold('Total:')} {summary}  {c_dim(f'in {elapsed:.2f}s')}")
        self._p()

# ── BDD hooks (module-level) ──────────────────────────────────────────────────
# Must be module-level functions — pytest-bdd 8 uses strict hookspec validation
# that rejects 'self' in hookimpl signatures. These delegate to the plugin
# instance via _glaze_plugin and are no-ops when --glaze is not active.

def pytest_bdd_before_scenario(request, feature, scenario) -> None:
    if _glaze_plugin is not None:
        _glaze_plugin._bdd_before_scenario(request, feature, scenario)


def pytest_bdd_before_step(request, feature, scenario, step, step_func) -> None:
    if _glaze_plugin is not None:
        _glaze_plugin._bdd_before_step(request, feature, scenario, step, step_func)


def pytest_bdd_after_step(
    request, feature, scenario, step, step_func, step_func_args
) -> None:
    if _glaze_plugin is not None:
        _glaze_plugin._bdd_after_step(request, feature, scenario, step, step_func, step_func_args)


def pytest_bdd_step_error(
    request, feature, scenario, step, step_func, step_func_args, exception
) -> None:
    if _glaze_plugin is not None:
        _glaze_plugin._bdd_step_error(
            request, feature, scenario, step, step_func, step_func_args, exception
        )


def pytest_bdd_step_func_lookup_error(
    request, feature, scenario, step, exception
) -> None:
        if _glaze_plugin is not None:
            _glaze_plugin._bdd_step_func_lookup_error(
            request, feature, scenario, step, exception
        )

# ── Registration ──────────────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    """Declare the --glaze flag that opts in to the formatter."""
    group = parser.getgroup("terminal reporting")
    group.addoption(
        "--glaze",
        action="store_true",
        default=False,
        help="Enable pytest-glaze compact, color-semantic output formatter.",
    )
    group.addoption(
        "--bdd-steps",
        action="store_true",
        default=False,
        help="Show full step-by-step BDD output. Default is compact (scenario lines only).",
    )

@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Activate glaze only when --glaze is explicitly requested.

    ``trylast=True`` guarantees this runs after the default terminal reporter
    has registered itself, so we can safely unregister it without racing
    against load order.  This works for all activation paths — entry-point
    auto-load, ``-p pytest_glaze``, and ``addopts = "--glaze"``.

    When --glaze is passed:
      1. The default terminal reporter is unregistered (if present) and the
         terminal plugin is blocked so it cannot re-register.
      2. FormatterPlugin is registered to handle all output hooks.
      3. A TerminalReporterStub is registered so plugins that call
         config.get_terminal_writer() (e.g. pytest-cov) do not crash.

    When --glaze is absent the function returns immediately, leaving the
    default pytest output pipeline completely untouched.
    """
    try:
        enabled = config.getoption("--glaze")
    except (ValueError, AttributeError):
        # Options not yet available during very early plugin initialisation.
        return

    if not enabled:
        return

    # Unregister the default TerminalReporter if it was registered before us.
    # Because we use trylast=True this is the normal case — terminal runs first,
    # we clean up after it.
    existing = config.pluginmanager.get_plugin("terminalreporter")
    if existing is not None:
        config.pluginmanager.unregister(existing)

    # Block terminal so it cannot register again later.
    if not config.pluginmanager.is_blocked("terminal"):
        config.pluginmanager.set_blocked("terminal")

    _plugin_key = "_pytest_glaze_instance"
    existing = config.pluginmanager.get_plugin(_plugin_key)
    if existing is None:
        plugin = FormatterPlugin()
        plugin._bdd_steps_mode = config.getoption("--bdd-steps", default=False)
        config.pluginmanager.register(plugin, _plugin_key)
    else:
        plugin = existing
    global _glaze_plugin
    _glaze_plugin = plugin

    # Register stub so config.get_terminal_writer() never raises.
    if config.pluginmanager.get_plugin("terminalreporter") is None \
            and _PytestTerminalWriter is not None:
        _writer_cls = _PytestTerminalWriter  # local binding — narrows type for Pyright

        class _TerminalReporterStub:  # pylint: disable=too-few-public-methods
            """Satisfies config.get_terminal_writer() without rendering anything."""

            def __init__(self) -> None:
                self._tw = _writer_cls(io.StringIO())

        config.pluginmanager.register(_TerminalReporterStub(), "terminalreporter")
