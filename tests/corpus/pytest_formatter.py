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
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pytest

try:
    from _pytest._io import TerminalWriter as _PytestTerminalWriter
except ImportError:  # pragma: no cover — only missing outside a pytest install
    _PytestTerminalWriter = None  # type: ignore[assignment,misc]

# ── ANSI palette ──────────────────────────────────────────────────────────────
# Plain functions so linters don't flag unnecessary-lambda-assignment.
# Change the escape codes here to retheme everything.

_NO_COLOR = not sys.stdout.isatty() or bool(os.environ.get("NO_COLOR"))


def _esc(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def c_pass(t: str) -> str:
    """Bright green — passing tests / expected values."""
    return _esc("92", t)


def c_fail(t: str) -> str:
    """Standard red — FAIL badge, expected values."""
    return _esc("31", t)


def c_error(t: str) -> str:
    """Bright red — errors."""
    return _esc("91", t)


def c_skip(t: str) -> str:
    """Bright yellow — skipped tests."""
    return _esc("93", t)


def c_xfail(t: str) -> str:
    """Gray — expected failures."""
    return _esc("90", t)


def c_xpass(t: str) -> str:
    """Yellow — unexpected passes."""
    return _esc("93", t)


def c_emsg(t: str) -> str:
    """Lighter red — E-line messages, context lines, assert keywords."""
    return _esc("91", t)


def c_section(t: str) -> str:
    """Gray — captured output section headers."""
    return _esc("90", t)


def c_dim(t: str) -> str:
    """Dim — metadata, timing, context lines."""
    return _esc("2", t)


def c_bold(t: str) -> str:
    """Bold — totals label."""
    return _esc("1", t)


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


# ── Line coloring ─────────────────────────────────────────────────────────────

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

    # E lines that add no value in compact output
    _NOISE: Tuple[str, ...] = (
        "Use -v to get more diff",
        "use -vv to show",
        "Omitting",
        "Full diff",
    )

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
    def _find_op(cls, text: str) -> Optional[Tuple[int, str]]:
        """
        Scan text for the first comparison operator at bracket/quote depth 0.

        Returns (position, operator) or None.
        Depth tracking:
          - Bracket pairs ()[]{}  increment / decrement depth
          - String literals ' and " are consumed so their contents are skipped
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
    def color_assert_line(cls, text: str) -> str:
        """
        Color 'assert X op Y' with received (X) in red and expected (Y) in green.

        If the line cannot be parsed as an assertion, falls back to full red.
        The 'AssertionError:' prefix is preserved in red; 'assert' and the
        operator are dimmed so the values stand out.
        """
        parsed = cls.parse_assert(text)
        if parsed is None:
            return c_emsg(text)

        received, op, expected = parsed

        prefix = c_emsg("AssertionError: ") if text.startswith("AssertionError: ") else ""
        return (
            prefix
            + c_emsg("assert ")
            + c_pass(received)
            + c_emsg(f" {op} ")
            + c_fail(expected)
        )

    @classmethod
    def color_e_line(cls, line: str, outcome: str, is_first: bool) -> str:
        """
        Dispatch coloring for one E line based on content and context.

        Rules (in priority order):
          skipped outcome      → yellow    (it's a reason, not an error)
          starts with '- '     → green     (received value in unified diff)
          starts with '+ '     → bright red (expected value in unified diff)
          starts with '? '     → soft red  (diff caret pointer)
          first line + assert  → parse and color left/right individually
          first line otherwise → soft red  (main exception type and message)
          any other line       → soft red  (context — informative but not primary)
        """
        if outcome == "skipped":
            return c_skip(line)
        if line.startswith("- ") or line == "-":
            return c_pass(line)
        if line.startswith("+ ") or line == "+":
            return c_fail(line)
        if line.startswith("? "):
            return c_emsg(line)
        if is_first and cls.parse_assert(line) is not None:
            return cls.color_assert_line(line)
        if is_first:
            return c_emsg(line)
        return c_emsg(line)

    @classmethod
    def is_noise(cls, line: str) -> bool:
        """Return True if the line adds no value and should be suppressed."""
        return any(noise in line for noise in cls._NOISE)


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

    # ── I/O ───────────────────────────────────────────────────────────────────

    def _p(self, text: str = "") -> None:
        print(text, flush=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _classify(report) -> str:
        """Map a raw pytest report to one of the canonical outcome strings."""
        if hasattr(report, "wasxfail"):
            return "xpassed" if report.outcome == "passed" else "xfailed"
        if report.when in ("setup", "teardown") and report.outcome == "failed":
            return "error"
        return report.outcome  # passed | failed | skipped

    @staticmethod
    def _extract_short(report, outcome: str) -> Optional[str]:
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
                return "\n".join(e_lines[:6])
            return reprcrash.message  # type: ignore[union-attr]

        return next(
            (ln.strip()[:300] for ln in str(lr).strip().splitlines() if ln.strip()),
            None,
        )

    @staticmethod
    def _split_nodeid(nodeid: str) -> Tuple[str, str]:
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
        self._cur_file = file
        self._file_buf = []
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

    # ── Per-result rendering ──────────────────────────────────────────────────

    def _render_result(self, r: TestResult) -> None:
        """Print one test result line, inline E lines, and captured sections."""
        badge = _BADGE.get(r.outcome, r.outcome.upper())
        dur   = c_dim(f"  {r.duration * 1000:.1f}ms")
        self._p(f"  --- {badge}  {r.name}{dur}")

        if r.short_msg:
            lines = [
                ln for ln in r.short_msg.splitlines()
                if not LineColorizer.is_noise(ln)
            ]
            for i, line in enumerate(lines):
                colored = LineColorizer.color_e_line(line, r.outcome, is_first=(i == 0))
                self._p(f"    {c_emsg('E')}  {colored}")

        if r.outcome not in ("passed", "xfailed"):
            for section_name, content in r.sections:
                if not content.strip():
                    continue
                self._p(f"    {c_section('── ' + section_name + ' ──')}")
                for ln in content.rstrip().splitlines():
                    self._p(f"    {ln}")

    # ── pytest hooks ──────────────────────────────────────────────────────────

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self) -> None:
        """Record session start time."""
        self._t0 = time.monotonic()
        self._p()

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session) -> None:
        """Print the 'collected N tests' header."""
        n    = len(session.items)
        noun = "test" if n == 1 else "tests"
        self._p(f"{c_dim('collected')} {c_bold(str(n))} {c_dim(noun)}")
        self._p()

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

        outcome    = self._classify(report)
        short_msg  = self._extract_short(report, outcome)
        file, name = self._split_nodeid(report.nodeid)

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
        if self._file_buf:
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


# ── Registration ──────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    """Register the formatter plugin and a terminal-reporter stub if needed."""
    _plugin_key = "_pytest_formatter_instance"
    if not config.pluginmanager.get_plugin(_plugin_key):
        config.pluginmanager.register(FormatterPlugin(), _plugin_key)

    # When -p no:terminal is used, the real TerminalReporter is absent.
    # pytest's assertion rewriting calls config.get_terminal_writer() which
    # asserts terminalreporter is not None — causing bare "AssertionError"
    # with no detail on every assertion failure.
    #
    # Fix: register a minimal stub so get_terminal_writer() works while
    # all output is silently discarded into a StringIO sink.
    terminal_absent = not config.pluginmanager.get_plugin("terminalreporter")
    if terminal_absent and _PytestTerminalWriter is not None:
        _writer_cls = _PytestTerminalWriter  # local binding — narrows type for Pyright

        class _TerminalReporterStub:  # pylint: disable=too-few-public-methods
            """Exists only to satisfy config.get_terminal_writer()."""

            def __init__(self) -> None:
                self._tw = _writer_cls(io.StringIO())

        config.pluginmanager.register(_TerminalReporterStub(), "terminalreporter")
