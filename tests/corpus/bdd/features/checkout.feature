Feature: Shopping cart checkout

  # ── 1. All steps pass ─────────────────────────────────────────────────────
  Scenario: Guest completes a purchase
    Given the cart contains 2 items
    When the guest submits valid payment
    Then the order confirmation is shown

  # ── 2. And / But keyword variety, all passing ─────────────────────────────
  Scenario: Logged-in user applies a gift card
    Given the user is authenticated
    And a gift card with 25 credit exists
    When the gift card is redeemed
    Then the balance is deducted from the total
    But the original price is shown as reference

  # ── 3. AssertionError in Then ─────────────────────────────────────────────
  Scenario: Discount code reduces the cart total
    Given the cart total is 100
    When a 10 percent discount is applied
    Then the cart total is 90

  # ── 4. Non-assertion error in When ────────────────────────────────────────
  Scenario: Inventory service is unavailable
    Given the cart contains 1 item
    When the cart is validated against live stock
    Then the item is confirmed available

  # ── 5. Background steps (defined in the test file) ────────────────────────
  Scenario: Authenticated user checks out
    Given the user is logged in
    And the cart has items
    When the user proceeds to checkout
    Then the checkout page is displayed

  # ── 6. Scenario Outline — parametrized via Examples ───────────────────────
  Scenario Outline: Cart total with quantity
    Given the unit price is <price>
    When the user adds <qty> units
    Then the subtotal is <subtotal>

    Examples:
      | price | qty | subtotal |
      | 10    | 3   | 30       |
      | 25    | 2   | 50       |
      | 5     | 4   | 21       |

  # ── 7. Skipped scenario ───────────────────────────────────────────────────
  Scenario: Feature not yet implemented
    Given a feature flag is disabled
    When the user tries to access it
    Then the page is not found

  # ── 8. Expected failure (xfail) ───────────────────────────────────────────
  Scenario: Known bug in promo stacking
    Given two promo codes exist
    When both codes are applied
    Then the higher discount wins
