"""
tests/bdd/test_advanced.py — Advanced BDD corpus for pytest-glaze.

Covers:
  3.  Docstring step argument
  4.  Datatable step argument
  5.  Long step names
  6.  Unicode in scenario/step names
  7.  Tagged scenarios (@smoke, @regression)
  8.  Large assertion diff (intentional FAIL)
  1.  Rule block
  2.  Multiple example tables with tags
"""
from __future__ import annotations

from pytest_bdd import given, parsers, scenario, step, then, when


# ── Scenario 3: Docstring ─────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Email body is validated")
def test_email_body() -> None: ...


@given("the following email body:", target_fixture="email_body")
def email_body(docstring: str) -> str:
    return docstring


@when("the email is sent")
def send_email(email_body: str) -> None:
    assert "confirmed" in email_body


@then("the recipient receives the message")
def recipient_receives(email_body: str) -> None:
    assert len(email_body) > 0


# ── Scenario 4: Datatable ─────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Shopping cart contains multiple items")
def test_cart_datatable() -> None: ...


@given("the cart contains the following items:", target_fixture="cart_items")
def cart_items(datatable: list) -> list:
    # datatable is a list of lists: [[name, qty, price], ...]
    # first row is headers
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


@when("the cart total is calculated", target_fixture="cart_total")
def calculate_total(cart_items: list) -> float:
    return sum(float(item["price"]) * int(item["quantity"]) for item in cart_items)


@then("the total is 4.50")
def assert_total(cart_total: float) -> None:
    assert round(cart_total, 2) == 4.50


# ── Scenario 6: Unicode ───────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Überprüfung der Bestellung")
def test_unicode_scenario() -> None: ...


@given("el carrito contiene artículos", target_fixture="order")
def cart_with_articles() -> dict:
    return {"items": ["artículo_1", "artículo_2"], "status": None}


@when("la commande est passée")
def place_order(order: dict) -> None:
    order["status"] = "已确认"


@then("the order status is 已确认")
def assert_order_status(order: dict) -> None:
    assert order["status"] == "已确认"


# ── Scenario 7: Tagged scenarios ──────────────────────────────────────────────

@scenario("features/advanced.feature", "Quick health check")
def test_smoke_health_check() -> None: ...


@given("the service is running", target_fixture="service")
def service_running() -> dict:
    return {"status": "running"}


@when("a ping is sent")
def send_ping(service: dict) -> None:
    service["ping"] = True


@then("a pong is received")
def receive_pong(service: dict) -> None:
    assert service["ping"] is True


@scenario("features/advanced.feature", "Full order processing pipeline")
def test_regression_order_pipeline() -> None: ...


@given("a complete order exists", target_fixture="pipeline_order")
def complete_order() -> dict:
    return {"id": "ORD-001", "items": 5, "processed": False}


@when("the order is processed end to end")
def process_order(pipeline_order: dict) -> None:
    pipeline_order["processed"] = True


@then("all systems are updated")
def systems_updated(pipeline_order: dict) -> None:
    assert pipeline_order["processed"] is True


# ── Scenario 8: Large assertion diff (intentional FAIL) ───────────────────────

@scenario("features/advanced.feature", "Order summary matches expected")
def test_large_diff() -> None: ...


@given("an order with many line items exists", target_fixture="order_summary")
def order_with_many_items() -> dict:
    return {
        "id": "ORD-001",
        "items": [
            {"name": "Apple",  "qty": 3, "price": 0.50},
            {"name": "Bread",  "qty": 1, "price": 1.20},
            {"name": "Milk",   "qty": 2, "price": 0.90},
            {"name": "Eggs",   "qty": 12, "price": 0.10},
            {"name": "Butter", "qty": 1, "price": 2.50},
        ],
        "total": 7.90,
        "discount": 0,
        "tax": 0.79,
    }


@when("the order summary is retrieved", target_fixture="summary")
def get_summary(order_summary: dict) -> dict:
    return order_summary


