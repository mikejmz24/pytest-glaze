# tests/corpus/acceptance/conftest.py
"""Shared fixtures for acceptance tests."""

from __future__ import annotations

import pytest

from pytest_glaze import FormatterPlugin


@pytest.fixture
def glaze() -> FormatterPlugin:
    """Fresh FormatterPlugin with an initial file group opened."""
    p = FormatterPlugin()
    with p.capture():
        p.open_file("tests/bdd/test_checkout.py")
    p.test_outcome = "passed"
    p.test_short_msg = None
    return p


@pytest.fixture
def plugin() -> FormatterPlugin:
    """Fresh FormatterPlugin for rendering tests."""
    return FormatterPlugin()


@pytest.fixture
def theme_config() -> dict:
    """Default theme config for theme selection tests."""
    return {"theme_flag": "auto"}
