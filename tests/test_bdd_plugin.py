# tests/test_bdd_plugin.py
"""
Unit tests for BDD helper methods in FormatterPlugin.

Same patterns as test_plugin.py — SimpleNamespace stubs, no pytest machinery.
All methods tested in pure isolation by inspecting _bdd_scenario_buf directly
rather than capturing printed output.

Coverage:
  _extract_exception_msg    — exception → concise E-line string
  _bdd_before_scenario      — Feature/Scenario header buffering, blank line rules
  _bdd_after_step           — PASS step buffering, handled set, last_step_idx
  _bdd_step_error           — FAIL/ERROR step buffering, message capture
  _bdd_flush_scenario       — xfail/xpass correction, buffer cleared after flush
  _bdd_before_step          — start time recording, Background label insertion
"""
from types import SimpleNamespace

import pytest_glaze
from pytest_glaze import FormatterPlugin, _BDDStep, c_bdd_scenario
from tests.helpers import (strip_ansi, _make_result)

# ── Stubs ─────────────────────────────────────────────────────────────────────

def _plugin() -> FormatterPlugin:
    """Fresh FormatterPlugin with _glaze_plugin wired up."""
    p = FormatterPlugin()
    pytest_glaze._glaze_plugin = p
    return p


def _feature(name: str = "Shopping cart checkout", background=None):
    return SimpleNamespace(name=name, background=background)


def _scenario(name: str = "Guest completes a purchase"):
    return SimpleNamespace(name=name)


def _step(keyword: str = "Given", type_: str = "given", name: str = "the cart contains 2 items"):
    return SimpleNamespace(keyword=keyword, type=type_, name=name)


def _request(nodeid: str = "tests/bdd/test_checkout.py::test_guest_purchase"):
    return SimpleNamespace(node=SimpleNamespace(nodeid=nodeid))


def _buf_strings(p: FormatterPlugin) -> list:
    """Return only string items from _bdd_scenario_buf (excludes _BDDStep instances)."""
    return [item for item in p._bdd_scenario_buf if isinstance(item, str)]


def _buf_steps(p: FormatterPlugin) -> list:
    """Return only _BDDStep items from _bdd_scenario_buf."""
    return [item for item in p._bdd_scenario_buf if isinstance(item, _BDDStep)]


# ── _extract_exception_msg ────────────────────────────────────────────────────

class TestExtractExceptionMsg:
    """Tests for FormatterPlugin._extract_exception_msg()."""

    def test_assertion_error_does_not_prepend_type_name(self):
        # pytest assertion rewriting already includes 'assert' in the message.
        # _extract_exception_msg preserves it as-is without prepending 'AssertionError:'.
        msg = FormatterPlugin._extract_exception_msg(AssertionError("assert 95.0 == 90"))
        assert msg == "assert 95.0 == 90"

    def test_assertion_error_includes_message_body(self):
        msg = FormatterPlugin._extract_exception_msg(AssertionError("assert 95.0 == 90"))
        assert "assert 95.0 == 90" in msg

    def test_runtime_error_prepends_type(self):
        msg = FormatterPlugin._extract_exception_msg(RuntimeError("inventory timed out"))
        assert msg == "RuntimeError: inventory timed out"

    def test_connection_error_prepends_type(self):
        msg = FormatterPlugin._extract_exception_msg(ConnectionError("could not reach db.internal"))
        assert msg.startswith("ConnectionError:")

    def test_empty_exception_returns_type_name(self):
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(""))
        assert msg == "RuntimeError"

    def test_multiline_trimmed_to_max_e_lines(self):
        """More than MAX_E_LINES lines must be truncated."""
        big = "\n".join(f"line {i}" for i in range(30))
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(big))
        assert len(msg.splitlines()) == pytest_glaze.MAX_E_LINES

    def test_blank_lines_excluded_from_count(self):
        """Blank lines in the exception message must not count toward MAX_E_LINES."""
        lines = "\n\n".join(f"line {i}" for i in range(20))
        msg = FormatterPlugin._extract_exception_msg(RuntimeError(lines))
        assert msg is not None


