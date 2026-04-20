"""
tests/bdd/test_shared.py — Shared steps and hooks corpus for pytest-glaze.

Covers:
  - Step definitions from conftest.py reused across scenarios
  - pytest_bdd_apply_tag hook (@skip, @slow)
  - Session-scoped fixtures shared across scenarios
"""
from __future__ import annotations

from pytest_bdd import given, scenario, then


@scenario("features/shared.feature", "Application health check using shared steps")
def test_health_check() -> None: ...


@scenario("features/shared.feature", "Second scenario reusing shared application step")
def test_health_check_reuse() -> None: ...


@scenario("features/shared.feature", "Scenario skipped via Gherkin tag")
def test_gherkin_skip() -> None: ...


@scenario("features/shared.feature", "Slow scenario with registered mark")
def test_slow_scenario() -> None: ...


@scenario("features/shared.feature", "Session config is consistent across scenarios")
def test_session_config() -> None: ...


# ── Step only needed in test_shared.py ───────────────────────────────────────

@then("the app version is 1.0.0")
def assert_app_version(app: dict) -> None:
    assert app["config"]["version"] == "1.0.0"
