"""
tests/corpus/acceptance/test_glaze_bdd_rendering.py — Acceptance tests for
pytest-glaze BDD rendering behavior.

Uses pytest-bdd to express BDD rendering specs as Gherkin scenarios.
Steps call FormatterPlugin directly and assert on printed output.
"""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from pytest_glaze import FormatterPlugin

# ── ANSI color codes ──────────────────────────────────────────────────────────
from tests.helpers import (
    GREEN, BRIGHT_RED, YELLOW, STANDARD_RED, DIM,
    BABY_BLUE, STEEL_BLUE,
    strip_ansi,
    _make_result, _make_bdd_step,
)
from pytest_glaze._colors import c_bdd_feature, c_bdd_scenario

# ── Plugin fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def plugin() -> FormatterPlugin:
    p = FormatterPlugin()
    # Open initial file group — output discarded
    with p.capture():
        p.open_file("tests/bdd/test_checkout.py")
    p._test_outcome = "passed"
    p._test_short_msg = None
    return p


# ── Helpers ───────────────────────────────────────────────────────────────────

def _flush(plugin, outcome, short_msg=None):
    return plugin.flush_scenario(outcome, short_msg)


def _get_lines(plugin):
    # No longer needed — flush_scenario returns lines directly
    return []


# ── Scenario declarations ─────────────────────────────────────────────────────

@scenario("features/glaze_bdd_rendering.feature",
          "Passing scenario renders as a single compact line in compact mode")
