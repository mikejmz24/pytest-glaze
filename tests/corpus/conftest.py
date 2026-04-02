# tests/corpus/conftest.py
"""
Shared fixtures for the formatter validation corpus.
"""
import pytest


@pytest.fixture
def clean_fixture():
    """A normal fixture that works fine."""
    return {"value": 42, "label": "ok"}


@pytest.fixture
def broken_setup():
    """Fixture that always fails on setup → ERROR outcome."""
    raise RuntimeError("Setup exploded intentionally")


@pytest.fixture
def broken_teardown():
    """Fixture that passes setup but fails on teardown → ERROR outcome."""
    yield "value"
    raise RuntimeError("Teardown exploded intentionally")


@pytest.fixture
def slow_fixture():
    """Fixture with a small sleep — confirms duration display."""
    import time
    time.sleep(0.02)
    return "slow"
