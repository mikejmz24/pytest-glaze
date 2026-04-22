"""
tests/corpus/acceptance/test_glaze_rendering.py — Acceptance tests for pytest-glaze rendering.
"""
from __future__ import annotations

import re
from typing import List

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from pytest_glaze import FormatterPlugin
from pytest_glaze._types import TestResult

GREEN        = "\033[92m"
BRIGHT_RED   = "\033[91m"
YELLOW       = "\033[93m"
STANDARD_RED = "\033[31m"
SOFT_PEACH   = "\033[0;38;2;252;205;174m"
DIM          = "\033[2m"


def strip_ansi(text: str) -> str:
    return re.sub(r"\033\[[\d;]*m?", "", text)


def is_colorless(text: str) -> bool:
    return not re.search(r"\033\[[\d;]*m", text)


@pytest.fixture
def plugin() -> FormatterPlugin:
    import pytest_glaze._colors as colors
    colors._NO_COLOR = False
    return FormatterPlugin()


def _make_result(
    name: str = "test_example",
    outcome: str = "passed",
    short_msg: str | None = None,
    duration: float = 0.1,
    sections: list | None = None,
    file: str = "tests/test_example.py",
) -> TestResult:
    return TestResult(
        nodeid=f"{file}::{name}", file=file, name=name, outcome=outcome,
        duration=duration, short_msg=short_msg, sections=sections or [],
    )


def _render_one(plugin: FormatterPlugin, result: TestResult) -> List[str]:
    lines: List[str] = []
    plugin._p = lambda t="": lines.append(t)
    plugin._open_file_group(result.file)
    plugin._file_buf.append(result)
    plugin._results.append(result)
    plugin._render_result(result)
    return lines


def _render_many(plugin: FormatterPlugin, results: list) -> List[str]:
    lines: List[str] = []
    plugin._p = lambda t="": lines.append(t)
    for r in results:
        plugin._open_file_group(r.file)
        plugin._file_buf.append(r)
        plugin._results.append(r)
        plugin._render_result(r)
    return lines


# ── Scenarios ─────────────────────────────────────────────────────────────────

@scenario("features/glaze_rendering.feature", "Passing test renders as a single compact line")
def test_passing_compact(): ...

@scenario("features/glaze_rendering.feature", "Multiple passing tests render one line each")
def test_multiple_passing(): ...

@scenario("features/glaze_rendering.feature", "Failing test renders inline assertion error")
def test_failing_inline(): ...

@scenario("features/glaze_rendering.feature", "Failing test never defers its error to a separate block")
def test_failing_not_deferred(): ...

@scenario("features/glaze_rendering.feature", "Class-based tests render with a class header")
def test_class_header(): ...

@scenario("features/glaze_rendering.feature", "Consecutive tests in the same class share one header")
def test_class_header_once(): ...

@scenario("features/glaze_rendering.feature", "New class prints a blank line then a new header")
def test_class_blank_line(): ...

@scenario("features/glaze_rendering.feature", "File summary shows correct counts")
def test_file_summary(): ...

@scenario("features/glaze_rendering.feature", "Skipped test renders with SKIP badge and reason")
def test_skip_badge(): ...

@scenario("features/glaze_rendering.feature", "Xfailed test renders with XFAIL badge and reason")
def test_xfail_badge(): ...

@scenario("features/glaze_rendering.feature", "Xpassed test renders with XPASS badge and reason")
def test_xpass_badge(): ...

@scenario("features/glaze_rendering.feature", "Setup error renders with ERROR badge")
def test_error_badge(): ...

@scenario("features/glaze_rendering.feature", "Teardown error renders after the passing test")
def test_teardown_error(): ...

@scenario("features/glaze_rendering.feature", "Captured output is shown only on failures")
def test_captured_on_failure(): ...

@scenario("features/glaze_rendering.feature", "Captured output is suppressed on passing tests")
def test_captured_suppressed(): ...

@scenario("features/glaze_rendering.feature", "Noise lines are suppressed from output")
def test_noise_suppressed(): ...