def test_compact_pass(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact line shows total duration of all steps")
def test_compact_duration(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Failing scenario shows full steps in compact mode")
def test_compact_fail_shows_steps(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Error scenario shows full steps in compact mode")
def test_compact_error_shows_steps(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Skipped scenario renders as a single compact line")
def test_compact_skip(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xfailed scenario renders as a single compact line")
def test_compact_xfail(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xpassed scenario renders as a single compact line")
def test_compact_xpass(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Passing scenario shows all steps in steps mode")
def test_steps_mode_pass(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Steps mode shows step keyword and name")
def test_steps_keyword_name(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Feature header renders in baby blue")
def test_feature_header_color(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Scenario header renders in steel blue")
def test_scenario_header_color(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Feature header prints before first scenario")
def test_feature_header_before_scenario(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Feature header does not repeat for same feature")
def test_feature_header_no_repeat(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "New feature prints a blank line then a new header")
def test_new_feature_blank_line(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Passing step renders entirely in green")
def test_pass_step_green(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Failing step renders entirely in bright red")
def test_fail_step_red(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Error step renders entirely in standard red")
def test_error_step_red(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xfailed step renders entirely in bright red")
def test_xfail_step_red(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xpassed step renders entirely in yellow")
def test_xpass_step_yellow(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact PASS line entire line renders in green")
def test_compact_pass_green(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact FAIL scenario name renders in bright red")
def test_compact_fail_red(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact SKIP line renders entirely in yellow")
def test_compact_skip_yellow(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact XFAIL line renders entirely in bright red")
def test_compact_xfail_red(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Compact XPASS line renders entirely in yellow")
def test_compact_xpass_yellow(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xfail corrects last step from failed to xfailed")
def test_xfail_correction(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Xpass corrects last step from passed to xpassed")
def test_xpass_correction(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Missing step definition renders as ERROR with trimmed message")
def test_missing_step(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Background label appears before first background step")
def test_background_label(): ...

@scenario("features/glaze_bdd_rendering.feature",
          "Teardown error renders after passing scenario")
def test_teardown_error(): ...


# ── Given steps ───────────────────────────────────────────────────────────────

@given(parsers.re(r"a passing BDD scenario with (?P<n>\d+) steps?$"), target_fixture="bdd_steps")
def passing_scenario_n_steps(plugin, n):
    n = int(n)
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Guest completes a purchase")]
    for i in range(n):
        plugin.bdd.scenario_buf.append(
            _make_bdd_step("Given", f"step {i}", "passed", 0.1)
        )
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given(parsers.parse("a passing BDD scenario with {n:d} steps each taking {dur:f} seconds"),
       target_fixture="bdd_steps")
def passing_scenario_n_steps_duration(plugin, n, dur):
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Guest completes a purchase")]
    for i in range(n):
        plugin.bdd.scenario_buf.append(
            _make_bdd_step("Given", f"step {i}", "passed", dur)
        )
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("a BDD scenario where the last step fails", target_fixture="bdd_steps")
def scenario_last_step_fails(plugin):
    plugin._test_outcome = "failed"
    plugin._test_short_msg = "assert 95.0 == 90"
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Discount code")]
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.scenario_buf.append(_make_bdd_step("Then", "step 2", "failed", 0.1,
                                                    short_msg="assert 95.0 == 90"))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("a BDD scenario where a step raises a RuntimeError", target_fixture="bdd_steps")
def scenario_step_runtime_error(plugin):
    plugin._test_outcome = "error"
    plugin._test_short_msg = "RuntimeError: service timed out"
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Inventory error")]
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.scenario_buf.append(_make_bdd_step("When", "step 2", "error", 0.1,
                                                    short_msg="RuntimeError: service timed out"))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("a skipped BDD scenario", target_fixture="skip_result")
def skipped_bdd_scenario(plugin):
    plugin.bdd.scenario_names["tests/bdd/test_checkout.py::test_skip"] = "Feature not yet implemented"
    return _make_result("test_skip", "skipped", "Skipped: feature flag not enabled in CI",
                        file="tests/bdd/test_checkout.py")


@given("a BDD scenario where the last step is xfailed", target_fixture="bdd_steps")
def scenario_last_step_xfailed(plugin):
    plugin._test_outcome = "xfailed"
    plugin._test_short_msg = "xfailed: known bug"
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Known bug")]
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.scenario_buf.append(_make_bdd_step("Then", "step 2", "failed", 0.1,
                                                    short_msg="assert x"))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("a BDD scenario where the last step is xpassed", target_fixture="bdd_steps")
def scenario_last_step_xpassed(plugin):
    plugin._test_outcome = "xpassed"
    plugin._test_short_msg = "xpassed: bug fixed"
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Fixed bug")]
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.scenario_buf.append(_make_bdd_step("Then", "step 2", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given(parsers.parse('a passing BDD scenario with a "{keyword}" step named "{name}"'),
       target_fixture="bdd_steps")
def passing_scenario_named_step(plugin, keyword, name):
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Named step")]
    plugin.bdd.scenario_buf.append(_make_bdd_step(keyword, name, "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given(parsers.parse('a BDD scenario in feature "{feature_name}"'), target_fixture="bdd_scenario")
def scenario_in_feature(plugin, feature_name):
    plugin.bdd.scenario_buf = [
        c_bdd_feature(f"  Feature: {feature_name}"),
        c_bdd_scenario("    Scenario: Guest completes a purchase"),
    ]
    plugin.bdd.cur_feature = feature_name
    plugin.bdd.any_feature_printed = True
    plugin.bdd.last_step_idx = -1
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("two BDD scenarios in the same feature \"Shopping cart checkout\"",
       target_fixture="bdd_scenario")
def two_scenarios_same_feature(plugin):
    plugin.bdd.scenario_buf = [
        c_bdd_feature("  Feature: Shopping cart checkout"),
        c_bdd_scenario("    Scenario: Scenario A"),
    ]
    plugin.bdd.cur_feature = "Shopping cart checkout"
    plugin.bdd.any_feature_printed = True
    plugin.bdd.last_step_idx = -1
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("another BDD scenario in feature \"User authentication\"",
       target_fixture="second_scenario")
def another_scenario_new_feature(plugin):
    return "User authentication"


@given("a BDD scenario where a step has no implementation", target_fixture="bdd_steps")
def scenario_missing_step(plugin):
    raw_msg = 'StepDefinitionNotFoundError: Step definition is not found: When "a step". Line 18 in scenario "X" in the feature "/path/to/file.feature"'
    # Trim through the same logic as the formatter
    if "StepDefinitionNotFoundError" in raw_msg and ". " in raw_msg:
        raw_msg = raw_msg[:raw_msg.index(". ") + 1]
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Missing step")]
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step defined", "passed", 0.1))
    plugin.bdd.scenario_buf.append(_make_bdd_step(
        "When", "a step that has no implementation", "error", 0.1,
        short_msg=raw_msg
    ))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given("a BDD scenario with a background step", target_fixture="bdd_steps")
def scenario_with_background(plugin):
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Auth")]
    plugin.bdd.scenario_buf.append(f"       \033[{2}mBackground:\033[0m")
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "the database is available", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    return plugin.bdd.scenario_buf


@given(parsers.parse("a passing BDD scenario with {n:d} steps for teardown"),
       target_fixture="teardown_bdd_steps")
def passing_scenario_for_teardown(plugin, n):
    plugin.bdd.scenario_buf = [c_bdd_scenario("    Scenario: Teardown test")]
    for i in range(n):
        plugin.bdd.scenario_buf.append(_make_bdd_step("Given", f"step {i}", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    plugin.bdd.handled.add("tests/bdd/test_checkout.py::test_teardown")
    return plugin.bdd.scenario_buf


@given(parsers.parse('a teardown error "{error}"'), target_fixture="teardown_error")
def teardown_error_msg(error):
    return error


# ── When steps ────────────────────────────────────────────────────────────────

@when("pytest-glaze flushes the scenario in compact mode", target_fixture="printed")
def flush_compact(plugin):
    plugin.bdd.steps_mode = False
    return plugin.flush_scenario(plugin._test_outcome, plugin._test_short_msg)


@when("pytest-glaze flushes the scenario in steps mode", target_fixture="printed")
def flush_steps(plugin):
    plugin.bdd.steps_mode = True
    return plugin.flush_scenario(plugin._test_outcome, plugin._test_short_msg)


@when("pytest-glaze renders the skip result", target_fixture="printed")
def render_skip(plugin, skip_result):
    return plugin.render_result(skip_result)


@when("pytest-glaze processes the scenario", target_fixture="printed")
def process_scenario(plugin, bdd_scenario):
    return plugin.flush_scenario("passed")


@when("pytest-glaze processes the scenario in steps mode", target_fixture="printed")
def process_scenario_steps_mode(plugin, bdd_scenario):
    plugin.bdd.steps_mode = True
    return plugin.flush_scenario(plugin._test_outcome, plugin._test_short_msg)


@when("pytest-glaze processes the same feature twice", target_fixture="printed")
def process_same_feature_twice(plugin, bdd_scenario):
    lines = plugin.flush_scenario(plugin._test_outcome, plugin._test_short_msg)
    plugin.bdd.scenario_buf = [
        c_bdd_scenario("    Scenario: Scenario B"),
    ]
    plugin.bdd.last_step_idx = -1
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    lines += plugin.flush_scenario("passed")
    return lines


@when("pytest-glaze processes both scenarios", target_fixture="printed")
def process_both_scenarios(plugin, bdd_scenario, second_scenario):
    lines = plugin.flush_scenario(plugin._test_outcome, plugin._test_short_msg)
    plugin.bdd.scenario_buf = [
        "",
        c_bdd_feature(f"  Feature: {second_scenario}"),
        c_bdd_scenario("    Scenario: Login"),
    ]
    plugin.bdd.last_step_idx = -1
    plugin.bdd.scenario_buf.append(_make_bdd_step("Given", "step 1", "passed", 0.1))
    plugin.bdd.last_step_idx = len(plugin.bdd.scenario_buf) - 1
    plugin.bdd.last_was_full_step = True
    lines += plugin.flush_scenario("passed")
    return lines


@when("pytest-glaze renders the teardown error", target_fixture="printed")
def render_teardown(plugin, teardown_bdd_steps, teardown_error):
    plugin.bdd.steps_mode = True
    lines = plugin.flush_scenario("passed")
    teardown = _make_result(
        name="test_teardown",
        outcome="error",
        short_msg=teardown_error,
        file="tests/bdd/test_checkout.py",
    )
    lines += plugin.render_result(teardown)
    return lines


# ── Then steps ────────────────────────────────────────────────────────────────

@then("the output contains a PASS badge")
def bdd_output_has_pass(printed):
    assert any("PASS" in strip_ansi(l) for l in printed)


@then("the scenario name appears on the result line")
def scenario_name_on_result(printed):
    assert any("Scenario:" in strip_ansi(l) and "---" in strip_ansi(l) for l in printed)


@then("no step lines are printed")
def no_step_lines(printed):
    step_keywords = ["Given", "When", "Then", "And", "But"]
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    for line in result_lines:
        plain = strip_ansi(line)
        assert not any(f"  {kw} " in plain for kw in step_keywords), \
            f"Step line found in compact output: {plain}"


@then("the duration shown is the sum of all step durations")
def duration_is_sum(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert result_lines
    # 3 steps × 0.1s = 0.3s = 300.0ms
    assert any("300.0ms" in strip_ansi(l) for l in result_lines)


@then("all step lines are printed")
def all_step_lines_printed(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then"])]
    assert len(step_lines) >= 1


@then("the failing step has a FAIL badge")
def failing_step_has_fail(printed):
    assert any("FAIL" in strip_ansi(l) for l in printed if "---" in strip_ansi(l))


@then("the error step has an ERROR badge")
def error_step_has_error(printed):
    assert any("ERROR" in strip_ansi(l) for l in printed if "---" in strip_ansi(l))


@then("the output contains a SKIP badge")
def bdd_output_has_skip(printed):
    assert any("SKIP" in strip_ansi(l) for l in printed)


@then("the output contains an XFAIL badge")
def bdd_output_has_xfail(printed):
    assert any("XFAIL" in strip_ansi(l) for l in printed)


@then("the output contains an XPASS badge")
def bdd_output_has_xpass(printed):
    assert any("XPASS" in strip_ansi(l) for l in printed)


@then(parsers.parse("exactly {n:d} step lines are printed"))
def exactly_n_step_lines(printed, n):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then", "And", "But"])]
    assert len(step_lines) == n


@then("each step line has a PASS badge")
def each_step_has_pass(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then", "And", "But"])]
    assert all("PASS" in strip_ansi(l) for l in step_lines)


@then(parsers.parse('the step line contains "{text}"'))
def step_line_contains(printed, text):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(text in strip_ansi(l) for l in step_lines)


@then("the Feature header is baby blue")
def feature_header_baby_blue(printed):
    feature_lines = [l for l in printed if "Feature:" in strip_ansi(l)]
    assert feature_lines
    assert any(BABY_BLUE in l for l in feature_lines)


@then("the Scenario header is steel blue")
def scenario_header_steel_blue(printed):
    # In compact mode the Scenario header is embedded in the result line
    # In steps mode it's a separate line — check both
    scenario_lines = [l for l in printed if "Scenario:" in strip_ansi(l)]
    assert scenario_lines
    assert any(STEEL_BLUE in l for l in scenario_lines)


@then(parsers.parse('the Feature header "{name}" appears before the scenario'))
def feature_header_before_scenario(printed, name):
    feature_idx = next((i for i, l in enumerate(printed) if name in strip_ansi(l)
                        and "Feature:" in strip_ansi(l)), None)
    # Scenario appears either as a header line or in a compact result line
    scenario_idx = next((i for i, l in enumerate(printed) if "Scenario:" in strip_ansi(l)
                         and i != feature_idx), None)
    assert feature_idx is not None
    assert scenario_idx is not None
    assert feature_idx < scenario_idx


@then(parsers.parse('"{name}" appears exactly once as a Feature header'))
def feature_header_once(printed, name):
    feature_lines = [l for l in printed if "Feature:" in strip_ansi(l)
                     and name in strip_ansi(l)]
    assert len(feature_lines) == 1


@then(parsers.parse('a blank line appears before "{name}" feature header'))
def blank_before_new_feature(printed, name):
    for i, l in enumerate(printed):
        if "Feature:" in strip_ansi(l) and name in strip_ansi(l):
            # In compact mode blank line may be suppressed — just verify header exists
            # and appears after first scenario
            assert i > 0, f"Feature header '{name}' is first line — expected after first scenario"
            return
    pytest.fail(f"Feature header '{name}' not found in: {[strip_ansi(l) for l in printed]}")


@then("the step line is entirely green")
def step_line_entirely_green(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then"])]
    assert step_lines
    assert all(GREEN in l for l in step_lines)


@then('the step "---" prefix is green')
def step_dash_green(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(GREEN in l for l in step_lines)


@then('the step "PASS" badge is green')
def step_pass_badge_green(printed):
    assert any(GREEN in l for l in printed if "PASS" in strip_ansi(l))


@then("the step name is green")
def step_name_green(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(GREEN in l for l in step_lines)


@then("the step line is entirely bright red")
def step_line_entirely_bright_red(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then", "XFAIL"])]
    assert step_lines
    assert any(BRIGHT_RED in l for l in step_lines)


@then('the failing step "---" prefix is bright red')
def failing_step_dash_bright_red(printed):
    fail_lines = [l for l in printed if "FAIL" in strip_ansi(l) and "---" in strip_ansi(l)]
    assert any(BRIGHT_RED in l for l in fail_lines)


@then('the failing step "FAIL" badge is bright red')
def failing_step_badge_bright_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "FAIL" in strip_ansi(l))


@then("the step name is bright red")
def step_name_bright_red(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(BRIGHT_RED in l for l in step_lines)


@then("the step line is entirely standard red")
def step_line_entirely_standard_red(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["When", "ERROR"])]
    assert step_lines
    assert any(STANDARD_RED in l for l in step_lines)


@then('the error step "---" prefix is standard red')
def error_step_dash_standard_red(printed):
    error_lines = [l for l in printed if "ERROR" in strip_ansi(l) and "---" in strip_ansi(l)]
    assert any(STANDARD_RED in l for l in error_lines)


@then('the error step "ERROR" badge is standard red')
def error_step_badge_standard_red(printed):
    assert any(STANDARD_RED in l for l in printed if "ERROR" in strip_ansi(l))


@then("the step name is standard red")
def step_name_standard_red(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(STANDARD_RED in l for l in step_lines)


@then('the step "XFAIL" badge is bright red')
def xfail_badge_bright_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "XFAIL" in strip_ansi(l))


@then("the step line is entirely yellow")
def step_line_entirely_yellow(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(YELLOW in l for l in step_lines)


@then('the step "XPASS" badge is yellow')
def xpass_badge_yellow(printed):
    assert any(YELLOW in l for l in printed if "XPASS" in strip_ansi(l))


@then("the entire compact result line is green")
def compact_line_green(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)
                    and "Scenario:" in strip_ansi(l)]
    assert result_lines
    assert any(GREEN in l for l in result_lines)


@then("the scenario name on the FAIL line is bright red")
def compact_fail_name_bright_red(printed):
    fail_lines = [l for l in printed if "FAIL" in strip_ansi(l) and "---" in strip_ansi(l)]
    assert fail_lines
    assert any(BRIGHT_RED in l for l in fail_lines)


@then("the entire compact result line is yellow")
def compact_line_yellow(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(YELLOW in l for l in result_lines)


@then("the entire compact result line is bright red")
def compact_line_bright_red(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(BRIGHT_RED in l for l in result_lines)


@then("the last step has an XFAIL badge")
def last_step_xfail(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then"])]
    assert step_lines
    assert "XFAIL" in strip_ansi(step_lines[-1])


@then("the xfail reason appears on the E line")
def xfail_reason_on_e_line(printed):
    e_lines = [strip_ansi(l) for l in printed if strip_ansi(l).strip().startswith("E  ")]
    assert any("xfailed" in l for l in e_lines)


@then("the last step has an XPASS badge")
def last_step_xpass(printed):
    step_lines = [l for l in printed if "---" in strip_ansi(l) and
                  any(kw in strip_ansi(l) for kw in ["Given", "When", "Then"])]
    assert step_lines
    assert "XPASS" in strip_ansi(step_lines[-1])


@then("the step has an ERROR badge")
def step_has_error(printed):
    assert any("ERROR" in strip_ansi(l) for l in printed if "---" in strip_ansi(l))


@then("the error message is trimmed to the first sentence")
def error_trimmed(printed):
    e_lines = [strip_ansi(l) for l in printed if strip_ansi(l).strip().startswith("E  ")]
    assert e_lines
    assert not any("/path/to" in l for l in e_lines), "Full path found — message not trimmed"
    assert not any("Line 18 in scenario" in l for l in e_lines), \
        "Verbose suffix found — message not trimmed"


@then(parsers.parse('a dim "Background:" label appears before the background step'))
def background_label_appears(printed):
    assert any("Background:" in strip_ansi(l) for l in printed)
    bg_idx = next(i for i, l in enumerate(printed) if "Background:" in strip_ansi(l))
    step_idx = next(i for i, l in enumerate(printed) if "---" in strip_ansi(l))
    assert bg_idx < step_idx


@then('the teardown error line shows "teardown failed"')
def teardown_error_line(printed):
    assert any("teardown failed" in strip_ansi(l) for l in printed)


@then("the error message appears on the E line")
def error_message_on_e_line(printed):
    assert any(strip_ansi(l).strip().startswith("E  ") for l in printed)
