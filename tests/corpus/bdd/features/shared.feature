Feature: Shared steps and hooks

  # ── Shared steps from conftest ────────────────────────────────────────────
  Scenario: Application health check using shared steps
    Given the application is running
    And the database is connected
    When a health check is performed
    Then the service is healthy

  # ── Shared step reused across scenarios ──────────────────────────────────
  Scenario: Second scenario reusing shared application step
    Given the application is running
    When a health check is performed
    Then the service is healthy

  # ── pytest_bdd_apply_tag: @skip tag ──────────────────────────────────────
  @skip
  Scenario: Scenario skipped via Gherkin tag
    Given the application is running
    When a health check is performed
    Then the service is healthy

  # ── pytest_bdd_apply_tag: @slow tag (passes through to default) ──────────
  @slow
  Scenario: Slow scenario with registered mark
    Given the application is running
    When a health check is performed
    Then the service is healthy

  # ── Session-scoped fixture shared across scenarios ────────────────────────
  Scenario: Session config is consistent across scenarios
    Given the application is running
    Then the app version is 1.0.0

# ── @pytest.mark.usefixtures on scenario ─────────────────────────────────
  Scenario: Scenario with injected fixture via usefixtures
    Given the application is running
    When a health check is performed
    Then the service is healthy
