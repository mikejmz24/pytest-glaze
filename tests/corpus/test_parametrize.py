# tests/corpus/test_parametrize.py
"""
Covers parametrize shapes:
  single param, multiple params, custom IDs, mixed pass/fail within a set.
"""
import pytest


# ── Single param — mix of pass and fail ──────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (2,  4),    # pass
    (3,  9),    # pass
    (4,  15),   # fail: 4*4=16, not 15
    (5,  25),   # pass
    (10, 99),   # fail: 10*10=100, not 99
])
def test_square(value, expected):
    assert value * value == expected


# ── Multiple params with custom IDs ──────────────────────────────────────────

@pytest.mark.parametrize("a,b,result", [
    (1,  2,  3),    # pass
    (10, 20, 30),   # pass
    (5,  5,  11),   # fail
], ids=["small-add", "large-add", "fail-case"])
def test_add(a, b, result):
    assert a + b == result


# ── String parametrize — mirrors screenshot label scenario ────────────────────

@pytest.mark.parametrize("priority,expected_label", [
    ("P1", "P1 - Critical"),   # pass
    ("P2", "P2 - High"),       # pass
    ("P3", "P3 - High"),       # fail: should be "P3 - Low"
])
def test_priority_label(priority, expected_label):
    mapping = {"P1": "P1 - Critical", "P2": "P2 - High", "P3": "P3 - Low"}
    assert mapping[priority] == expected_label


# ── All passing — verifies clean parametrize block ───────────────────────────

@pytest.mark.parametrize("s,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("pytest", "PYTEST"),
])
def test_upper(s, expected):
    assert s.upper() == expected
