Feature: pytest-glaze test output rendering

  pytest-glaze replaces the default pytest terminal reporter with a compact,
  color-semantic display. Failures surface inline and every color carries a
  consistent meaning across every line type.

  # ── Passing tests ────────────────────────────────────────────────────────────

  Scenario: Passing test renders as a single compact line
    Given a passing test result
    When pytest-glaze renders the result
    Then the output contains a PASS badge
    And the test name appears on the same line
    And no E lines are printed

  Scenario: Multiple passing tests render one line each
    Given 3 passing test results in the same file
    When pytest-glaze renders all results
    Then exactly 3 result lines are printed
    And each line contains a PASS badge

  # ── Failing tests ─────────────────────────────────────────────────────────────

  Scenario: Failing test renders inline assertion error
    Given a failing test with assertion error "assert 3 == 30"
    When pytest-glaze renders the result
    Then the output contains a FAIL badge
    And the assertion error appears immediately below the test line
    And the received value is highlighted
    And the expected value is highlighted

  Scenario: Failing test never defers its error to a separate block
    Given a failing test with assertion error "assert 3 == 30"
    When pytest-glaze renders the result
    Then the error appears on the line directly after the FAIL line

  # ── Class grouping ────────────────────────────────────────────────────────────

  Scenario: Class-based tests render with a class header
    Given a passing test result with name "TestUserModel::test_create"
    When pytest-glaze renders the result
    Then the class name "TestUserModel" appears as a header
    And the method name "test_create" appears on the result line
    And the result line does not contain "::"

  Scenario: Consecutive tests in the same class share one header
    Given 2 passing test results with name "TestUserModel::test_create" and "TestUserModel::test_update"
    When pytest-glaze renders all results
    Then "TestUserModel" appears exactly once
    And both method names appear on separate result lines

Scenario: New class prints a blank line then a new header
    Given test results for "TestUserModel::test_create" and "TestOrderModel::test_create"
    When pytest-glaze renders all results
    Then a blank line appears between the two class groups
    And "TestOrderModel" appears as a second header

  # ── Per-file summaries ────────────────────────────────────────────────────────

  Scenario: File summary shows correct counts
    Given 2 passing and 1 failing test results in the same file
    When pytest-glaze closes the file group
    Then the summary line shows "2 passed"
    And the summary line shows "1 failed"

  # ── Skip, Xfail, Xpass ────────────────────────────────────────────────────────

  Scenario: Skipped test renders with SKIP badge and reason
    Given a skipped test result with reason "Windows-only feature"
    When pytest-glaze renders the result
    Then the output contains a SKIP badge
    And the reason "Windows-only feature" appears on the E line

  Scenario: Xfailed test renders with XFAIL badge and reason
    Given an xfailed test result with reason "known bug"
    When pytest-glaze renders the result
    Then the output contains an XFAIL badge
    And the reason "known bug" appears on the E line

  Scenario: Xpassed test renders with XPASS badge and reason
    Given an xpassed test result with reason "bug was fixed"
    When pytest-glaze renders the result
    Then the output contains an XPASS badge
    And the reason "bug was fixed" appears on the E line

  # ── Fixture errors ────────────────────────────────────────────────────────────

  Scenario: Setup error renders with ERROR badge
    Given a test result with a setup error "ConnectionError: db unreachable"
    When pytest-glaze renders the result
    Then the output contains an ERROR badge
    And the error message appears on the E line

  Scenario: Teardown error renders after the passing test
    Given a passing test result
    And a teardown error result "RuntimeError: cleanup failed"
    When pytest-glaze renders both results
    Then the PASS line appears first
    And the ERROR line appears immediately after

  # ── Captured output ───────────────────────────────────────────────────────────

  Scenario: Captured output is shown only on failures
    Given a failing test result with captured stdout "debug info"
    When pytest-glaze renders the result
    Then the captured stdout section appears below the failure

  Scenario: Captured output is suppressed on passing tests
    Given a passing test result with captured stdout "debug info"
    When pytest-glaze renders the result
    Then the captured stdout section does not appear

  # ── Noise suppression ─────────────────────────────────────────────────────────

  Scenario: Noise lines are suppressed from output
    Given a failing test with E lines containing "Use -v to get more diff"
    When pytest-glaze renders the result
    Then the noise line does not appear in the output

  # ── Color semantics ───────────────────────────────────────────────────────────

  Scenario: PASS badge and dash render in green
    Given a passing test result
    When pytest-glaze renders the result
    Then the "---" prefix is green
    And the "PASS" badge is green

  Scenario: FAIL badge and dash render in bright red
    Given a failing test result
    When pytest-glaze renders the result
    Then the "---" prefix is bright red
    And the "FAIL" badge is bright red

  Scenario: ERROR badge and dash render in standard red
    Given a test result with a setup error "ConnectionError: db unreachable"
    When pytest-glaze renders the result
    Then the "---" prefix is standard red
    And the "ERROR" badge is standard red

  Scenario: SKIP badge and dash render in yellow
    Given a skipped test result with reason "Windows-only feature"
    When pytest-glaze renders the result
    Then the "---" prefix is yellow
    And the "SKIP" badge is yellow

  Scenario: XFAIL badge and dash render in bright red
    Given an xfailed test result with reason "known bug"
    When pytest-glaze renders the result
    Then the "---" prefix is bright red
    And the "XFAIL" badge is bright red

  Scenario: XPASS badge and dash render in yellow
    Given an xpassed test result with reason "bug was fixed"
    When pytest-glaze renders the result
    Then the "---" prefix is yellow
    And the "XPASS" badge is yellow

  Scenario: Received value in assertion renders in bright red
    Given a failing test with assertion error "assert 3 == 30"
    When pytest-glaze renders the result
    Then the received value "3" is bright red
    And the expected value "30" is green

  Scenario: Expected value in assertion renders in green
    Given a failing test with assertion error "assert 'foo' == 'bar'"
    When pytest-glaze renders the result
    Then the received value "'foo'" is bright red
    And the expected value "'bar'" is green

  Scenario: Diff minus lines render in green
    Given a failing test with a diff line "- expected value"
    When pytest-glaze renders the result
    Then the diff minus line is green

  Scenario: Diff plus lines render in bright red
    Given a failing test with a diff line "+ received value"
    When pytest-glaze renders the result
    Then the diff plus line is bright red

  Scenario: E line context renders in soft peach
    Given a failing test with a context E line "Differing items:"
    When pytest-glaze renders the result
    Then the context line is soft peach

  Scenario: Duration metadata renders in dim
    Given a passing test result with duration 0.8 seconds
    When pytest-glaze renders the result
    Then the duration "800.0ms" is dim

  # ── Test name rendering ───────────────────────────────────────────────────────

  Scenario: Passing test name renders without color
    Given a passing test result with name "test_user_login"
    When pytest-glaze renders the result
    Then the test name "test_user_login" has no color applied

  Scenario: Failing test name renders without color
    Given a failing test result with name "test_user_update"
    When pytest-glaze renders the result
    Then the test name "test_user_update" has no color applied

Scenario: Skipped test name renders without color
    Given a skipped test result with reason "Windows-only feature"
    When pytest-glaze renders the result
    Then the test name "test_example" has no color applied

  Scenario: Error test name renders without color
    Given a test result with a setup error "ConnectionError: db unreachable"
    When pytest-glaze renders the result
    Then the test name "test_example" has no color applied

  Scenario: Class header renders without color
    Given a passing test result with name "TestUserModel::test_create"
    When pytest-glaze renders the result
    Then the class name "TestUserModel" has no color applied
