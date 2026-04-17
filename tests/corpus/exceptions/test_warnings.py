# tests/corpus/test_warnings.py
"""
Covers pytest.warns and warnings surfacing:
  warns-passes (basic, with match=), warns-fails (no warning, wrong category,
  match mismatch), recwarn fixture, multiple warnings in one block,
  DeprecationWarning and FutureWarning shapes, and unhandled warnings
  (warnings emitted outside pytest.warns — appear in pytest's warning summary,
  not in per-test E-lines).
"""
import warnings
import pytest


# ── pytest.warns — passing cases ──────────────────────────────────────────────

def test_warns_pass():
    """Correct category issued — test passes."""
    with pytest.warns(UserWarning):
        warnings.warn("expected UserWarning", UserWarning)


def test_warns_pass_with_match():
    """Correct category AND message matches the regex — test passes."""
    with pytest.warns(UserWarning, match=r"expected"):
        warnings.warn("this is the expected warning message", UserWarning)


def test_warns_pass_deprecation():
    """DeprecationWarning — the most common warning type in real codebases."""
    with pytest.warns(DeprecationWarning):
        warnings.warn("this feature is deprecated", DeprecationWarning)


def test_warns_pass_multiple():
    """Multiple warnings in one block — pytest.warns passes if at least one matches."""
    with pytest.warns(UserWarning):
        warnings.warn("first warning", UserWarning)
        warnings.warn("second warning", UserWarning)


# ── pytest.warns — failing cases ──────────────────────────────────────────────

def test_warns_fail_no_warning():
    """No warning raised at all — 'DID NOT WARN' failure shape."""
    with pytest.warns(UserWarning):
        _ = 1 + 1   # no warning emitted


def test_warns_fail_wrong_category():
    """Warning issued but wrong category — DeprecationWarning ≠ UserWarning."""
    with pytest.warns(UserWarning):
        warnings.warn("wrong category", DeprecationWarning)


def test_warns_fail_match_mismatch():
    """Correct category issued, but message doesn't match the regex.
    Distinct E-line shape from wrong-category: the assert is about the pattern."""
    with pytest.warns(UserWarning, match=r"very specific phrase"):
        warnings.warn("completely unrelated message", UserWarning)


def test_warns_fail_future_warning():
    """FutureWarning expected but UserWarning issued — exercises a third category."""
    with pytest.warns(FutureWarning):
        warnings.warn("not a future warning", UserWarning)


# ── recwarn fixture ───────────────────────────────────────────────────────────

def test_recwarn_pass(recwarn):
    """recwarn collects all warnings without requiring a specific category."""
    warnings.warn("any warning", UserWarning)
    assert len(recwarn) == 1
    assert recwarn[0].category is UserWarning
    assert "any warning" in str(recwarn[0].message)


def test_recwarn_fail_count(recwarn):
    """recwarn assertion on count — exercises int equality failure shape."""
    warnings.warn("one warning", UserWarning)
    assert len(recwarn) == 2   # only 1 was issued


def test_recwarn_fail_category(recwarn):
    """recwarn assertion on category — exercises identity failure shape."""
    warnings.warn("a deprecation", DeprecationWarning)
    assert recwarn[0].category is UserWarning   # wrong: it's DeprecationWarning


# ── Unhandled warnings (outside pytest.warns) ─────────────────────────────────
# These appear in pytest's warning summary section, NOT in per-test E-lines.
# Verifies the formatter doesn't inject spurious section content for them.

def test_unhandled_warning_pass():
    """Warning emitted without pytest.warns on a passing test.
    Appears in the global warnings summary; formatter shows no section for it."""
    warnings.warn("unhandled UserWarning — passes anyway", UserWarning)
    assert True


def test_unhandled_warning_fail():
    """Warning emitted without pytest.warns on a failing test.
    Verifies the formatter shows the assertion section but not a spurious
    warning section — warnings summary is global, not per-test."""
    warnings.warn("unhandled UserWarning on a failing test", UserWarning)
    assert False, "intentional failure with an unhandled warning"
