# tests/corpus/conftest.py
"""
Shared fixtures for the formatter validation corpus.
"""
import time
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
    time.sleep(0.02)
    return "slow"


@pytest.fixture(params=["alpha", "beta", "gamma"])
def parametrized_fixture(request):
    """Fixture-level params — produces one test instance per value.
    Distinct from @pytest.mark.parametrize: the param appears in the
    node ID as test_name[alpha], test_name[beta], etc."""
    return {"label": request.param, "value": len(request.param)}
