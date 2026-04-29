"""
pytest_glaze/_formatter.py — FormatterPlugin: the core pytest output formatter.

Depends on _types, _colors, and _colorizer. No direct dependency on _hooks.
"""

import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import pytest

from pytest_glaze._colorizer import LineColorizer
from pytest_glaze._colors import (
    _BADGE,
    _OUTCOME_COLOR,
    _OUTCOME_ORDER,
    _SUMMARY_FMT,
    c_bdd_feature,
    c_bdd_scenario,
    c_bold,
    c_dim,
    c_emsg,
    c_error,
    c_section,
)
from pytest_glaze._testing import _FormatterTestingMixin
from pytest_glaze._types import (
    MAX_E_LINES,
    TestResult,
    _BDDState,
    _BDDStep,
    _SessionState,
)


class FormatterPlugin(_FormatterTestingMixin):
    """
    Drop-in replacement for pytest's default terminal reporter.

    Design decisions:
    - Failures surface inline — no need to scroll to a deferred FAILURES block.
    - Per-file => summaries give instant orientation across multi-suite runs.
    - Collection errors (bad imports, syntax) are surfaced clearly.
    - Captured stdout/stderr/logs are shown only on failing tests.
    """

    def __init__(self) -> None:
        self._cur_file: Optional[str] = None
        self._file_buf: List[TestResult] = []
        self._cur_class: Optional[str] = None
        self.session = _SessionState()
        self.bdd = _BDDState()

    # ── I/O ───────────────────────────────────────────────────────────────────

    def _p(self, text: str = "") -> None:
        if self.session.output_buf is not None:
            self.session.output_buf.append(text)
        else:
            sys.stdout.write(text + "\n")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def classify(report) -> str:
        """Map a raw pytest report to one of the canonical outcome strings."""
        if hasattr(report, "wasxfail"):
            return "xpassed" if report.outcome == "passed" else "xfailed"
        if report.when in ("setup", "teardown") and report.outcome == "failed":
            return "error"
        return report.outcome

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
        self._cur_file = file
        self._file_buf = []
        self._cur_class = None
        self._p(file)

    def _flush_file_summary(self) -> None:
        """Print the per-file '=> N passed, N failed' summary line."""
        counts: Dict[str, int] = {}
        for r in self._file_buf:
            counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [_SUMMARY_FMT[o](n) for o in _OUTCOME_ORDER if (n := counts.get(o))]
        self._p(f"  => {', '.join(parts) if parts else c_dim('nothing ran')}")
        self._file_buf = []

    # ── Per-result rendering ──────────────────────────────────────────────────

    def _render_result(self, r: TestResult) -> None:
        """Print one test result line, inline E lines, and captured sections."""
        if r.nodeid in self.bdd.handled:
            self._render_bdd_handled(r)
            return
        if r.outcome == "skipped" and r.nodeid in self.bdd.scenario_names:
            self._render_bdd_skip(r)
            return
        self._render_normal(r)

    # ── BDD helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def extract_exception_msg(exc: BaseException) -> Optional[str]:
        """Concise inline message from a step exception."""
        raw = str(exc).strip()
        if not raw:
            return type(exc).__name__ or None
        if not isinstance(exc, AssertionError):
            raw = f"{type(exc).__name__}: {raw}"
        if "StepDefinitionNotFoundError" in raw and ". " in raw:
            raw = raw[: raw.index(". ") + 1]
        lines = [ln for ln in raw.splitlines() if ln.strip()][:MAX_E_LINES]
        return "\n".join(lines) or None

    def _render_bdd_step_line(self, bdd_step: _BDDStep) -> None:
        badge = _BADGE.get(bdd_step.outcome, bdd_step.outcome.upper())
        color_fn = _OUTCOME_COLOR.get(bdd_step.outcome, c_dim)
        keyword = getattr(bdd_step.step, "keyword", "").rstrip()
        dur = c_dim(f"  {bdd_step.duration * 1000:.1f}ms")
        step_text = color_fn(f"{keyword} {LineColorizer.sanitize(bdd_step.step.name)}")
        self._p(f"      {color_fn('---')} {badge}  {step_text}{dur}")

        if bdd_step.short_msg:
            lines = [
                ln
                for ln in bdd_step.short_msg.splitlines()
                if not LineColorizer.is_noise(ln)
            ]
            for i, line in enumerate(lines):
                line = LineColorizer.sanitize(line)
                colored = LineColorizer.color_e_line(
                    line, bdd_step.outcome, is_first=i == 0
                )
                self._p(f"        {c_emsg('E')}  {colored}")

    def _render_bdd_handled(self, r: TestResult) -> None:
        """Render a result that was already handled by BDD hooks."""
        if r.outcome == "error":
            self._p(
                f"    {c_error('---')} {_BADGE['error']}  "
                f"{c_error('teardown failed')}{c_dim(f'  {r.duration * 1000:.1f}ms')}"
            )
            if r.short_msg:
                lines = [
                    ln
                    for ln in r.short_msg.splitlines()
                    if not LineColorizer.is_noise(ln)
                ]
                for i, line in enumerate(lines):
                    line = LineColorizer.sanitize(line)
                    colored = LineColorizer.color_e_line(line, "error", is_first=i == 0)
                    self._p(f"      {c_emsg('E')}  {colored}")
            return
        if self.bdd.pending_file:
            self._open_file_group(self.bdd.pending_file)
            self.bdd.pending_file = None
        self._bdd_flush_scenario(r.outcome, r.short_msg)

    def _render_bdd_skip(self, r: TestResult) -> None:
        """Render a skipped BDD scenario."""
        self._open_file_group(r.file)
        feature_name = self.bdd.scenario_names.get(r.nodeid + "__feature__", "")
        if feature_name and feature_name != self.bdd.cur_feature:
            if self.bdd.any_feature_printed:
                self._p()
            self._p(c_bdd_feature(f"  Feature: {feature_name}"))
            self.bdd.cur_feature = feature_name
            self.bdd.any_feature_printed = True
        if self.bdd.last_was_full_step:
            self._p()
        color_fn = _OUTCOME_COLOR["skipped"]
        badge = _BADGE["skipped"]
        scenario_name = self.bdd.scenario_names[r.nodeid]
        self._p(
            f"    {color_fn('---')} {badge}  {color_fn(f'Scenario: {scenario_name}')}"
        )
        if r.short_msg:
            sanitized = LineColorizer.sanitize(r.short_msg)
            colored = LineColorizer.color_e_line(sanitized, "skipped", is_first=True)
            self._p(f"      {c_emsg('E')}  {colored}")
        self.bdd.last_was_full_step = False

    def _render_normal(self, r: TestResult) -> None:
        """Render a normal (non-BDD) test result."""
        badge = _BADGE.get(r.outcome, r.outcome.upper())
        color_fn = _OUTCOME_COLOR.get(r.outcome, c_dim)
        dur = c_dim(f"  {r.duration * 1000:.1f}ms")

        if "::" in r.name:
            class_name, method_name = r.name.split("::", 1)
            if class_name != self._cur_class:
                if self._cur_class is not None:
                    self._p()
                self._p(f"  {LineColorizer.sanitize(class_name)}")
                self._cur_class = class_name
            # display_name = method_name
            display_name = LineColorizer.sanitize(method_name)
        else:
            self._cur_class = None
            display_name = LineColorizer.sanitize(r.name)

        self._p(f"  {color_fn('---')} {badge}  {display_name}{dur}")

        if r.short_msg:
            lines = [
                ln for ln in r.short_msg.splitlines() if not LineColorizer.is_noise(ln)
            ]
            for i, line in enumerate(lines):
                line = LineColorizer.sanitize(line)
                colored = LineColorizer.color_e_line(line, r.outcome, is_first=i == 0)
                self._p(f"    {c_emsg('E')}  {colored}")

        if r.outcome not in ("passed", "xfailed"):
            for section_name, content in r.sections:
                if not content.strip():
                    continue
                self._p(
                    f"    {c_section('── ' + LineColorizer.sanitize(section_name) + ' ──')}"
                )
                for ln in content.rstrip().splitlines():
                    self._p(f"    {LineColorizer.sanitize(ln)}")

    def _bdd_flush_scenario(self, outcome: str, short_msg: Optional[str]) -> None:
        """
        Flush the buffered scenario lines, applying xfail/xpass correction
        to the last step before printing.
        """
        if outcome in ("xfailed", "xpassed") and self.bdd.last_step_idx >= 0:
            last = self.bdd.scenario_buf[self.bdd.last_step_idx]
            if isinstance(last, _BDDStep):
                last.outcome = outcome
                last.short_msg = short_msg

        needs_steps = outcome in ("failed", "error") or self.bdd.steps_mode
        if not needs_steps:
            total_dur = sum(
                item.duration
                for item in self.bdd.scenario_buf
                if isinstance(item, _BDDStep)
            )
            scenario_line = next(
                (
                    item
                    for item in reversed(self.bdd.scenario_buf)
                    if isinstance(item, str) and "Scenario:" in item
                ),
                None,
            )
            for item in self.bdd.scenario_buf:
                if isinstance(item, str) and "Scenario:" not in item:
                    if item == "" and not self.bdd.last_was_full_step:
                        continue
                    self._p(item)
            self.bdd.last_was_full_step = False
            if scenario_line is not None:
                badge = _BADGE.get(outcome, outcome.upper())
                color_fn = _OUTCOME_COLOR.get(outcome, c_dim)
                dur = c_dim(f"  {total_dur * 1000:.1f}ms")
                plain = re.sub(r"\033\[[\d;]*m", "", scenario_line).strip()
                self._p(f"    {color_fn('---')} {badge}  {color_fn(plain)}{dur}")
        else:
            for item in self.bdd.scenario_buf:
                if isinstance(item, str):
                    self._p(item)
                else:
                    self._render_bdd_step_line(item)
            self.bdd.last_was_full_step = True

        self.bdd.scenario_buf = []
        self.bdd.last_step_idx = -1

    # ── BDD delegate methods (called by module-level hooks) ───────────────────

    def _bdd_before_scenario(self, _request, feature, scenario) -> None:
        file, _ = self.split_nodeid(_request.node.nodeid)
        self.bdd.pending_file = file
        feature_name = getattr(feature, "name", "")
        self.bdd.scenario_buf = []
        if feature_name and feature_name != self.bdd.cur_feature:
            if self.bdd.any_feature_printed:
                self.bdd.scenario_buf.append("")
            self.bdd.scenario_buf.append(c_bdd_feature(f"  Feature: {feature_name}"))
            self.bdd.cur_feature = feature_name
            self.bdd.any_feature_printed = True
            self.bdd.first_in_file = False
        elif not self.bdd.first_in_file:
            self.bdd.scenario_buf.append("")
        self.bdd.first_in_file = False
        self.bdd.scenario_buf.append(c_bdd_scenario(f"    Scenario: {scenario.name}"))
        self.bdd.last_step_idx = -1

    def _bdd_before_step(self, _request, _feature, _scenario, step, _step_func) -> None:
        bg = getattr(_feature, "background", None)
        bg_steps = list(bg.steps) if bg and hasattr(bg, "steps") else []
        if bg_steps and step is bg_steps[0]:
            self.bdd.scenario_buf.append(f"       {c_dim('Background:')}")
        self.bdd.step_t0[id(step)] = time.monotonic()

    def _bdd_after_step(
        self, request, _feature, _scenario, step, _step_func, _step_func_args
    ) -> None:
        t0 = self.bdd.step_t0.pop(id(step), time.monotonic())
        duration = time.monotonic() - t0
        bdd_step = _BDDStep(
            step=step, outcome="passed", duration=duration, short_msg=None
        )
        self.bdd.scenario_buf.append(bdd_step)
        self.bdd.last_step_idx = len(self.bdd.scenario_buf) - 1
        self.bdd.handled.add(request.node.nodeid)

    def _bdd_step_error(
        self, request, _feature, _scenario, step, _step_func, _step_func_args, exception
    ) -> None:
        t0 = self.bdd.step_t0.pop(id(step), time.monotonic())
        duration = time.monotonic() - t0
        outcome = "failed" if isinstance(exception, AssertionError) else "error"
        short_msg = self.extract_exception_msg(exception)
        bdd_step = _BDDStep(
            step=step, outcome=outcome, duration=duration, short_msg=short_msg
        )
        self.bdd.scenario_buf.append(bdd_step)
        self.bdd.last_step_idx = len(self.bdd.scenario_buf) - 1
        self.bdd.handled.add(request.node.nodeid)

    def _bdd_step_func_lookup_error(
        self, request, _feature, _scenario, step, exception
    ) -> None:
        t0 = self.bdd.step_t0.pop(id(step), time.monotonic())
        duration = time.monotonic() - t0
        short_msg = self.extract_exception_msg(exception)
        bdd_step = _BDDStep(
            step=step, outcome="error", duration=duration, short_msg=short_msg
        )
        self.bdd.scenario_buf.append(bdd_step)
        self.bdd.last_step_idx = len(self.bdd.scenario_buf) - 1
        self.bdd.handled.add(request.node.nodeid)

    # ── pytest hooks ──────────────────────────────────────────────────────────

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self) -> None:
        """Record session start time."""
        self.session.t0 = time.monotonic()
        self._p()

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session) -> None:
        """Print the 'collected N tests' header and index BDD scenario names."""
        n = len(session.items)
        noun = "test" if n == 1 else "tests"
        self._p(f"{c_dim('collected')} {c_bold(str(n))} {c_dim(noun)}")
        self._p()
        for item in session.items:
            fn = getattr(item, "function", None)
            if fn is None:
                continue
            scenario_obj = getattr(fn, "__scenario__", None)
            if scenario_obj is not None:
                self.bdd.scenario_names[item.nodeid] = getattr(
                    scenario_obj, "name", None
                ) or str(scenario_obj)
                feature = getattr(scenario_obj, "feature", None)
                if feature:
                    self.bdd.scenario_names[item.nodeid + "__feature__"] = getattr(
                        feature, "name", ""
                    )
            elif fn.__doc__:
                parts = fn.__doc__.split(": ", 1)
                if len(parts) == 2:
                    self.bdd.scenario_names[item.nodeid] = parts[1]

    @pytest.hookimpl(tryfirst=True)
    def pytest_collectreport(self, report) -> None:
        """Capture collection-phase errors: bad imports, syntax errors, etc."""
        if report.failed and report.longrepr:
            self.session.col_errors.append(
                (str(report.nodeid), str(report.longrepr).strip())
            )

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report) -> None:
        """Handle each test phase report and render the result line."""
        if report.when != "call" and report.outcome == "passed":
            return

        outcome = self.classify(report)
        short_msg = self.extract_short(report, outcome)
        file, name = self.split_nodeid(report.nodeid)

        result = TestResult(
            nodeid=report.nodeid,
            file=file,
            name=name,
            outcome=outcome,
            duration=getattr(report, "duration", 0.0),
            short_msg=short_msg,
            sections=list(report.sections),
        )

        self._open_file_group(file)
        self._file_buf.append(result)
        self.session.counts[result.outcome] = (
            self.session.counts.get(result.outcome, 0) + 1
        )
        self._render_result(result)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self) -> None:
        """Flush the last file summary and print the global Total line."""
        if self._cur_file is not None:
            self._flush_file_summary()

        if self.session.col_errors:
            self._p()
            self._p(c_bold(c_error("COLLECTION ERRORS")))
            for nodeid, msg in self.session.col_errors:
                self._p(f"  {c_error('⚠')}  {LineColorizer.sanitize(nodeid)}")
                for line in msg.splitlines():
                    self._p(f"    {c_dim(LineColorizer.sanitize(line))}")

        elapsed = time.monotonic() - self.session.t0
        counts: Dict[str, int] = self.session.counts
        # for r in self.session.results:
        #     counts[r.outcome] = counts.get(r.outcome, 0) + 1

        parts = [_SUMMARY_FMT[o](n) for o in _OUTCOME_ORDER if (n := counts.get(o))]
        summary = ", ".join(parts) if parts else c_dim("no tests ran")
        self._p()
        self._p(f"{c_bold('Total:')} {summary}  {c_dim(f'in {elapsed:.2f}s')}")
        self._p()
