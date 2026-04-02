# tests/corpus/test_exceptions.py
"""
Covers unexpected exceptions raised inside tests and pytest.raises usage:
  AttributeError, TypeError, KeyError, ValueError, IndexError,
  raises-passes, raises-wrong-exception, raises-no-exception.
"""
import pytest


# ── pytest.raises — passing cases ────────────────────────────────────────────

def test_raises_correct_exception():
    with pytest.raises(ValueError):
        int("not a number")


def test_raises_with_match():
    with pytest.raises(AttributeError, match="has no attribute"):
        None.get("x")  # type: ignore[union-attr]


# ── Unexpected exceptions ─────────────────────────────────────────────────────

def test_attribute_error():
    """Mirrors 'NoneType has no attribute get' in screenshot."""
    obj = None
    _ = obj.get("x")  # type: ignore[union-attr]


def test_type_error():
    _ = "string" + 42  # type: ignore[operator]  # noqa


def test_key_error():
    d = {"a": 1}
    _ = d["b"]


def test_value_error():
    int("not_a_number")


def test_index_error():
    lst = [1, 2, 3]
    _ = lst[10]


def test_zero_division():
    _ = 1 / 0


# ── pytest.raises — failing cases ────────────────────────────────────────────

def test_raises_wrong_exception():
    """Wrong exception type — pytest reports as FAILED."""
    with pytest.raises(ValueError):
        raise TypeError("this is not a ValueError")


def test_raises_no_exception():
    """No exception raised — pytest reports as FAILED."""
    with pytest.raises(ValueError):
        x = 1 + 1   # noqa — intentionally benign
