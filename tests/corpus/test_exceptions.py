# tests/corpus/test_exceptions.py
"""
Covers unexpected exceptions raised inside tests and pytest.raises usage:
  AttributeError, TypeError, KeyError, ValueError, IndexError,
  RuntimeError, NameError, ZeroDivisionError, exception chaining,
  raises-passes, raises-with-match-passes, raises-wrong-exception,
  raises-no-exception, raises-match-fails.

Every non-raises test here is a deliberate crash. Every raises test that
is a *passing* case is included as a baseline to confirm the formatter
shows PASS for it, not a false failure.
"""
import pytest


# ── pytest.raises — passing cases (formatter must show PASS) ─────────────────

def test_raises_correct_exception():
    """Correct exception type caught — test passes."""
    with pytest.raises(ValueError):
        int("not a number")

def test_raises_with_match():
    """Exception type and message pattern both match — test passes."""
    with pytest.raises(AttributeError, match="has no attribute"):
        None.get("x")  # type: ignore[union-attr]


# ── pytest.raises — failing cases ────────────────────────────────────────────

def test_raises_wrong_exception():
    """Wrong exception type — pytest wraps the mismatch as a FAILED test."""
    with pytest.raises(ValueError):
        raise TypeError("this is not a ValueError")

def test_raises_no_exception():
    """No exception raised — 'DID NOT RAISE' reported as FAILED."""
    with pytest.raises(ValueError):
        _ = 1 + 1  # noqa — intentionally benign

def test_raises_match_fails():
    """Correct exception type but message doesn't match the pattern.
    Exercises the regex-mismatch path — distinct E-line shape from wrong-type."""
    with pytest.raises(ValueError, match=r"specific pattern"):
        raise ValueError("completely different message")


# ── Attribute errors ──────────────────────────────────────────────────────────

def test_attribute_error_none():
    """AttributeError on None — mirrors 'NoneType has no attribute get' screenshot."""
    obj = None
    _ = obj.get("x")  # type: ignore[union-attr]

def test_attribute_error_object():
    """AttributeError on a real object — missing method on a known type."""
    _ = (42).nonexistent_method()  # type: ignore[attr-defined]


# ── Type errors ───────────────────────────────────────────────────────────────

def test_type_error_add():
    """TypeError: unsupported operand — int + str."""
    _ = "string" + 42  # type: ignore[operator]

def test_type_error_call():
    """TypeError: object is not callable — calling a non-callable."""
    value = 42
    value()  # type: ignore[operator]


# ── Key / index errors ────────────────────────────────────────────────────────

def test_key_error():
    """KeyError — missing dict key; key repr appears quoted in the E-line."""
    d = {"a": 1}
    _ = d["b"]

def test_index_error():
    """IndexError — out-of-range list access."""
    lst = [1, 2, 3]
    _ = lst[10]


# ── Value errors ──────────────────────────────────────────────────────────────

def test_value_error_int():
    """ValueError from int() on non-numeric string."""
    int("not_a_number")

def test_value_error_unpack():
    """ValueError from unpacking the wrong number of values."""
    a, b = [1, 2, 3]  # noqa: F841


# ── Name errors ───────────────────────────────────────────────────────────────

def test_name_error():
    """NameError — referencing an undefined variable."""
    _ = undefined_variable_xyz  # type: ignore[name-defined]  # noqa: F821


# ── Arithmetic errors ─────────────────────────────────────────────────────────

def test_zero_division():
    """ZeroDivisionError — division by zero."""
    _ = 1 / 0


# ── Runtime errors ────────────────────────────────────────────────────────────

def test_runtime_error():
    """RuntimeError — explicit raise; exercises the generic exception shape."""
    raise RuntimeError("something went wrong internally")


# ── Exception chaining ────────────────────────────────────────────────────────

def test_exception_chaining():
    """raise X from Y — produces a chained traceback with 'The above exception
    was the direct cause of the following exception'. Verifies the formatter
    extracts only the final exception's E-lines, not the full chain."""
    try:
        int("not_a_number")
    except ValueError as exc:
        raise RuntimeError("conversion pipeline failed") from exc
