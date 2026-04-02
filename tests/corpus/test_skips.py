# tests/corpus/test_skips.py
"""
Covers all skip/xfail variants:
  skip (decorator), skipif, imperative skip, xfail expected,
  xpass unexpected, xfail strict.
"""
import sys
import pytest


# ── Skip ─────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="demonstrating unconditional skip")
def test_skip_unconditional():
    assert False   # never reached


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only feature")
def test_skip_platform_conditional():
    pass


def test_skip_imperative():
    pytest.skip("skipping imperatively mid-test")
    assert False   # never reached


# ── xfail ────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="known bug — assert will fail as expected")
def test_xfail_expected_failure():
    assert 1 == 2   # fails → xfailed (expected)


@pytest.mark.xfail(reason="this test unexpectedly passes")
def test_xpass_unexpected_pass():
    assert 1 == 1   # passes → xpassed (unexpected)


@pytest.mark.xfail(strict=True, reason="strict: passing when expected to fail is an error")
def test_xfail_strict_becomes_fail():
    assert 1 == 1   # passes → strict xfail → reported as FAILED
