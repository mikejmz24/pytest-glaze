"""
pytest_formatter.py — Opinionated pytest output formatter.

Output style (mirrors the reference screenshot):

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

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pytest

# ── ANSI palette ──────────────────────────────────────────────────────────────
# Change these lambdas to retheme everything.

_NO_COLOR = not sys.stdout.isatty() or bool(os.environ.get("NO_COLOR"))

def _esc(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"

# Outcome colours
c_pass  = lambda t: _esc("92", t)   # bright green
c_fail  = lambda t: _esc("91", t)   # bright red
c_error = lambda t: _esc("91", t)   # bright red
c_skip  = lambda t: _esc("93", t)   # bright yellow
c_xfail = lambda t: _esc("90", t)   # gray
c_xpass = lambda t: _esc("93", t)   # yellow

# UI colours
c_emsg    = lambda t: _esc("91", t)   # inline error text
c_section = lambda t: _esc("90", t)   # captured output headers
c_dim     = lambda t: _esc("2",  t)   # metadata / timing
c_bold    = lambda t: _esc("1",  t)   # bold

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
    nodeid:    str
    file:      str
    name:      str
    outcome:   str                          # one of _OUTCOME_ORDER
    duration:  float                        # seconds
    short_msg: Optional[str] = None         # one-liner shown on the E line
    sections:  List[Tuple[str, str]] = field(default_factory=list)

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
        self._file_buf:   List[TestResult] = []   # results for the active file
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
             (the "assert 3 == 30 / where 3 = result" detail pytest rewrites)
          4. reprcrash.message as fallback
          5. First non-blank line of the string repr
        """
        if outcome in ("xfailed", "xpassed"):
            reason = getattr(report, "wasxfail", "")
            return f"{outcome}: {reason}" if reason else outcome

        lr = report.longrepr
        if not lr:
            return None

        # Skip reason: (filename, lineno, "Skipped: ...")
        if isinstance(lr, tuple) and len(lr) == 3:
            return str(lr[2])

        # ReprExceptionInfo — assertion / exception failures.
        # Extract the E-prefixed lines pytest's assertion rewriting produces.
        # These contain the actual diff/detail, e.g.:
        #   E  assert 3 == 30
        #   E    where 3 = result
        if hasattr(lr, "reprcrash"):
            e_lines = []
            for line in str(lr).splitlines():
                stripped = line.lstrip()
                if stripped.startswith("E ") or stripped == "E":
                    content = stripped[1:].strip()
                    if content:
                        e_lines.append(content)

            if e_lines:
                return "\n".join(e_lines[:6])   # cap at 6 lines

            # No E lines (e.g. bare raise with no message): fall back
            return lr.reprcrash.message

        # Fallback: first non-blank line of the string repr
        for line in str(lr).strip().splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:300]

        return None

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
        self._p(file)   # plain white file path, matches screenshot

    def _flush_file_summary(self) -> None:
        counts: Dict[str, int] = {}
        for r in self._file_buf:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [
            _SUMMARY_FMT[o](n)
            for o in _OUTCOME_ORDER
            if (n := counts.get(o))
        ]
        line = ", ".join(parts) if parts else c_dim("nothing ran")
        self._p(f"  => {line}")

    # ── Per-result rendering ──────────────────────────────────────────────────

    def _render_result(self, r: TestResult) -> None:
        badge = _BADGE.get(r.outcome, r.outcome.upper())
        dur   = c_dim(f"  {r.duration * 1000:.1f}ms")
        self._p(f"  --- {badge}  {r.name}{dur}")

        if r.short_msg:
            # Skip reasons in yellow, everything else in red
            msg_color = c_skip if r.outcome == "skipped" else c_emsg
            for line in r.short_msg.splitlines():
                self._p(f"    {c_emsg('E')}  {msg_color(line)}")

        # Captured stdout / stderr / logs — only shown when a test fails/errors
        if r.outcome not in ("passed", "xfailed"):
            for section_name, content in r.sections:
                if not content.strip():
                    continue
                self._p(f"    {c_section('── ' + section_name + ' ──')}")
                for ln in content.rstrip().splitlines():
                    self._p(f"    {ln}")

    # ── pytest hooks ──────────────────────────────────────────────────────────

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session) -> None:
        self._t0 = time.monotonic()
        self._p()

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session) -> None:
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
        # Suppress passing setup/teardown — only surface them when they fail.
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
    def pytest_sessionfinish(self, session, exitstatus) -> None:
        # Flush the last open file group
        if self._file_buf:
            self._flush_file_summary()

        # Collection errors
        if self._col_errors:
            self._p()
            self._p(c_bold(c_error("COLLECTION ERRORS")))
            for nodeid, msg in self._col_errors:
                self._p(f"  {c_error('⚠')}  {nodeid}")
                for line in msg.splitlines():
                    self._p(f"    {c_dim(line)}")

        # Global summary
        elapsed = time.monotonic() - self._t0
        counts: Dict[str, int] = {}
        for r in self._results:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [
            _SUMMARY_FMT[o](n)
            for o in _OUTCOME_ORDER
            if (n := counts.get(o))
        ]
        summary = ", ".join(parts) if parts else c_dim("no tests ran")
        timing  = c_dim(f"in {elapsed:.2f}s")

        self._p()
        self._p(f"{c_bold('Total:')} {summary}  {timing}")
        self._p()


# ── Registration ──────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    # Guard: the module itself is already registered as "pytest_formatter" when
    # loaded via -p.  Register the stateful instance under a distinct name.
    _KEY = "_pytest_formatter_instance"
    if not config.pluginmanager.get_plugin(_KEY):
        config.pluginmanager.register(FormatterPlugin(), _KEY)

    # When -p no:terminal is used, the real TerminalReporter is absent.
    # pytest's assertion rewriting calls config.get_terminal_writer() which
    # asserts terminalreporter is not None — causing bare "AssertionError"
    # with no detail on every assertion failure.
    #
    # Fix: register a minimal stub so get_terminal_writer() works, while
    # all output is silently discarded to /dev/null.
    if not config.pluginmanager.get_plugin("terminalreporter"):
        from _pytest._io import TerminalWriter

        class _TerminalReporterStub:
            """Exists only to satisfy config.get_terminal_writer()."""
            def __init__(self) -> None:
                self._tw = TerminalWriter(open(os.devnull, "w"))

        config.pluginmanager.register(_TerminalReporterStub(), "terminalreporter")
