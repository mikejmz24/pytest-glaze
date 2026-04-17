"""
tests/corpus/test_bdd_background.py — Background block corpus.

Covers:
  9.  Background steps + passing scenario
  10. Background steps + failing scenario

Background steps fire pytest_bdd_before_step / pytest_bdd_after_step
identically to regular steps. The formatter must handle them inline
within each scenario's step list.
"""
from __future__ import annotations

from pytest_bdd import given, scenario, then, when


# ── Scenario 9: Background + passing ─────────────────────────────────────────

@scenario("features/authentication.feature", "User logs in successfully")
def test_login_success() -> None: ...


# ── Scenario 10: Background + failing ────────────────────────────────────────

@scenario("features/authentication.feature", "User login fails with wrong password")
def test_login_failure() -> None: ...


# ── Background steps (shared across both scenarios) ───────────────────────────

@given("the database is available", target_fixture="db")
def db_available() -> dict:
    return {"connected": True, "tables": []}


@given("the user table is seeded")
def user_table_seeded(db: dict) -> None:
    db["tables"].append("users")


# ── Scenario 9 steps ──────────────────────────────────────────────────────────

@when("the user submits valid credentials", target_fixture="auth_result")
def submit_valid_credentials(db: dict) -> dict:
    return {"success": True, "session_token": "abc123"}


@then("the session is created")
def session_created(auth_result: dict) -> None:
    assert auth_result["success"] is True


# ── Scenario 10 steps ─────────────────────────────────────────────────────────

@when("the user submits invalid credentials", target_fixture="auth_result")
def submit_invalid_credentials(db: dict) -> dict:
    return {"success": False, "error": "invalid password"}


@then("an authentication error is returned")
def auth_error_returned(auth_result: dict) -> None:
    assert auth_result["success"] is False