@scenario("features/glaze_rendering.feature", "PASS badge and dash render in green")
def test_pass_color(): ...

@scenario("features/glaze_rendering.feature", "FAIL badge and dash render in bright red")
def test_fail_color(): ...

@scenario("features/glaze_rendering.feature", "ERROR badge and dash render in standard red")
def test_error_color(): ...

@scenario("features/glaze_rendering.feature", "SKIP badge and dash render in yellow")
def test_skip_color(): ...

@scenario("features/glaze_rendering.feature", "XFAIL badge and dash render in bright red")
def test_xfail_color(): ...

@scenario("features/glaze_rendering.feature", "XPASS badge and dash render in yellow")
def test_xpass_color(): ...

@scenario("features/glaze_rendering.feature", "Received value in assertion renders in bright red")
def test_received_red(): ...

@scenario("features/glaze_rendering.feature", "Expected value in assertion renders in green")
def test_expected_green(): ...

@scenario("features/glaze_rendering.feature", "Diff minus lines render in green")
def test_diff_minus_green(): ...

@scenario("features/glaze_rendering.feature", "Diff plus lines render in bright red")
def test_diff_plus_red(): ...

@scenario("features/glaze_rendering.feature", "E line context renders in soft peach")
def test_context_soft_peach(): ...

@scenario("features/glaze_rendering.feature", "Duration metadata renders in dim")
def test_duration_dim(): ...

@scenario("features/glaze_rendering.feature", "Passing test name renders without color")
def test_pass_name_no_color(): ...

@scenario("features/glaze_rendering.feature", "Failing test name renders without color")
def test_fail_name_no_color(): ...

@scenario("features/glaze_rendering.feature", "Skipped test name renders without color")
def test_skip_name_no_color(): ...

@scenario("features/glaze_rendering.feature", "Error test name renders without color")
def test_error_name_no_color(): ...

@scenario("features/glaze_rendering.feature", "Class header renders without color")
def test_class_header_no_color(): ...


# ── Given ─────────────────────────────────────────────────────────────────────

@given("a passing test result", target_fixture="result")
def passing_result():
    return _make_result()

@given("a failing test result", target_fixture="result")
def failing_result():
    return _make_result(outcome="failed", short_msg="assert False")

@given(parsers.parse('a passing test result with name "{name}"'), target_fixture="result")
def passing_result_named(name):
    return _make_result(name=name)

@given(parsers.parse('a failing test result with name "{name}"'), target_fixture="result")
def failing_result_named(name):
    return _make_result(name=name, outcome="failed", short_msg="assert False")

@given(parsers.parse('a failing test with assertion error "{error}"'), target_fixture="result")
def failing_with_error(error):
    return _make_result(outcome="failed", short_msg=error)

@given(parsers.parse('a skipped test result with reason "{reason}"'), target_fixture="result")
def skipped_result(reason):
    return _make_result(outcome="skipped", short_msg=f"Skipped: {reason}")

@given(parsers.parse('an xfailed test result with reason "{reason}"'), target_fixture="result")
def xfailed_result(reason):
    return _make_result(outcome="xfailed", short_msg=f"xfailed: {reason}")

@given(parsers.parse('an xpassed test result with reason "{reason}"'), target_fixture="result")
def xpassed_result(reason):
    return _make_result(outcome="xpassed", short_msg=f"xpassed: {reason}")

@given(parsers.parse('a test result with a setup error "{error}"'), target_fixture="result")
def error_result(error):
    return _make_result(outcome="error", short_msg=error)

@given(parsers.parse('a failing test result with captured stdout "{content}"'), target_fixture="result")
def failing_with_captured(content):
    return _make_result(outcome="failed", short_msg="assert False",
                        sections=[("Captured stdout call", content)])

@given(parsers.parse('a passing test result with captured stdout "{content}"'), target_fixture="result")
def passing_with_captured(content):
    return _make_result(sections=[("Captured stdout call", content)])

@given(parsers.parse('a failing test with E lines containing "{noise}"'), target_fixture="result")
def failing_with_noise(noise):
    return _make_result(outcome="failed", short_msg=f"assert False\n{noise}")

