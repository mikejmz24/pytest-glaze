Feature: Edge cases and special outcomes

  # ── 11. ERROR in Given (setup crash) ──────────────────────────────────────
  Scenario: Database connection fails at setup
    Given the database connection is established
    When the user queries their profile
    Then the profile data is returned

  # ── 12. Xpass — xfail that actually passes ────────────────────────────────
  Scenario: Fixed bug in tax calculation
    Given an order total of 100
    When tax at 10 percent is applied
    Then the total with tax is 110

  # ── 13. Step not found (StepDefinitionNotFoundError) ─────────────────────
  Scenario: Step with no implementation
    Given a step that is defined
    When a step that has no implementation
    Then this step is never reached

  # ── 14. Full And/But keyword chain (type inheritance) ────────────────────
  Scenario: Full keyword chain
    Given the system is initialized
    And the cache is warm
    When the request is sent
    And the response is received
    Then the status is success
    And the body is not empty
    But the error field is null