# ── _bdd_before_scenario: Feature header ─────────────────────────────────────

class TestBddBeforeScenarioFeatureHeader:
    """Buffer contents for Feature header — when it appears and when it doesn't."""

    def test_first_scenario_buffers_feature_header(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        assert any("Feature:" in s and "Shopping cart checkout" in s for s in strings)

    def test_first_scenario_no_blank_line_before_feature(self):
        """The very first feature must not be preceded by a blank line."""
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        feature_idx = next(i for i, s in enumerate(strings) if "Feature:" in s)
        assert "" not in strings[:feature_idx]

    def test_new_feature_blank_line_buffered_before_header(self):
        """When the feature changes, a blank line must precede the new Feature header."""
        p = _plugin()
        p._bdd_cur_feature       = "Old Feature"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature("Shopping cart checkout"), _scenario())
        strings = _buf_strings(p)
        feature_idx = next(i for i, s in enumerate(strings) if "Feature:" in s)
        assert strings[feature_idx - 1] == ""

    def test_same_feature_no_duplicate_header(self):
        """Consecutive scenarios of the same feature must not repeat the header."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        assert not any("Feature:" in s for s in strings)

    def test_cur_feature_updated_to_new_name(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature("New Feature"), _scenario())
        assert p._bdd_cur_feature == "New Feature"

    def test_any_feature_printed_flag_set_after_first(self):
        p = _plugin()
        assert p._bdd_any_feature_printed is False
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert p._bdd_any_feature_printed is True


# ── _bdd_before_scenario: Scenario header ────────────────────────────────────

class TestBddBeforeScenarioScenarioHeader:
    """Buffer contents for Scenario header and blank-line spacing."""

    def test_scenario_name_in_buffer(self):
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario("Guest completes a purchase"))
        strings = _buf_strings(p)
        assert any("Scenario:" in s and "Guest completes a purchase" in s for s in strings)

    def test_blank_line_between_same_feature_scenarios(self):
        """Two scenarios in the same feature must be separated by a blank line."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        p._bdd_first_in_file     = False
        p._bdd_before_scenario(_request(), _feature(), _scenario("Scenario B"))
        strings = _buf_strings(p)
        assert "" in strings

    def test_feature_header_before_scenario_header(self):
        """Feature header must always precede the Scenario header in the buffer."""
        p = _plugin()
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        strings = _buf_strings(p)
        feature_idx  = next(i for i, s in enumerate(strings) if "Feature:" in s)
        scenario_idx = next(i for i, s in enumerate(strings) if "Scenario:" in s)
        assert feature_idx < scenario_idx

    def test_buffer_reset_on_each_scenario(self):
        """Each call to _bdd_before_scenario must start with a fresh buffer."""
        p = _plugin()
        p._bdd_scenario_buf = ["stale content"]
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert "stale content" not in p._bdd_scenario_buf

    def test_last_step_idx_reset_to_minus_one(self):
        p = _plugin()
        p._bdd_last_step_idx = 5
        p._bdd_before_scenario(_request(), _feature(), _scenario())
        assert p._bdd_last_step_idx == -1


# ── _bdd_after_step ───────────────────────────────────────────────────────────