@given(parsers.parse("a passing test result with duration {duration:f} seconds"), target_fixture="result")
def passing_with_duration(duration):
    return _make_result(duration=duration)

@given(parsers.parse('a failing test with a diff line "{diff_line}"'), target_fixture="result")
def failing_with_diff(diff_line):
    return _make_result(outcome="failed", short_msg=diff_line)

@given(parsers.parse('a failing test with a context E line "{context}"'), target_fixture="result")
def failing_with_context(context):
    return _make_result(outcome="failed", short_msg=f"assert False\n{context}")

@given(parsers.parse("{n:d} passing test results in the same file"), target_fixture="results")
def n_passing_results(n):
    return [_make_result(name=f"test_{i}") for i in range(n)]

@given(parsers.parse('2 passing test results with name "{name1}" and "{name2}"'),
       target_fixture="results")
def two_named_results(name1, name2):
    return [_make_result(name=name1), _make_result(name=name2)]

@given(
    parsers.parse('test results for "{name1}" and "{name2}"'),
    target_fixture="results",
)
def two_results_for_classes(name1, name2):
    return [_make_result(name=name1), _make_result(name=name2)]

@given(parsers.parse("{n_pass:d} passing and {n_fail:d} failing test results in the same file"),
       target_fixture="results")
def mixed_results(n_pass, n_fail):
    results = [_make_result(name=f"test_pass_{i}") for i in range(n_pass)]
    results += [_make_result(name=f"test_fail_{i}", outcome="failed", short_msg="assert False")
                for i in range(n_fail)]
    return results

@given(parsers.parse('a teardown error result "{error}"'), target_fixture="teardown_error")
def teardown_error_msg(error):
    return error


# ── When ──────────────────────────────────────────────────────────────────────

@when("pytest-glaze renders the result", target_fixture="printed")
def render_result(plugin, result):
    return _render_one(plugin, result)

@when("pytest-glaze renders all results", target_fixture="printed")
def render_all_results(plugin, results):
    return _render_many(plugin, results)

@when("pytest-glaze closes the file group", target_fixture="printed")
def close_file_group(plugin, results):
    lines: List[str] = []
    plugin._p = lambda t="": lines.append(t)
    for r in results:
        plugin._open_file_group(r.file)
        plugin._file_buf.append(r)
        plugin._results.append(r)
        plugin._render_result(r)
    plugin._flush_file_summary()
    return lines

@when("pytest-glaze renders both results", target_fixture="printed")
def render_both(plugin, result, teardown_error):
    lines: List[str] = []
    plugin._p = lambda t="": lines.append(t)
    plugin._open_file_group(result.file)
    plugin._file_buf.append(result)
    plugin._results.append(result)
    plugin._render_result(result)
    teardown = _make_result(name=result.name, outcome="error",
                            short_msg=teardown_error, file=result.file)
    plugin._render_result(teardown)
    return lines


# ── Then ──────────────────────────────────────────────────────────────────────

@then("the output contains a PASS badge")
def output_has_pass(printed):
    assert any("PASS" in strip_ansi(l) for l in printed)

@then("the test name appears on the same line")
def assert_name_on_same_line(printed):
    assert any("---" in strip_ansi(l) for l in printed)

@then("no E lines are printed")
def no_e_lines(printed):
    assert not any(strip_ansi(l).strip().startswith("E  ") for l in printed)

@then(parsers.parse("exactly {n:d} result lines are printed"))
def exactly_n_result_lines(printed, n):
    assert len([l for l in printed if "---" in strip_ansi(l)]) == n

