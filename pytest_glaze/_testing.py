"""
pytest_glaze/_testing.py — _FormatterTestingMixin: testing-only interface.

Mixed into FormatterPlugin to expose protected machinery to the test suite
without leaking it into the production API. Methods here delegate to
attributes/methods defined on FormatterPlugin; type-ignores are required
because the mixin alone has no knowledge of those members.

Not part of the public API. Do not import from production code.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, List, Optional

from pytest_glaze._types import TestResult


class _FormatterTestingMixin:
    """
    Testing interface for FormatterPlugin.

    Provides public methods for unit testing without accessing protected members.
    Do not call these methods in production code.
    """

    @contextmanager
    def capture(self) -> "Generator[List[str], None, None]":
        """Capture printed output as a list of strings. For testing only."""
        lines: List[str] = []
        self.session.output_buf = lines  # type: ignore[attr-defined]
        try:
            yield lines
        finally:
            self.session.output_buf = None  # type: ignore[attr-defined]

    def render_result(self, result: "TestResult") -> "List[str]":
        """Render a result and return printed lines. For testing only."""
        with self.capture() as lines:
            self._open_file_group(result.file)  # type: ignore[attr-defined]
            self._file_buf.append(result)  # type: ignore[attr-defined]
            self.session.counts[result.outcome] = (  # type: ignore[attr-defined]
                self.session.counts.get(result.outcome, 0) + 1  # type: ignore[attr-defined]
            )
            self._render_result(result)  # type: ignore[attr-defined]
        return lines

    def render_results(self, results: "List[TestResult]") -> "List[str]":
        """Render multiple results and return printed lines. For testing only."""
        with self.capture() as lines:
            for r in results:
                self._open_file_group(r.file)  # type: ignore[attr-defined]
                self._file_buf.append(r)  # type: ignore[attr-defined]
                self.session.counts[r.outcome] = (  # type: ignore[attr-defined]
                    self.session.counts.get(r.outcome, 0) + 1  # type: ignore[attr-defined]
                )
                self._render_result(r)  # type: ignore[attr-defined]
        return lines

    def flush_scenario(
        self, outcome: str, short_msg: "Optional[str]" = None
    ) -> "List[str]":
        """Flush BDD scenario buffer and return printed lines. For testing only."""
        with self.capture() as lines:
            self._bdd_flush_scenario(outcome, short_msg)  # type: ignore[attr-defined]
        return lines

    def open_file(self, file: str) -> "List[str]":
        """Open a file group and return printed lines. For testing only."""
        with self.capture() as lines:
            self._open_file_group(file)  # type: ignore[attr-defined]
        return lines

    def flush_file_summary(self) -> "List[str]":
        """Flush file summary and return printed lines. For testing only."""
        with self.capture() as lines:
            self._flush_file_summary()  # type: ignore[attr-defined]
        return lines

    def simulate_before_scenario(self, *args) -> None:
        """Simulate pytest_bdd_before_scenario hook. For testing only."""
        self._bdd_before_scenario(*args)  # type: ignore[attr-defined]

    def simulate_before_step(self, *args) -> None:
        """Simulate pytest_bdd_before_step hook. For testing only."""
        self._bdd_before_step(*args)  # type: ignore[attr-defined]

    def simulate_after_step(self, *args) -> None:
        """Simulate pytest_bdd_after_step hook. For testing only."""
        self._bdd_after_step(*args)  # type: ignore[attr-defined]

    def simulate_step_error(self, *args) -> None:
        """Simulate pytest_bdd_step_error hook. For testing only."""
        self._bdd_step_error(*args)  # type: ignore[attr-defined]

    def simulate_step_func_lookup_error(self, *args) -> None:
        """Simulate pytest_bdd_step_func_lookup_error hook. For testing only."""
        self._bdd_step_func_lookup_error(*args)  # type: ignore[attr-defined]

    def set_cur_file(self, file: "Optional[str]") -> None:
        """Set the current file. For testing only."""
        self._cur_file = file  # type: ignore[attr-defined]

    @property
    def file_buf(self) -> "List[TestResult]":
        """Current file buffer. For testing only."""
        return self._file_buf  # type: ignore[attr-defined]

    @property
    def cur_file(self) -> "Optional[str]":
        """Currently open file. For testing only."""
        return self._cur_file  # type: ignore[attr-defined]
