# tests/corpus/conftest.py
"""Shared fixtures for corpus tests."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def session_config() -> dict:
    """Session-scoped config available to all BDD steps."""
    return {"env": "test", "version": "1.0.0", "debug": False}
