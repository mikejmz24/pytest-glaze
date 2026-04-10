# tests/corpus/test_parametrize.py
"""
Covers parametrize shapes:
  single param, multiple params, custom IDs, mixed pass/fail within a set,
  pytest.param with id=, pytest.param with marks (xfail / skip per-case),
  combined / matrix parametrize, None and complex objects as param values.

Every shape here produces a distinct node-ID format that exercises the
_split_nodeid() call and per-file grouping in the formatter.
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
    """Mixed pass/fail — verifies per-file summary counts parametrized variants."""
    assert value * value == expected


# ── Multiple params with custom IDs ──────────────────────────────────────────

@pytest.mark.parametrize("a,b,result", [
    (1,  2,  3),    # pass
    (10, 20, 30),   # pass
    (5,  5,  11),   # fail
], ids=["small-add", "large-add", "fail-case"])
def test_add(a, b, result):
    """Human-readable IDs in node names — formatter must preserve brackets."""
    assert a + b == result


# ── pytest.param with explicit id= ───────────────────────────────────────────

@pytest.mark.parametrize("x,y,expected", [
    pytest.param(0,   0,   0,   id="zeros"),
    pytest.param(1,   1,   2,   id="unit"),
    pytest.param(100, 200, 999, id="large-fail"),   # fail: 100+200=300
])
def test_explicit_ids(x, y, expected):
    """pytest.param with id= — node IDs become test_explicit_ids[zeros] etc."""
    assert x + y == expected


# ── pytest.param with per-case marks ─────────────────────────────────────────

@pytest.mark.parametrize("value", [
    pytest.param(1,  id="passes"),
    pytest.param(99, id="xfail-case", marks=pytest.mark.xfail(reason="known regression")),
    pytest.param(50, id="skip-case",  marks=pytest.mark.skip(reason="not implemented yet")),
])
def test_param_with_marks(value):
    """Per-case marks — one PASS, one XFAIL, one SKIP from the same test function.
    Exercises the formatter showing three different badges in a single file group."""
    assert value < 50


# ── String parametrize — mirrors screenshot label scenario ────────────────────

@pytest.mark.parametrize("priority,expected_label", [
    ("P1", "P1 - Critical"),   # pass
    ("P2", "P2 - High"),       # pass
    ("P3", "P3 - High"),       # fail: should be "P3 - Low"
])
def test_priority_label(priority, expected_label):
    mapping = {"P1": "P1 - Critical", "P2": "P2 - High", "P3": "P3 - Low"}
    assert mapping[priority] == expected_label


# ── None and complex objects as param values ──────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (None,    "none"),   # None in param — repr is 'None', ID is 'value0'
    ("hello", "hello"),  # pass
    (42,      "42"),     # pass
    ([1, 2],  "list"),   # fail: str([1,2]) != "list" — list as param value
])
def test_param_with_none_and_complex(value, expected):
    """None and list as param values — exercises unusual repr in node IDs."""
    result = "none" if value is None else str(value).lower()
    assert result == expected


# ── Combined / matrix parametrize ────────────────────────────────────────────

@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [10, 20])
def test_matrix(x, y):
    """Two @parametrize decorators create a 2×2 matrix of four test instances.
    Node IDs: test_matrix[10-1], test_matrix[10-2], test_matrix[20-1], etc.
    assert x*y > 25 fails for (1,10) only — mixed output in a dense group."""
    assert x * y > 25


# ── All passing — verifies clean parametrize block ───────────────────────────

@pytest.mark.parametrize("s,expected", [
    ("hello",  "HELLO"),
    ("world",  "WORLD"),
    ("pytest", "PYTEST"),
])
def test_upper(s, expected):
    """All pass — formatter must show three consecutive PASS lines, no summary noise."""
    assert s.upper() == expected
