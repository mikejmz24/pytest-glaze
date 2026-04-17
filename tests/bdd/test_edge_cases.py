"""
tests/corpus/test_bdd_edge_cases.py — Edge case outcomes corpus.

Covers:
  11. ERROR in Given — ConnectionError before any When/Then fires
  12. Xpass — xfail(strict=False) scenario that actually passes
  13. Step not found — StepDefinitionNotFoundError at runtime
  14. Full And/But chain — And/But after Given, When, Then
      (exercises keyword type inheritance for color rendering)
"""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# ── Scenario 11: ERROR in Given ───────────────────────────────────────────────

@scenario("features/edge_cases.feature", "Database connection fails at setup")
def test_given_failure() -> None: ...


@given("the database connection is established", target_fixture="db_conn")
def db_connection_established() -> dict:
    # Intentional corpus error — fires before When/Then.
    raise ConnectionError("could not reach database host db.internal:5432")


@when("the user queries their profile")
def query_profile(db_conn: dict) -> None:
    pass  # pragma: no cover — never reached


@then("the profile data is returned")
def profile_returned(db_conn: dict) -> None:
    pass  # pragma: no cover — never reached


# ── Scenario 12: Xpass ────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="bug was fixed in v1.2", strict=False)
@scenario("features/edge_cases.feature", "Fixed bug in tax calculation")
def test_fixed_bug() -> None: ...


@given(parsers.parse("an order total of {amount}"), target_fixture="order_total")
def order_total(amount: str) -> float:
    return float(amount)


@when(parsers.parse("tax at {rate} percent is applied"), target_fixture="total_with_tax")
def apply_tax(order_total: float, rate: str) -> float:
    return order_total * (1 + float(rate) / 100)


@then(parsers.parse("the total with tax is {expected}"))
def assert_total_with_tax(total_with_tax: float, expected: str) -> None:
    assert total_with_tax == pytest.approx(float(expected))  # passes → xpass


# ── Scenario 13: Step not found ───────────────────────────────────────────────

@scenario("features/edge_cases.feature", "Step with no implementation")
def test_missing_step() -> None: ...


@given("a step that is defined", target_fixture="state")
def defined_step() -> dict:
    return {"ready": True}


# "When a step that has no implementation" is intentionally not defined.
# pytest-bdd raises StepDefinitionNotFoundError at runtime.

@then("this step is never reached")
def never_reached(state: dict) -> None:
    pass  # pragma: no cover


# ── Scenario 14: Full And/But keyword chain ───────────────────────────────────

@scenario("features/edge_cases.feature", "Full keyword chain")
def test_full_keyword_chain() -> None: ...


@given("the system is initialized", target_fixture="system")
def system_initialized() -> dict:
    return {"ready": True, "cache": False, "status": None, "body": None, "error": None}


@given("the cache is warm")   # And — type inherits "given" → gray
def cache_warm(system: dict) -> None:
    system["cache"] = True


@when("the request is sent")
def request_sent(system: dict) -> None:
    system["status"] = 200


@when("the response is received")   # And — type inherits "when" → yellow
def response_received(system: dict) -> None:
    system["body"] = {"data": "ok"}


@then("the status is success")
def status_success(system: dict) -> None:
    assert system["status"] == 200


@then("the body is not empty")   # And — type inherits "then" → green
def body_not_empty(system: dict) -> None:
    assert system["body"] is not None


@then("the error field is null")   # But — type inherits "then" → green
def error_field_null(system: dict) -> None:
    assert system["error"] is None
