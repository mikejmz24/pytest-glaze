# tests/corpus/test_assertions.py
"""
Covers every assertion introspection shape pytest produces:
  int equality, string equality, multiline string diff, list diff,
  dict diff, set diff, boolean, None check, membership, custom message,
  approximate equality, chained comparison.
"""
import pytest


# ── Passing ───────────────────────────────────────────────────────────────────

def test_pass_int():
    assert 1 + 1 == 2


def test_pass_string():
    assert "hello".upper() == "HELLO"


def test_pass_with_fixture(clean_fixture):
    assert clean_fixture["value"] == 42


# ── Failing ───────────────────────────────────────────────────────────────────

def test_fail_int_equality():
    result = 3
    assert result == 30                                  # mirrors screenshot


def test_fail_string_short():
    assert "INTGPT-109" == "INTGPT-1091"                # mirrors screenshot


def test_fail_string_multiline():
    assert "hello\nworld\nxxx" == "hello\nworld\nyyy"


def test_fail_list():
    assert ["Global Launch"] == ["Global Launches"]     # mirrors screenshot


def test_fail_dict():
    assert {"a": 1, "b": 2, "c": 3} == {"a": 1, "b": 999, "d": 4}


def test_fail_set():
    assert {1, 2, 3} == {1, 2, 4}


def test_fail_bool():
    assert False, "this flag should be True"


def test_fail_none_check():
    value = None
    assert value is not None


def test_fail_in():
    assert "foo" in ["bar", "baz"]


def test_fail_not_in():
    assert "bar" in {"foo": 1}


def test_fail_custom_message():
    result, expected = 5, 15
    assert result == expected, f"got {result}, expected {expected}"


def test_fail_approximate():
    import math
    assert math.pi == pytest.approx(3.14, abs=0.001)


def test_fail_chained_comparison():
    x = 5
    assert 0 < x < 3