@then("each line contains a PASS badge")
def each_has_pass(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert all("PASS" in strip_ansi(l) for l in result_lines)

@then("the output contains a FAIL badge")
def output_has_fail(printed):
    assert any("FAIL" in strip_ansi(l) for l in printed)

@then("the assertion error appears immediately below the test line")
def error_below_test(printed):
    result_idxs = [i for i, l in enumerate(printed) if "---" in strip_ansi(l)]
    e_idxs = [i for i, l in enumerate(printed) if strip_ansi(l).strip().startswith("E  ")]
    assert result_idxs and e_idxs
    assert e_idxs[0] == result_idxs[-1] + 1

@then("the received value is highlighted")
def received_highlighted(printed):
    assert any(BRIGHT_RED in l for l in printed)

@then("the expected value is highlighted")
def expected_highlighted(printed):
    assert any(GREEN in l for l in printed)

@then("the error appears on the line directly after the FAIL line")
def error_directly_after_fail(printed):
    fail_idx = next(i for i, l in enumerate(printed) if "FAIL" in strip_ansi(l))
    assert strip_ansi(printed[fail_idx + 1]).strip().startswith("E  ")

@then(parsers.parse('the class name "{cls}" appears as a header'))
def class_header_appears(printed, cls):
    assert any(strip_ansi(l).strip() == cls for l in printed)

@then(parsers.parse('the method name "{method}" appears on the result line'))
def method_on_result_line(printed, method):
    assert any(method in strip_ansi(l) for l in printed if "---" in strip_ansi(l))

@then('the result line does not contain "::"')
def result_no_double_colon(printed):
    assert all("::" not in strip_ansi(l) for l in printed if "---" in strip_ansi(l))

@then(parsers.parse('"{name}" appears exactly once'))
def appears_exactly_once(printed, name):
    assert sum(1 for l in printed if strip_ansi(l).strip() == name) == 1

@then("both method names appear on separate result lines")
def both_methods_appear(printed, results):
    result_lines = [strip_ansi(l) for l in printed if "---" in l]
    for r in results:
        assert any(r.name.split("::")[-1] in l for l in result_lines)

@then("a blank line appears between the two class groups")
def blank_between_classes(printed):
    assert "" in printed

@then(parsers.parse('"{name}" appears as a second header'))
def appears_as_second_header(printed, name):
    assert sum(1 for l in printed if strip_ansi(l).strip() == name) == 1

@then(parsers.parse('the summary line shows "{text}"'))
def summary_shows(printed, text):
    assert any(text in strip_ansi(l) for l in printed)

@then("the output contains a SKIP badge")
def output_has_skip(printed):
    assert any("SKIP" in strip_ansi(l) for l in printed)

@then(parsers.parse('the reason "{reason}" appears on the E line'))
def reason_on_e_line(printed, reason):
    e_lines = [strip_ansi(l) for l in printed if strip_ansi(l).strip().startswith("E  ")]
    assert any(reason in l for l in e_lines)

@then("the output contains an XFAIL badge")
def output_has_xfail(printed):
    assert any("XFAIL" in strip_ansi(l) for l in printed)

@then("the output contains an XPASS badge")
def output_has_xpass(printed):
    assert any("XPASS" in strip_ansi(l) for l in printed)

@then("the output contains an ERROR badge")
def output_has_error(printed):
    assert any("ERROR" in strip_ansi(l) for l in printed)

@then("the error message appears on the E line")
def error_on_e_line(printed):
    assert any(strip_ansi(l).strip().startswith("E  ") for l in printed)

@then("the PASS line appears first")
def pass_line_first(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert "PASS" in strip_ansi(result_lines[0])

@then("the ERROR line appears immediately after")
def error_line_after(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert len(result_lines) >= 2
    assert "ERROR" in strip_ansi(result_lines[1])

@then("the captured stdout section appears below the failure")
def captured_below_failure(printed):
    assert any("Captured stdout" in strip_ansi(l) for l in printed)

@then("the captured stdout section does not appear")
def no_captured_section(printed):
    assert not any("Captured stdout" in strip_ansi(l) for l in printed)

@then("the noise line does not appear in the output")
def noise_not_in_output(printed):
    assert not any("Use -v to get more diff" in strip_ansi(l) for l in printed)

@then('the "---" prefix is green')
def dash_is_green(printed):
    assert any(GREEN in l for l in printed if "---" in strip_ansi(l))

@then('the "PASS" badge is green')
def pass_badge_green(printed):
    assert any(GREEN in l for l in printed if "PASS" in strip_ansi(l))

@then('the "---" prefix is bright red')
def dash_is_bright_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "---" in strip_ansi(l))

@then('the "FAIL" badge is bright red')
def fail_badge_bright_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "FAIL" in strip_ansi(l))

@then('the "---" prefix is standard red')
def dash_is_standard_red(printed):
    assert any(STANDARD_RED in l for l in printed if "---" in strip_ansi(l))

@then('the "ERROR" badge is standard red')
def error_badge_standard_red(printed):
    assert any(STANDARD_RED in l for l in printed if "ERROR" in strip_ansi(l))

@then('the "---" prefix is yellow')
def dash_is_yellow(printed):
    assert any(YELLOW in l for l in printed if "---" in strip_ansi(l))

@then('the "SKIP" badge is yellow')
def skip_badge_yellow(printed):
    assert any(YELLOW in l for l in printed if "SKIP" in strip_ansi(l))

@then('the "XFAIL" badge is bright red')
def xfail_badge_bright_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "XFAIL" in strip_ansi(l))

