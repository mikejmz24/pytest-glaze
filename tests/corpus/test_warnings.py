# tests/corpus/test_warnings.py
"""
Covers pytest.warns and warnings surfacing:
  warns-passes, warns-wrong-type, warns-no-warning.
"""
import warnings
import pytest


def test_warns_pass():
    with pytest.warns(UserWarning):
        warnings.warn("expected UserWarning", UserWarning)


def test_warns_fail_wrong_category():
    with pytest.warns(UserWarning):
        warnings.warn("wrong category", DeprecationWarning)


def test_warns_fail_no_warning():
    with pytest.warns(UserWarning):
        _ = 1 + 1   # no warning raised at all
