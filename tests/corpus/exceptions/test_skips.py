# tests/corpus/test_skips.py
"""
Covers all skip/xfail variants:
  skip (decorator), skipif, imperative skip,
  xfail expected, xpass unexpected, xfail strict,
  xfail(raises=) exception-scoped, xfail(run=False) no-run,
  pytest.importorskip.

Each variant produces a distinct badge and reason string that exercises
the formatter's skip/xfail classification and reason-extraction paths.
"""
import sys
import pytest


# ── Skip ─────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="demonstrating unconditional skip")
def test_skip_unconditional():
    """Decorator skip — reason surfaced on the E line in yellow."""
    assert False   # never reached


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only feature")
def test_skip_platform_conditional():
    """skipif — skips on Linux/macOS, runs on Windows. Reason shown when skipped."""
    pass


def test_skip_imperative():
    """pytest.skip() mid-test — same SKIP badge and yellow E-line as decorator."""
    pytest.skip("skipping imperatively mid-test")
    assert False   # never reached


def test_skip_import():
    """pytest.importorskip — skips when the named module is not installed.
    Uses a deliberately nonexistent name so it always skips in this corpus."""
    pytest.importorskip("_nonexistent_module_corpus_xyz")
    assert True   # never reached if module is missing


# ── xfail ────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="known bug — assert will fail as expected")
def test_xfail_expected_failure():
    """Marked xfail, actually fails → XFAIL badge (gray). Reason on E-line."""
    assert 1 == 2


@pytest.mark.xfail(reason="this test unexpectedly passes")
def test_xpass_unexpected_pass():
    """Marked xfail, actually passes → XPASS badge (yellow).
    Exercises the xpassed branch of classify() and the wasxfail reason extraction."""
    assert 1 == 1


@pytest.mark.xfail(strict=True, reason="strict: passing when expected to fail is an error")
def test_xfail_strict_becomes_fail():
    """strict=True + test passes → reported as FAILED (not XPASS).
    The only way to produce a strict-xfail badge in the formatter."""
    assert 1 == 1


@pytest.mark.xfail(raises=ValueError, reason="only xfail if a ValueError is raised")
def test_xfail_specific_exception_matches():
    """xfail(raises=ValueError) and a ValueError IS raised → XFAIL.
    If a different exception were raised it would be reported as ERROR."""
    raise ValueError("this specific error was expected")


@pytest.mark.xfail(raises=ValueError, reason="wrong exception type — becomes ERROR")
def test_xfail_specific_exception_mismatch():
    """xfail(raises=ValueError) but a TypeError is raised → ERROR, not XFAIL.
    Verifies the formatter distinguishes this from a normal xfail."""
    raise TypeError("not the exception that was expected")


@pytest.mark.xfail(run=False, reason="too unstable to execute safely")
def test_xfail_no_run():
    """xfail(run=False) — test body is never executed; marked xfail immediately.
    Distinct from skip: it counts as xfailed, not skipped, in the summary."""
    assert False   # never reached
