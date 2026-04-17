"""
tests/corpus/test_bdd.py — pytest-bdd corpus for pytest-glaze.

Covers every distinct rendering path:
  1. All steps pass
  2. And/But keyword variety
  3. AssertionError in Then  (intentional FAIL)
  4. Non-assertion error in When  (intentional ERROR)
  5. Background-style shared setup
  6. Scenario Outline (parametrized)
  7. Skipped scenario
  8. Expected failure (xfail)

Run the "before" state (no BDD-aware hooks yet):
    make test-raw SUITE=tests/corpus/test_bdd.py
    make test-bdd
"""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# ── Scenario 1: All steps pass ────────────────────────────────────────────────

@scenario("features/checkout.feature", "Guest completes a purchase")
def test_guest_purchase() -> None: ...


@given("the cart contains 2 items", target_fixture="cart")
def cart_two_items() -> dict:
    return {"items": 2, "total": 50, "shipping": 10}


@when("the guest submits valid payment")
def submit_valid_payment(cart: dict) -> None:
    cart["payment_status"] = "authorised"


@then("the order confirmation is shown")
def order_confirmed(cart: dict) -> None:
    assert cart["payment_status"] == "authorised"


# ── Scenario 2: And / But keyword variety ─────────────────────────────────────

@scenario("features/checkout.feature", "Logged-in user applies a gift card")
def test_gift_card() -> None: ...


@given("the user is authenticated", target_fixture="user")
def authenticated_user() -> dict:
    return {"authenticated": True, "gift_card_balance": 25}


@given("a gift card with 25 credit exists")
def gift_card_exists(user: dict) -> None:
    assert user["gift_card_balance"] == 25


@when("the gift card is redeemed", target_fixture="cart")
def redeem_gift_card(user: dict) -> dict:
    cart = {"total": 100, "reference_price": 100}
    redeemable = min(user["gift_card_balance"], cart["total"])
    cart["total"] -= redeemable
    user["gift_card_balance"] -= redeemable
    return cart


@then("the balance is deducted from the total")
def balance_deducted(cart: dict) -> None:
    assert cart["total"] == 75


@then("the original price is shown as reference")
def reference_price_shown(cart: dict) -> None:
    assert cart["reference_price"] == 100


# ── Scenario 3: AssertionError in Then (intentional FAIL) ─────────────────────

@scenario("features/checkout.feature", "Discount code reduces the cart total")
def test_discount_code() -> None: ...


@given("the cart total is 100", target_fixture="cart")
def cart_total_100() -> dict:
    return {"total": 100}


@when("a 10 percent discount is applied")
def apply_discount(cart: dict) -> None:
    # Bug: applies only half — intentional corpus failure.
    cart["total"] -= cart["total"] * 0.05


@then("the cart total is 90")
def assert_discounted_total(cart: dict) -> None:
    # cart["total"] == 95.0 → assertion fails.
    assert cart["total"] == 90


# ── Scenario 4: Non-assertion error in When (intentional ERROR) ───────────────

@scenario("features/checkout.feature", "Inventory service is unavailable")
def test_inventory_error() -> None: ...


@given("the cart contains 1 item", target_fixture="cart")
def cart_one_item() -> dict:
    return {"items": 1, "total": 25}


@when("the cart is validated against live stock")
def validate_stock(cart: dict) -> None:
    raise RuntimeError("inventory service timed out after 5000ms")


@then("the item is confirmed available")
def item_available(cart: dict) -> None:  # pragma: no cover
    pass


# ── Scenario 5: Background-style shared setup ─────────────────────────────────

@scenario("features/checkout.feature", "Authenticated user checks out")
def test_authenticated_checkout() -> None: ...


@given("the user is logged in", target_fixture="session")
def logged_in_user() -> dict:
    return {"user_id": 42, "authenticated": True}


@given("the cart has items")
def cart_has_items(session: dict) -> None:
    session["cart"] = ["item_a", "item_b"]


@when("the user proceeds to checkout")
def proceed_to_checkout(session: dict) -> None:
    session["checkout_started"] = True


@then("the checkout page is displayed")
def checkout_displayed(session: dict) -> None:
    assert session["checkout_started"] is True


# ── Scenario 6: Scenario Outline (parametrized) ───────────────────────────────

@scenario("features/checkout.feature", "Cart total with quantity")
def test_cart_total_parametrized() -> None: ...


@given(parsers.parse("the unit price is {price}"), target_fixture="unit_price")
def unit_price(price: str) -> int:
    return int(price)


@when(parsers.parse("the user adds {qty} units"), target_fixture="line_total")
def add_units(unit_price: int, qty: str) -> int:
    return unit_price * int(qty)


@then(parsers.parse("the subtotal is {subtotal}"))
def assert_subtotal(line_total: int, subtotal: str) -> None:
    # Row 3 (price=5, qty=4) → 20, not 21 → intentional FAIL.
    assert line_total == int(subtotal)

# ── Scenario 7: Skipped ───────────────────────────────────────────────────────

@pytest.mark.skip(reason="feature flag not enabled in CI")
@scenario("features/checkout.feature", "Feature not yet implemented")
def test_unimplemented_feature() -> None: ...


@given("a feature flag is disabled", target_fixture="flag")
def feature_flag_disabled() -> bool:
    return False


@when("the user tries to access it")
def access_disabled_feature(flag: bool) -> None:
    pass


@then("the page is not found")
def page_not_found(flag: bool) -> None:
    assert not flag


# ── Scenario 8: Expected failure (xfail) ─────────────────────────────────────

@pytest.mark.xfail(reason="promo stacking bug — see issue #42", strict=False)
@scenario("features/checkout.feature", "Known bug in promo stacking")
def test_promo_stacking() -> None: ...


@given("two promo codes exist", target_fixture="promos")
def two_promos() -> list:
    return ["SAVE10", "SAVE20"]


@when("both codes are applied", target_fixture="discount")
def apply_both(promos: list) -> int:
    # Bug: returns sum instead of max.
    return sum([10, 20])


@then("the higher discount wins")
def higher_discount_wins(discount: int) -> None:
    assert discount == 20  # fails — returns 30
