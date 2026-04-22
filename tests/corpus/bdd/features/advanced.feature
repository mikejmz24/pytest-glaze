Feature: Advanced BDD scenarios
  Exercises docstrings, datatables, unicode, tags, and large diffs.

  # ── 3. Docstring step argument ────────────────────────────────────────────
  Scenario: Email body is validated
    Given the following email body:
      """
      Dear customer,
      Your order has been confirmed.
      Thank you for your purchase.
      """
    When the email is sent
    Then the recipient receives the message

  # ── 4. Datatable step argument ────────────────────────────────────────────
  Scenario: Shopping cart contains multiple items
    Given the cart contains the following items:
      | name       | quantity | price |
      | Apple      | 3        | 0.50  |
      | Bread      | 1        | 1.20  |
      | Milk       | 2        | 0.90  |
    When the cart total is calculated
    Then the total is 4.50

  # ── 6. Unicode in scenario and step names ─────────────────────────────────
  Scenario: Überprüfung der Bestellung
    Given el carrito contiene artículos
    When la commande est passée
    Then the order status is 已确认

  # ── 7. Tagged scenarios ───────────────────────────────────────────────────
  @smoke
  Scenario: Quick health check
    Given the service is running
    When a ping is sent
    Then a pong is received

  @regression @slow
  Scenario: Full order processing pipeline
    Given a complete order exists
    When the order is processed end to end
    Then all systems are updated

  # ── 8. Large assertion diff ───────────────────────────────────────────────
  Scenario: Order summary matches expected
    Given an order with many line items exists
    When the order summary is retrieved
    Then the summary matches the expected output

  # ── 1. Rule block ─────────────────────────────────────────────────────────
  Rule: Guest users have limited access

    Scenario: Guest cannot access order history
      Given the user is not authenticated
      When the user requests order history
      Then access is denied

  # ── 2. Multiple example tables ────────────────────────────────────────────
  Scenario Outline: Discount tiers
    Given an order total of <amount>
    When the <tier> discount is applied
    Then the final price is <final>

    @bronze
    Examples: Bronze tier
      | amount | tier   | final |
      | 100    | bronze | 95    |
      | 200    | bronze | 190   |

    @gold
    Examples: Gold tier
      | amount | tier | final |
      | 100    | gold | 80    |
      | 200    | gold | 160   |

  # ── 5. Long step names ────────────────────────────────────────────────────
  Scenario: Very descriptive scenario with long step names
    Given the user has successfully authenticated using their corporate single sign-on credentials
    When the user submits a request to retrieve all historical transaction records from the past 12 months
    Then the system returns a paginated response containing all matching records with full metadata

# ── Wildcard * keyword ────────────────────────────────────────────────────
  Scenario: Wildcard keyword steps
    Given the system is ready
    * the user sends a request
    * the response is successful

  # ── Generic @step decorator ───────────────────────────────────────────────
  Scenario: Generic step decorator
    Given a product exists in the catalog
    When the product is added to the wishlist
    Then the wishlist contains the product

# ── Multi-column Scenario Outline ─────────────────────────────────────────
  Scenario Outline: Shipping cost by region
    Given the order is shipping to <region>
    When the shipping cost is calculated
    Then the cost is <cost>

    Examples:
      | region | cost |
      | north  | 5    |
      | south  | 8    |
      | east   | 6    |
