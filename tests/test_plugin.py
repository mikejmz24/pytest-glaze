# tests/test_plugin.py
"""
Unit tests for FormatterPlugin pure helper methods.

These tests use lightweight stubs (SimpleNamespace, _FakeLongrepr) instead
of real pytest report objects — no plugin machinery is needed.

Coverage:
  split_nodeid   — node-ID → (file, name) splitter
  classify       — raw report → canonical outcome string
  extract_short  — longrepr → inline E-line message
"""
from types import SimpleNamespace

import pytest_glaze
from pytest_glaze import FormatterPlugin


# ── split_nodeid ──────────────────────────────────────────────────────────────

class TestSplitNodeid:
    """Tests for FormatterPlugin.split_nodeid()."""

    def test_normal_nodeid(self):
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::test_bar") == (
            "tests/test_foo.py", "test_bar"
        )

    def test_parameterized_nodeid(self):
        """Bracket characters in the name must be preserved as-is."""
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::test_bar[x-y]") == (
            "tests/test_foo.py", "test_bar[x-y]"
        )

    def test_class_method_nodeid(self):
        """partition('::') splits on the first '::' only — rest stays in name."""
        assert FormatterPlugin.split_nodeid("tests/test_foo.py::TestClass::test_method") == (
            "tests/test_foo.py", "TestClass::test_method"
        )

    def test_no_separator_returns_full_path_as_name(self):
        """When there is no '::' the whole string is used as both file and name."""
        assert FormatterPlugin.split_nodeid("tests/test_foo.py") == (
            "tests/test_foo.py", "tests/test_foo.py"
        )


# ── classify ──────────────────────────────────────────────────────────────────

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


# ── extract_short ─────────────────────────────────────────────────────────────

class _FakeLongrepr:
    """Minimal longrepr stub — string representation only, with optional reprcrash."""

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
        assert len(result.splitlines()) == pytest_glaze.MAX_E_LINES

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