@then('the "XPASS" badge is yellow')
def xpass_badge_yellow(printed):
    assert any(YELLOW in l for l in printed if "XPASS" in strip_ansi(l))

@then(parsers.parse('the received value "{value}" is bright red'))
def received_value_bright_red(printed, value):
    e_lines = [l for l in printed if "E  " in strip_ansi(l)]
    assert any(value in strip_ansi(l) and BRIGHT_RED in l for l in e_lines)

@then(parsers.parse('the expected value "{value}" is green'))
def expected_value_green(printed, value):
    e_lines = [l for l in printed if "E  " in strip_ansi(l)]
    assert any(value in strip_ansi(l) and GREEN in l for l in e_lines)

@then("the diff minus line is green")
def diff_minus_green(printed):
    assert any(GREEN in l for l in printed if "E  " in strip_ansi(l))

@then("the diff plus line is bright red")
def diff_plus_red(printed):
    assert any(BRIGHT_RED in l for l in printed if "E  " in strip_ansi(l))

@then("the context line is soft peach")
def context_soft_peach(printed):
    assert any(SOFT_PEACH in l for l in printed if "E  " in strip_ansi(l))

@then(parsers.parse('the duration "{dur}" is dim'))
def duration_is_dim(printed, dur):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert any(dur in strip_ansi(l) and DIM in l for l in result_lines)

@then(parsers.parse('the test name "{name}" has no color applied'))
def assert_name_colorless(printed, name):
    result_lines = [l for l in printed if "---" in strip_ansi(l) and name in strip_ansi(l)]
    assert result_lines, f"No result line containing '{name}' found"
    for line in result_lines:
        segments = re.split(r"(\033\[[\d;]*m)", line)
        in_color = False
        for seg in segments:
            if re.match(r"\033\[[\d;]*m", seg):
                in_color = seg != "\033[0m"
            elif name in seg and not in_color:
                return
        pytest.fail(f"'{name}' appears colored in: {line!r}")

@then("the test name has no color applied")
def assert_name_no_color_generic(printed):
    result_lines = [l for l in printed if "---" in strip_ansi(l)]
    assert result_lines
    for line in result_lines:
        # The test name is whatever comes after the badge — check it's uncolored
        plain = strip_ansi(line)
        badge_end = plain.index("  ", plain.index("---") + 3) + 2
        name_part = plain[badge_end:].strip()
        # Strip duration (last token)
        name_only = name_part.rsplit("  ", 1)[0].strip()
        segments = re.split(r"(\033\[[\d;]*m)", line)
        in_color = False
        for seg in segments:
            if re.match(r"\033\[[\d;]*m", seg):
                in_color = seg != "\033[0m"
            elif name_only in seg and not in_color:
                return
        pytest.fail(f"Test name appears colored in: {line!r}")

@then(parsers.parse('the class name "{cls}" has no color applied'))
def class_name_colorless(printed, cls):
    headers = [l for l in printed if strip_ansi(l).strip() == cls]
    assert headers, f"Class header '{cls}' not found"
    for line in headers:
        assert is_colorless(line), f"'{cls}' has color: {line!r}"
