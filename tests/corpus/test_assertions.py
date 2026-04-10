# tests/corpus/test_assertions.py
"""
Covers every assertion introspection shape pytest produces so the formatter
is exercised on each distinct E-line path:

  Equality (==, !=), ordered comparisons (<, >, <=, >=), identity (is/is not),
  membership (in/not in), negation and bare truthiness, type checks, chained
  comparisons, string diffs (short/multiline/unicode), numeric (int/float/
  approximate), container types (list/dict/set/tuple/nested), large collections
  that trigger noise suppression, and custom assertion messages.
"""
import math
import pytest


# ── Passing — formatter must not corrupt passing output ───────────────────────

def test_pass_int():
    assert 1 + 1 == 2

def test_pass_string():
    assert "hello".upper() == "HELLO"

def test_pass_bool():
    assert True

def test_pass_none_check():
    value = 42
    assert value is not None

def test_pass_with_fixture(clean_fixture):
    assert clean_fixture["value"] == 42


# ── Equality — == and != ──────────────────────────────────────────────────────

def test_fail_int_equality():
    """assert X == Y — basic two-sided coloring; mirrors screenshot."""
    result = 3
    assert result == 30

def test_fail_inequality():
    """assert X != Y — inequality operator; both sides colored."""
    assert 1 != 1

def test_fail_float_equality():
    """Float without approx — classic 0.1+0.2 != 0.3 float imprecision."""
    assert 0.1 + 0.2 == 0.3


# ── String diffs ──────────────────────────────────────────────────────────────

def test_fail_string_short():
    """Short string — single-line assertion, inline +/- diff."""
    string_a: str = "INTGPT-109"
    string_b: str = "INTGPT-1091"
    assert string_a == string_b

def test_fail_string_multiline():
    """Multiline string — triggers full +/- unified diff block."""
    string_a: str = "hello\nworld\nxxx"
    string_b: str = "hello\nworld\nyyy"
    assert string_a == string_b

def test_fail_string_unicode():
    """Unicode — non-ASCII repr must pass through the colorizer cleanly."""
    assert "café" == "cafe"


# ── Ordered comparisons — <, >, <=, >= ───────────────────────────────────────

def test_fail_less_than():
    """assert X < Y."""
    x = 5
    assert x < 3

def test_fail_greater_than():
    """assert X > Y."""
    x = 1
    assert x > 10

def test_fail_less_than_or_equal():
    """assert X <= Y."""
    x = 5
    assert x <= 3

def test_fail_greater_than_or_equal():
    """assert X >= Y."""
    x = 1
    assert x >= 10

def test_fail_chained_comparison():
    """Chained a < b < c — pytest rewrites to the first failing sub-comparison."""
    x = 5
    assert 0 < x < 3


# ── Identity — is / is not ────────────────────────────────────────────────────

def test_fail_is_not_none():
    """assert X is not None — 'not None' rendered as one red unit."""
    value = None
    assert value is not None

def test_fail_is_none():
    """assert X is None — X in green, None in red."""
    value = 42
    assert value is None


# ── Membership — in / not in ──────────────────────────────────────────────────

def test_fail_in_list():
    """assert X in list — value absent from list."""
    assert "foo" in ["bar", "baz"]

def test_fail_in_dict():
    """assert X in dict — key-lookup failure; dict repr on the right side."""
    assert "bar" in {"foo": 1}

def test_fail_not_in():
    """assert X not in container — explicit not-in operator (distinct from 'in')."""
    assert "foo" not in ["foo", "bar"]


# ── Negation / bare truthiness ────────────────────────────────────────────────

def test_fail_bool():
    """assert False with custom message — message is E-line 1, assert is E-line 2."""
    assert False, "this flag should be True"

def test_fail_bool_variable():
    """assert bare variable — bare-assert path with a named identifier."""
    is_ready = False
    assert is_ready

def test_fail_not():
    """assert not True — bare negation; value goes bright red."""
    assert not True


# ── Type checks ───────────────────────────────────────────────────────────────

def test_fail_isinstance():
    """isinstance failure — bare-assert path; the where-clause adds a second line."""
    assert isinstance(42, str)


# ── Containers ────────────────────────────────────────────────────────────────

def test_fail_list():
    """List diff — triggers 'At index N diff:' context lines."""
    assert ["Global Launch"] == ["Global Launches"]

def test_fail_list_empty_vs_populated():
    """Empty vs non-empty — exercises the no-common-prefix diff path."""
    assert [] == [1, 2, 3]

def test_fail_tuple():
    """Tuple — same diff shape as list but with () repr."""
    assert (1, 2, 3) == (1, 2, 4)

def test_fail_dict():
    """Dict diff — triggers 'Differing items:' and '{k}: V != V' context lines."""
    assert {"a": 1, "b": 2, "c": 3} == {"a": 1, "b": 999, "d": 4}

def test_fail_dict_nested():
    """Nested dict — exercises deep repr in context comparison lines."""
    assert {"outer": {"inner": 1, "other": 2}} == {"outer": {"inner": 99, "other": 2}}

def test_fail_set():
    """Set diff — triggers 'Extra items in the left/right set:' prose lines.
    These must NOT be falsely colored green/red (they contain 'in' mid-sentence)."""
    assert {1, 2, 3} == {1, 2, 4}

def test_fail_large_list():
    """Large list — the only end-to-end exercise of the noise-suppression path.
    pytest emits 'Omitting N identical items, use -vv to show'; the formatter
    must suppress it. Only 'At index 30 diff: 999 != 1000' should appear."""
    a = list(range(30)) + [999]
    b = list(range(30)) + [1000]
    assert a == b


# ── Custom messages ───────────────────────────────────────────────────────────

def test_fail_custom_message():
    """f-string message — message is E-line 1 (soft red), assert is E-line 2."""
    result, expected = 5, 15
    assert result == expected, f"got {result}, expected {expected}"

def test_fail_custom_message_none():
    """Message on a None check — combines a message string + is-not-None assert."""
    value = None
    assert value is not None, "value must be populated before processing"


# ── Approximate equality — pytest.approx variants ────────────────────────────

def test_fail_approx_abs():
    """Absolute tolerance — exercises Obtained/Expected label lines."""
    assert math.pi == pytest.approx(3.14, abs=0.001)

def test_fail_approx_rel():
    """Relative tolerance — different ± repr from abs tolerance."""
    assert 1.0 == pytest.approx(2.0, rel=0.01)

def test_fail_approx_list():
    """List approx — Obtained/Expected show list reprs; table format may appear."""
    assert [0.1 + 0.2, 1.1 + 2.2] == pytest.approx([0.4, 3.4], abs=1e-9)

def test_fail_approx_dict():
    """Dict approx — Obtained/Expected show dict reprs with per-key tolerance."""
    assert {"x": 0.1 + 0.2, "y": 1.0} == pytest.approx({"x": 0.4, "y": 2.0}, abs=1e-9)
