Feature: User authentication flows
  Background steps run before every scenario in this feature.

  Background:
    Given the database is available
    And the user table is seeded

  # ── 9. Background + passing scenario ──────────────────────────────────────
  Scenario: User logs in successfully
    When the user submits valid credentials
    Then the session is created

  # ── 10. Background + failing scenario ─────────────────────────────────────
  Scenario: User login fails with wrong password
    When the user submits invalid credentials
    Then an authentication error is returned
