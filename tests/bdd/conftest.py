"""
tests/bdd/conftest.py — shared BDD steps and hooks available to all BDD test files.

Covers:
  - Shared step definitions reusable across feature files
  - pytest_bdd_apply_tag hook — custom tag → pytest mark conversion
  - Session-scoped fixture reused by steps
"""
from __future__ import annotations

import pytest
from pytest_bdd import given, then, when


# ── Session-scoped shared fixture ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def app_config() -> dict:
    """Session-scoped config available to all BDD steps."""
    return {"env": "test", "version": "1.0.0", "debug": False}


# ── Shared step definitions ───────────────────────────────────────────────────

@given("the application is running", target_fixture="app")
def app_is_running(app_config: dict) -> dict:
    return {"running": True, "config": app_config}


@given("the database is connected", target_fixture="db")
def db_connected() -> dict:
    return {"connected": True, "queries": []}


@when("a health check is performed", target_fixture="health")
def perform_health_check(app: dict) -> dict:
    return {"status": "ok", "version": app["config"]["version"]}


@then("the service is healthy")
def service_is_healthy(health: dict) -> None:
    assert health["status"] == "ok"


# ── pytest_bdd_apply_tag hook ─────────────────────────────────────────────────

def pytest_bdd_apply_tag(tag: str, function) -> bool | None:
    """
    Convert Gherkin tags to pytest marks.

    @skip     → pytest.mark.skip
    @slow     → pytest.mark.slow (registered mark)
    anything else → default pytest-bdd behavior
    """
    if tag == "skip":
        marker = pytest.mark.skip(reason="Skipped via @skip Gherkin tag")
        marker(function)
        return True
    return None
