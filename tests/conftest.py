# tests/conftest.py
"""
Shared test infrastructure for all pytest-glaze unit tests.
"""
import pytest
import pytest_glaze


@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output even when stdout is not a tty (CI / piped output).

    Applied automatically to every test in the suite.  Parser and plugin
    tests don't produce ANSI, so patching _NO_COLOR has no visible effect
    on them — it only matters for test_colorizer.py.
    """
    monkeypatch.setattr(pytest_glaze, "_NO_COLOR", False)