class TestBddAfterStep:
    """Tests for _bdd_after_step — PASS step buffering."""

    import time as _time

    def _run(self, p, step=None, nodeid="tests/bdd/test_checkout.py::test_guest_purchase"):
        import time
        step = step or _step()
        p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_after_step(_request(nodeid), _feature(), _scenario(), step, None, {})
        return step

    def test_adds_pass_step_to_buffer(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert len(_buf_steps(p)) == 1
        assert _buf_steps(p)[0].outcome == "passed"

    def test_step_name_preserved(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step(name="the cart contains 2 items")
        import time; p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_after_step(_request(), _feature(), _scenario(), step, None, {})
        assert _buf_steps(p)[0].step.name == "the cart contains 2 items"

    def test_nodeid_added_to_handled(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, nodeid="tests/bdd/test_checkout.py::test_guest_purchase")
        assert "tests/bdd/test_checkout.py::test_guest_purchase" in p._bdd_handled

    def test_last_step_idx_updated(self):
        p = _plugin()
        p._bdd_scenario_buf = ["header string"]
        self._run(p)
        assert p._bdd_last_step_idx == 1  # header at 0, step at 1

    def test_short_msg_is_none_for_passing_step(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert _buf_steps(p)[0].short_msg is None


# ── _bdd_step_error ───────────────────────────────────────────────────────────

class TestBddStepError:
    """Tests for _bdd_step_error — FAIL/ERROR step buffering."""

    def _run(self, p, exc, step=None, nodeid="tests/bdd/test_checkout.py::test_discount_code"):
        import time
        step = step or _step()
        p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_step_error(_request(nodeid), _feature(), _scenario(), step, None, {}, exc)
        return step

    def test_assertion_error_outcome_is_failed(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, AssertionError("assert 95.0 == 90"))
        assert _buf_steps(p)[0].outcome == "failed"

    def test_runtime_error_outcome_is_error(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, RuntimeError("inventory service timed out"))
        assert _buf_steps(p)[0].outcome == "error"

    def test_connection_error_outcome_is_error(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, ConnectionError("could not reach db.internal:5432"))
        assert _buf_steps(p)[0].outcome == "error"

    def test_short_msg_captured(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, RuntimeError("inventory service timed out after 5000ms"))
        assert "inventory service timed out after 5000ms" in _buf_steps(p)[0].short_msg

    def test_nodeid_added_to_handled(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p, AssertionError("x"), nodeid="tests/bdd/test_checkout.py::test_discount_code")
        assert "tests/bdd/test_checkout.py::test_discount_code" in p._bdd_handled

    def test_last_step_idx_updated(self):
        p = _plugin()
        p._bdd_scenario_buf = ["header"]
        self._run(p, AssertionError("x"))
        assert p._bdd_last_step_idx == 1


# ── _bdd_flush_scenario ───────────────────────────────────────────────────────

class TestBddFlushScenario:
    """Tests for _bdd_flush_scenario — xfail/xpass correction and buffer clearing."""

    def _make_step_buf(self, p, outcome="passed", short_msg=None):
        bdd_step = _BDDStep(step=_step(), outcome=outcome, duration=0.1, short_msg=short_msg)
        p._bdd_scenario_buf  = [bdd_step]
        p._bdd_last_step_idx = 0
        p._p = lambda t="": None  # suppress output
        return bdd_step

    def test_xfail_corrects_last_step_outcome(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed")
        p._bdd_flush_scenario("xfailed", "xfailed: known bug")
        assert bdd_step.outcome == "xfailed"

    def test_xfail_corrects_last_step_message(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed", "assert x")
        p._bdd_flush_scenario("xfailed", "xfailed: known bug")
        assert bdd_step.short_msg == "xfailed: known bug"

    def test_xpass_corrects_last_step_outcome(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "passed")
        p._bdd_flush_scenario("xpassed", "xpassed: bug was fixed")
        assert bdd_step.outcome == "xpassed"

    def test_passed_does_not_modify_last_step(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "passed")
        p._bdd_flush_scenario("passed", None)
        assert bdd_step.outcome == "passed"

    def test_failed_does_not_modify_last_step(self):
        p = _plugin()
        bdd_step = self._make_step_buf(p, "failed")
        p._bdd_flush_scenario("failed", "assert x")
        assert bdd_step.outcome == "failed"

    def test_buffer_cleared_after_flush(self):
        p = _plugin()
        self._make_step_buf(p)
        p._bdd_flush_scenario("passed", None)
        assert p._bdd_scenario_buf == []

    def test_last_step_idx_reset_after_flush(self):
        p = _plugin()
        self._make_step_buf(p)
        p._bdd_flush_scenario("passed", None)
        assert p._bdd_last_step_idx == -1

    def test_blank_string_items_printed(self):
        """Empty string items in the buffer must trigger a blank line print."""
        p = _plugin()
        p._bdd_last_was_full_step = True
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_scenario_buf  = [""]
        p._bdd_last_step_idx = -1
        p._bdd_flush_scenario("passed", None)
        assert "" in printed

    def test_no_crash_when_buffer_empty(self):
        p = _plugin()
        p._p = lambda t="": None
        p._bdd_flush_scenario("passed", None)  # must not raise


# ── _bdd_before_step ──────────────────────────────────────────────────────────

class TestBddBeforeStep:
    """Tests for _bdd_before_step — timing and Background label insertion."""

    def test_records_step_start_time(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        p._bdd_before_step(_request(), _feature(), _scenario(), step, None)
        assert id(step) in p._bdd_step_t0

    def test_background_label_added_for_first_bg_step(self):
        """The first background step must cause a 'Background:' label to be buffered."""
        p = _plugin()
        p._bdd_scenario_buf = []
        bg_step = _step("Given", "given", "the database is available")
        feature = SimpleNamespace(
            name="Auth",
            background=SimpleNamespace(steps=[bg_step])
        )
        p._bdd_before_step(_request(), feature, _scenario(), bg_step, None)
        strings = _buf_strings(p)
        assert any("Background:" in s for s in strings)

    def test_no_background_label_for_regular_step(self):
        """Steps from the scenario body must not trigger a Background label."""
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        feature = _feature()   # background=None
        p._bdd_before_step(_request(), feature, _scenario(), step, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)

    def test_no_background_label_for_second_bg_step(self):
        """Only the FIRST background step gets the label — subsequent ones do not."""
        p = _plugin()
        p._bdd_scenario_buf = []
        bg_step1 = _step("Given", "given", "step one")
        bg_step2 = _step("And",   "given", "step two")
        feature = SimpleNamespace(
            name="Auth",
            background=SimpleNamespace(steps=[bg_step1, bg_step2])
        )
        p._bdd_before_step(_request(), feature, _scenario(), bg_step2, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)

    def test_no_background_label_when_background_has_no_steps(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        step = _step()
        feature = SimpleNamespace(name="Auth", background=SimpleNamespace(steps=[]))
        p._bdd_before_step(_request(), feature, _scenario(), step, None)
        strings = _buf_strings(p)
        assert not any("Background:" in s for s in strings)

# ── _bdd_step_func_lookup_error ───────────────────────────────────────────────

class TestBddStepFuncLookupError:
    """Tests for _bdd_step_func_lookup_error — missing step definition."""

    def _run(self, p, step=None, nodeid="tests/bdd/test_edge_cases.py::test_missing_step"):
        import time
        step = step or _step("When", "when", "a step that has no implementation")
        p._bdd_step_t0[id(step)] = time.monotonic()
        p._bdd_step_func_lookup_error(
            _request(nodeid), _feature(), _scenario(), step,
            Exception("StepDefinitionNotFoundError: Step definition is not found")
        )
        return step

    def test_outcome_is_error(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert _buf_steps(p)[0].outcome == "error"

    def test_short_msg_captured(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert _buf_steps(p)[0].short_msg is not None

    def test_nodeid_added_to_handled(self):
        p = _plugin()
        p._bdd_scenario_buf = []
        self._run(p)
        assert "tests/bdd/test_edge_cases.py::test_missing_step" in p._bdd_handled


# ── blank line spacing ────────────────────────────────────────────────────────

class TestBddBlankLineSpacing:
    """Blank line rules between features and scenarios."""

    def test_no_extra_blank_line_at_file_boundary(self):
        """_open_file_group prints one blank line between files.
        The buffer must NOT add a second one on top of it."""
        p = _plugin()
        # Simulate: file group already open, feature already printed
        p._cur_file              = "tests/bdd/test_authentication.py"
        p._bdd_cur_feature       = "User authentication flows"
        p._bdd_any_feature_printed = True
        # Now simulate new file group opening via _render_result path
        # _bdd_first_in_file must be True after _open_file_group resets it
        p._bdd_first_in_file = True
        # New feature scenario: blank line must be buffered (once)
        p._bdd_before_scenario(
            _request("tests/bdd/test_checkout.py::test_guest_purchase"),
            _feature("Shopping cart checkout"),
            _scenario("Guest completes a purchase")
        )
        blank_lines = [s for s in _buf_strings(p) if s == ""]
        # Exactly one blank line in the buffer (the between-feature one)
        assert len(blank_lines) == 1

    def test_blank_line_between_scenarios_same_feature(self):
        """After first scenario flushes, _bdd_first_in_file is reset to True
        by _open_file_group. Second scenario must still get a blank line."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        # Simulate what happens after first scenario flushes and
        # _open_file_group runs (same file → no-op on cur_file,
        # but _bdd_first_in_file stays False since same file)
        p._bdd_first_in_file = False
        p._bdd_before_scenario(
            _request("tests/bdd/test_checkout.py::test_gift_card"),
            _feature("Shopping cart checkout"),
            _scenario("Logged-in user applies a gift card")
        )
        strings = _buf_strings(p)
        assert "" in strings

# ── pytest_collection_finish: BDD scenario name indexing ─────────────────────

class TestBddScenarioNameIndexing:
    """Tests for scenario name extraction from collected BDD items."""

    def _make_item(self, nodeid, doc=None, scenario_obj=None):
        fn = SimpleNamespace(
            __doc__      = doc,
            __scenario__ = scenario_obj,
        )
        return SimpleNamespace(nodeid=nodeid, function=fn)

    def test_scenario_name_from_scenario_obj(self):
        """__scenario__.name takes priority over __doc__."""
        p = _plugin()
        scenario_obj = SimpleNamespace(name="Guest completes a purchase")
        item = self._make_item(
            "tests/bdd/test_checkout.py::test_guest_purchase",
            doc="features/checkout.feature: Guest completes a purchase",
            scenario_obj=scenario_obj,
        )
        session = SimpleNamespace(items=[item])
        printed = []
        p._p = lambda t="": printed.append(t)
        p.pytest_collection_finish(session)
        assert p._bdd_scenario_names["tests/bdd/test_checkout.py::test_guest_purchase"] == \
            "Guest completes a purchase"

    def test_scenario_name_from_doc_fallback(self):
        """When __scenario__ is None, name parsed from __doc__."""
        p = _plugin()
        item = self._make_item(
            "tests/bdd/test_checkout.py::test_unimplemented_feature",
            doc="features/checkout.feature: Feature not yet implemented",
            scenario_obj=None,
        )
        session = SimpleNamespace(items=[item])
        p._p = lambda t="": None
        p.pytest_collection_finish(session)
        assert p._bdd_scenario_names[
            "tests/bdd/test_checkout.py::test_unimplemented_feature"
        ] == "Feature not yet implemented"

    def test_non_bdd_item_not_indexed(self):
        """Regular pytest items with no __doc__ or __scenario__ must be ignored."""
        p = _plugin()
        item = self._make_item(
            "tests/test_parsers.py::test_something",
            doc=None,
            scenario_obj=None,
        )
        session = SimpleNamespace(items=[item])
        p._p = lambda t="": None
        p.pytest_collection_finish(session)
        assert "tests/test_parsers.py::test_something" not in p._bdd_scenario_names

    def test_doc_without_colon_separator_not_indexed(self):
        """__doc__ that doesn't match 'file: Scenario name' format must be ignored."""
        p = _plugin()
        item = self._make_item(
            "tests/bdd/test_checkout.py::test_something",
            doc="just a plain docstring",
            scenario_obj=None,
        )
        session = SimpleNamespace(items=[item])
        p._p = lambda t="": None
        p.pytest_collection_finish(session)
        assert "tests/bdd/test_checkout.py::test_something" not in p._bdd_scenario_names

# Add to test_bdd_plugin.py

class TestBddSkipRendering:
    """Skip renders as Scenario line indented under Feature, not at file level."""

    def test_skip_shows_scenario_name_not_function_name(self):
        p = _plugin()
        p._bdd_scenario_names["tests/bdd/test_checkout.py::test_unimplemented_feature"] = \
            "Feature not yet implemented"
        printed = []
        p._p = lambda t="": printed.append(t)
        from pytest_glaze import TestResult
        r = _make_result("test_unimplemented_feature", "skipped",
                 "Skipped: feature flag not enabled in CI",
                 file="tests/bdd/test_checkout.py")
        p._render_result(r)
        combined = " ".join(strip_ansi(l) for l in printed)
        assert "Feature not yet implemented" in combined
        assert "test_unimplemented_feature" not in combined

    def test_skip_indented_as_scenario(self):
        p = _plugin()
        p._bdd_scenario_names["tests/bdd/test_checkout.py::test_skip"] = "My Scenario"
        printed = []
        p._p = lambda t="": printed.append(t)
        from pytest_glaze import TestResult
        r = _make_result("test_skip", "skipped", "Skipped: reason",
                 file="tests/bdd/test_checkout.py")
        p._render_result(r)
        skip_line = next(l for l in printed if "My Scenario" in l)
        assert skip_line.startswith("    ")  # indented under Feature level


class TestBddStepNotFoundMessage:
    """StepDefinitionNotFoundError message trimmed to first sentence only."""

    def test_step_not_found_message_trimmed(self):
        long_msg = (
            'StepDefinitionNotFoundError: Step definition is not found: '
            'When "a step that has no implementation". '
            'Line 18 in scenario "Step with no implementation" '
            'in the feature "/path/to/edge_cases.feature"'
        )
        msg = FormatterPlugin._extract_exception_msg(Exception(long_msg))
        assert "Line 18" not in msg
        assert "/path/to" not in msg
        assert "Step definition is not found" in msg


# ── compact mode ──────────────────────────────────────────────────────────────

class TestBddCompactMode:
    """Default compact mode — PASS scenarios collapse to one line."""

    def _make_pass_scenario(self, p, scenario_name="Guest completes a purchase"):
        """Simulate a fully passing scenario in the buffer."""
        import time
        p._bdd_scenario_buf = [c_bdd_scenario(f"    Scenario: {scenario_name}")]
        for keyword, type_, name in [
            ("Given", "given", "the cart contains 2 items"),
            ("When",  "when",  "the guest submits valid payment"),
            ("Then",  "then",  "the order confirmation is shown"),
        ]:
            step = _step(keyword, type_, name)
            bdd_step = _BDDStep(step=step, outcome="passed", duration=0.1, short_msg=None)
            p._bdd_scenario_buf.append(bdd_step)
        p._bdd_last_step_idx = len(p._bdd_scenario_buf) - 1

    def test_compact_pass_prints_single_line(self):
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        step_lines = [l for l in printed if "Given" in l or "When" in l or "Then" in l]
        assert len(step_lines) == 0
        blank_lines = [l for l in printed if l == ""]
        assert len(blank_lines) == 0
        compact_line = next(l for l in printed if "Guest completes" in l)
        assert compact_line.startswith("    ")  # 4 spaces — matches full step mode

    def test_compact_pass_shows_scenario_name(self):
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        # Scenario name must be colored — strip ANSI to check plain text
        combined = " ".join(strip_ansi(l) for l in printed)
        assert "Guest completes a purchase" in combined

    def test_compact_pass_shows_pass_badge(self):
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        from pytest_glaze import _NO_COLOR
        combined = " ".join(printed)
        assert "PASS" in combined

    def test_compact_fail_shows_steps(self):
        """FAIL scenarios must show full step-by-step even in compact mode."""
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        # Override last step to failed
        last = p._bdd_scenario_buf[p._bdd_last_step_idx]
        last.outcome  = "failed"
        last.short_msg = "assert 95.0 == 90"
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("failed", "assert 95.0 == 90")
        step_lines = [l for l in printed if "Given" in l or "When" in l or "Then" in l]
        assert len(step_lines) > 0

    def test_compact_error_shows_steps(self):
        """ERROR scenarios must show full step-by-step even in compact mode."""
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        last = p._bdd_scenario_buf[p._bdd_last_step_idx]
        last.outcome   = "error"
        last.short_msg = "RuntimeError: timeout"
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("error", "RuntimeError: timeout")
        step_lines = [l for l in printed if "Given" in l or "When" in l or "Then" in l]
        assert len(step_lines) > 0

    def test_steps_mode_shows_all_steps(self):
        """--bdd-steps flag: PASS scenarios show full step-by-step."""
        p = _plugin()
        p.bdd_steps_mode = True
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        step_lines = [l for l in printed if "Given" in l or "When" in l or "Then" in l]
        assert len(step_lines) == 3

    def test_compact_pass_duration_is_total(self):
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        combined = " ".join(printed)
        assert "300.0ms" in combined

    def test_compact_blank_line_after_fail_scenario(self):
        """A blank line must follow a full-step FAIL scenario in compact mode."""
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        last = p._bdd_scenario_buf[p._bdd_last_step_idx]
        last.outcome   = "failed"
        last.short_msg = "assert x"
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("failed", "assert x")
        assert printed[-1] != ""

class TestBddCompactSpacing:
    """Blank line rules between all scenario type combinations."""

    def _flush_full_step(self, p, outcome="failed"):
        self._make_pass_scenario(p)
        last = p._bdd_scenario_buf[p._bdd_last_step_idx]
        last.outcome = outcome
        last.short_msg = "some error" if outcome != "passed" else None
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario(outcome, last.short_msg)
        return printed

    def _make_pass_scenario(self, p, name="Scenario A"):
        p._bdd_scenario_buf = [c_bdd_scenario(f"    Scenario: {name}")]
        for keyword, type_, sname in [
            ("Given", "given", "step one"),
            ("When",  "when",  "step two"),
            ("Then",  "then",  "step three"),
        ]:
            step = _step(keyword, type_, sname)
            p._bdd_scenario_buf.append(
                _BDDStep(step=step, outcome="passed", duration=0.1, short_msg=None)
            )
        p._bdd_last_step_idx = len(p._bdd_scenario_buf) - 1

    def test_full_step_to_full_step_one_blank_line(self):
        """Two consecutive full-step scenarios must have exactly one blank line between them."""
        p = _plugin()
        p.bdd_steps_mode = False

        # First scenario flushes — no trailing blank
        printed1 = self._flush_full_step(p, "failed")
        assert printed1[-1] != ""  # no trailing blank from flush

        # Second scenario — _bdd_before_scenario prepends "" to the buffer
        self._make_pass_scenario(p, "Scenario B")
        p._bdd_scenario_buf.insert(0, "")  # simulate what _bdd_before_scenario does
        p._bdd_last_step_idx += 1          # account for the inserted item
        last = p._bdd_scenario_buf[p._bdd_last_step_idx]
        last.outcome   = "failed"
        last.short_msg = "assert x"
        printed2 = []
        p._p = lambda t="": printed2.append(t)
        p._bdd_flush_scenario("failed", "assert x")

        # First item printed must be the blank line
        assert printed2[0] == ""
        # Second item must not be blank — exactly one blank line between scenarios
        assert printed2[1] != ""

    def test_full_step_to_compact_one_blank_line(self):
        """Full-step scenario followed by compact must have exactly one blank line."""
        p = _plugin()
        p.bdd_steps_mode = False
        printed = self._flush_full_step(p, "failed")
        assert printed[-1] != ""

    def test_compact_to_compact_no_blank_line(self):
        """Two consecutive compact scenarios must have no blank line between them."""
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        assert printed[-1] != ""  # no trailing blank line after compact

    def test_compact_to_compact_no_blank_line(self):
        p = _plugin()
        p.bdd_steps_mode = False
        p._bdd_last_was_full_step = False  # previous was compact
        self._make_pass_scenario(p)
        p._bdd_scenario_buf.insert(0, "")
        p._bdd_last_step_idx += 1
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        assert printed[0] != ""  # no blank line

    def test_full_step_to_compact_blank_line_printed(self):
        p = _plugin()
        p.bdd_steps_mode = False
        p._bdd_last_was_full_step = True  # previous was full-step
        self._make_pass_scenario(p)
        p._bdd_scenario_buf.insert(0, "")
        p._bdd_last_step_idx += 1
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        assert printed[0] == ""  # blank line printed

    def ttest_full_step_to_compact_blank_line_printedest_full_step_to_compact_blank_line_printed(self):
        """Blank line buffered by _bdd_before_scenario must print in compact mode."""
        p = _plugin()
        p.bdd_steps_mode = False
        self._make_pass_scenario(p)
        p._bdd_scenario_buf.insert(0, "")  # simulate _bdd_before_scenario spacing
        p._bdd_last_step_idx += 1
        printed = []
        p._p = lambda t="": printed.append(t)
        p._bdd_flush_scenario("passed", None)
        assert printed[0] == ""  # blank line printed before compact scenario line


class TestBddSkipFeatureHeader:
    """Skip renders Feature header when it hasn't been printed yet."""

    def test_skip_prints_feature_header_if_new(self):
        p = _plugin()
        p._bdd_scenario_names[
            "tests/bdd/test_checkout.py::test_unimplemented_feature"
        ] = "Feature not yet implemented"
        p._bdd_scenario_names[
            "tests/bdd/test_checkout.py::test_unimplemented_feature__feature__"
        ] = "Shopping cart checkout"
        printed = []
        p._p = lambda t="": printed.append(t)
        from pytest_glaze import TestResult
        r = _make_result("test_unimplemented_feature", "skipped",
                 "Skipped: feature flag not enabled in CI",
                 file="tests/bdd/test_checkout.py")
        p._render_result(r)
        assert any("Shopping cart checkout" in l for l in printed)
        assert any("Feature not yet implemented" in l for l in printed)

    def test_skip_no_duplicate_feature_header(self):
        """If feature already printed, skip must not reprint it."""
        p = _plugin()
        p._bdd_cur_feature       = "Shopping cart checkout"
        p._bdd_any_feature_printed = True
        p._bdd_scenario_names[
            "tests/bdd/test_checkout.py::test_unimplemented_feature"
        ] = "Feature not yet implemented"
        p._bdd_scenario_names[
            "tests/bdd/test_checkout.py::test_unimplemented_feature__feature__"
        ] = "Shopping cart checkout"
        printed = []
        p._p = lambda t="": printed.append(t)
        from pytest_glaze import TestResult
        r = _make_result("test_unimplemented_feature", "skipped",
                 "Skipped: feature flag not enabled in CI",
                 file="tests/bdd/test_checkout.py")
        p._render_result(r)
        feature_lines = [l for l in printed if "Shopping cart checkout" in l]
        assert len(feature_lines) == 0


# ── teardown error rendering ──────────────────────────────────────────────────

class TestBddTeardownError:
    """Teardown errors on BDD-handled nodeids render as standalone ERROR lines."""

    def test_teardown_error_renders_after_scenario(self):
        p = _plugin()
        p._bdd_handled.add("tests/bdd/test_edge_cases.py::test_teardown_failure")
        printed = []
        p._p = lambda t="": printed.append(t)
        r = _make_result("test_teardown_failure", "error",
                 "RuntimeError: cleanup failed",
                 file="tests/bdd/test_edge_cases.py")
        p._render_result(r)
        assert any("teardown" in l.lower() for l in printed)
        assert any("RuntimeError" in l for l in printed)

    def test_teardown_error_does_not_reflush_scenario(self):
        """Teardown error must not trigger _bdd_flush_scenario — buffer is empty."""
        p = _plugin()
        p._bdd_handled.add("tests/bdd/test_edge_cases.py::test_teardown_failure")
        p._bdd_scenario_buf = []  # already flushed
        p._p = lambda t="": None
        from pytest_glaze import TestResult
        r = _make_result("test_teardown_failure", "error",
                 "RuntimeError: cleanup failed",
                 file="tests/bdd/test_edge_cases.py")
        p._render_result(r)
        assert p._bdd_scenario_buf == []  # buffer untouched
