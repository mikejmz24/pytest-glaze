# tests/conftest.py
"""Shared test infrastructure for all pytest-glaze unit tests."""
import pytest
import pytest_glaze._colors as _colors


@pytest.fixture(autouse=True)
def force_color(monkeypatch):
    """Force ANSI output regardless of TTY detection."""
    monkeypatch.setattr(_colors, "_NO_COLOR", False)