@then("the summary matches the expected output")
def assert_summary(summary: dict) -> None:
    # Intentional FAIL — wrong total and missing fields
    expected = {
        "id": "ORD-001",
        "items": [
            {"name": "Apple",  "qty": 3, "price": 0.50},
            {"name": "Bread",  "qty": 1, "price": 1.20},
            {"name": "Milk",   "qty": 2, "price": 0.90},
            {"name": "Eggs",   "qty": 12, "price": 0.10},
            {"name": "Butter", "qty": 1, "price": 2.50},
        ],
        "total": 8.50,   # wrong — intentional
        "discount": 0.5, # wrong — intentional
        "tax": 0.79,
    }
    assert summary == expected


# ── Rule block ────────────────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Guest cannot access order history")
def test_guest_no_order_history() -> None: ...


@given("the user is not authenticated", target_fixture="guest")
def unauthenticated_user() -> dict:
    return {"authenticated": False}


@when("the user requests order history")
def request_order_history(guest: dict) -> None:
    guest["attempted"] = True


@then("access is denied")
def access_denied(guest: dict) -> None:
    assert guest["authenticated"] is False


# ── Multiple example tables ───────────────────────────────────────────────────

@scenario("features/advanced.feature", "Discount tiers")
def test_discount_tiers() -> None: ...


@given(parsers.parse("an order total of {amount}"), target_fixture="order_amount")
def order_amount(amount: str) -> int:
    return int(amount)


@when(parsers.parse("the {tier} discount is applied"), target_fixture="discounted")
def apply_tier_discount(order_amount: int, tier: str) -> int:
    rates = {"bronze": 0.05, "gold": 0.20}
    return int(order_amount * (1 - rates.get(tier, 0)))


@then(parsers.parse("the final price is {final}"))
def assert_final_price(discounted: int, final: str) -> None:
    assert discounted == int(final)


# ── Long step names ───────────────────────────────────────────────────────────

@scenario("features/advanced.feature",
          "Very descriptive scenario with long step names")
def test_long_step_names() -> None: ...


@given(
    "the user has successfully authenticated using their corporate "
    "single sign-on credentials",
    target_fixture="auth_session"
)
def sso_authenticated() -> dict:
    return {"authenticated": True, "method": "sso"}


@when(
    "the user submits a request to retrieve all historical transaction "
    "records from the past 12 months",
    target_fixture="transaction_records"
)
def fetch_transactions(auth_session: dict) -> list:
    return [{"id": f"TXN-{i}", "amount": i * 10} for i in range(1, 6)]


@then(
    "the system returns a paginated response containing all matching "
    "records with full metadata"
)
def assert_paginated_response(transaction_records: list) -> None:
    assert len(transaction_records) == 5
    assert all("id" in r and "amount" in r for r in transaction_records)

# ── Wildcard * keyword ────────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Wildcard keyword steps")
def test_wildcard_keyword() -> None: ...


@given("the system is ready", target_fixture="system_state")
def wildcard_system_ready() -> dict:
    return {"ready": True, "response": None}


@step("the user sends a request")
def wildcard_send_request(system_state: dict) -> None:
    system_state["response"] = 200


@step("the response is successful")
def wildcard_response_success(system_state: dict) -> None:
    assert system_state["response"] == 200


# ── Generic @step decorator ───────────────────────────────────────────────────

@scenario("features/advanced.feature", "Generic step decorator")
def test_generic_step_decorator() -> None: ...


@step("a product exists in the catalog", target_fixture="product")
def product_in_catalog() -> dict:
    return {"id": "PROD-001", "name": "Widget", "in_wishlist": False}


@step("the product is added to the wishlist")
def add_to_wishlist(product: dict) -> None:
    product["in_wishlist"] = True


@step("the wishlist contains the product")
def wishlist_contains(product: dict) -> None:
    assert product["in_wishlist"] is True


# ── Vertical example table ────────────────────────────────────────────────────

@scenario("features/advanced.feature", "Shipping cost by region")
def test_shipping_vertical() -> None: ...


@given(parsers.parse("the order is shipping to {region}"),
       target_fixture="shipping_region")
def shipping_region(region: str) -> str:
    return region


@when("the shipping cost is calculated", target_fixture="shipping_cost")
def calculate_shipping(shipping_region: str) -> int:
    rates = {"north": 5, "south": 8, "east": 6}
    return rates.get(shipping_region, 0)


@then(parsers.parse("the cost is {cost}"))
def assert_shipping_cost(shipping_cost: int, cost: str) -> None:
    assert shipping_cost == int(cost)

