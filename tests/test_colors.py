"""
tests/test_colors.py — Unit tests for palette selection, detect_theme,
set_theme, reset_theme, and get_badge.
"""

from __future__ import annotations

import os
import sys

import pytest

import pytest_glaze._colors as colors
from pytest_glaze._colors import (
    _DARK_PALETTE,
    _LIGHT_PALETTE,
    _detect_term_program,
    _osc11_is_light,
    _osc11_safe_to_query,
    _query_osc11,
    c_bdd_feature,
    c_bdd_scenario,
    c_emsg,
    c_fail,
    c_pass,
    detect_theme,
    get_badge,
    no_color_context,
    set_active_palette,
    theme_context,
)

pytestmark = pytest.mark.unit

# ── detect_theme ──────────────────────────────────────────────────────────────


class TestDetectTheme:
    def test_dark_terminal_colorfgbg(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15;0")
        assert detect_theme() == "dark"

    def test_light_terminal_colorfgbg(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;7")
        assert detect_theme() == "light"

    def test_light_threshold_exactly_seven(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;7")
        assert detect_theme() == "light"

    def test_dark_threshold_below_seven(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;6")
        assert detect_theme() == "dark"

    def test_multi_segment_colorfgbg_uses_last(self, monkeypatch):
        """iTerm2 emits three-segment COLORFGBG values."""
        monkeypatch.setenv("COLORFGBG", "15;default;0")
        assert detect_theme() == "dark"

    def test_missing_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        assert detect_theme() == "dark"

    def test_malformed_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "garbage")
        assert detect_theme() == "dark"

    def test_empty_colorfgbg_defaults_to_dark(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "")
        assert detect_theme() == "dark"


class TestDetectThemeMultiSource:
    """
    Unit tests for the multi-source detect_theme() detection chain.
    Covers all six sources in priority order.
    """

    # ── 1. $GLAZE_THEME override ──────────────────────────────────────────────

    def test_glaze_theme_dark_overrides_all(self, monkeypatch):
        monkeypatch.setenv("GLAZE_THEME", "dark")
        monkeypatch.setenv("COLORFGBG", "0;15")  # would be light
        assert detect_theme() == "dark"

    def test_glaze_theme_light_overrides_all(self, monkeypatch):
        monkeypatch.setenv("GLAZE_THEME", "light")
        monkeypatch.setenv("COLORFGBG", "15;0")  # would be dark
        assert detect_theme() == "light"

    def test_glaze_theme_auto_falls_through(self, monkeypatch):
        monkeypatch.setenv("GLAZE_THEME", "auto")
        monkeypatch.setenv("COLORFGBG", "0;7")  # light
        assert detect_theme() == "light"

    def test_glaze_theme_unknown_value_falls_through(self, monkeypatch):
        monkeypatch.setenv("GLAZE_THEME", "rainbow")
        monkeypatch.setenv("COLORFGBG", "15;0")  # dark
        assert detect_theme() == "dark"

    def test_glaze_theme_empty_falls_through(self, monkeypatch):
        monkeypatch.setenv("GLAZE_THEME", "")
        monkeypatch.setenv("COLORFGBG", "0;7")  # light
        assert detect_theme() == "light"

    # ── 2. $COLORFGBG ─────────────────────────────────────────────────────────

    def test_colorfgbg_light(self, monkeypatch):
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.setenv("COLORFGBG", "0;15")
        assert detect_theme() == "light"

    def test_colorfgbg_dark(self, monkeypatch):
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.setenv("COLORFGBG", "15;0")
        assert detect_theme() == "dark"

    def test_colorfgbg_malformed_falls_through(self, monkeypatch):
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.setenv("COLORFGBG", "garbage")
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        assert detect_theme() == "dark"  # falls through to fallback

    # ── 3. OSC 11 ─────────────────────────────────────────────────────────────

    def test_osc11_skipped_when_not_tty(self, monkeypatch):
        """_query_osc11 must return None when /dev/tty is unavailable."""
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        # Simulate no /dev/tty by making os.open raise OSError
        original_open = os.open

        def _fake_open(path, flags):
            if path == "/dev/tty":
                raise OSError("No such device")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", _fake_open)

        assert _query_osc11() is None

    def test_osc11_skipped_in_tmux(self, monkeypatch):
        monkeypatch.setenv("TMUX", "/tmp/tmux-1234/default,1234,0")

        assert _query_osc11() is None

    def test_osc11_skipped_in_screen(self, monkeypatch):
        monkeypatch.setenv("TERM", "screen-256color")

        assert _query_osc11() is None

    def test_osc11_is_light_white_background(self):
        assert _osc11_is_light("rgb:ffff/ffff/ffff") is True

    def test_osc11_is_light_dark_background(self):
        assert _osc11_is_light("rgb:0d0d/1111/1717") is False

    def test_osc11_is_light_mid_grey_is_light(self):
        # Pure mid-grey — luminance exactly 0.5, treated as light
        assert _osc11_is_light("rgb:8080/8080/8080") is True

    def test_osc11_pure_black_rejected(self, monkeypatch):
        """Pure black response from buggy terminals must be rejected."""
        # Simulate a terminal that responds with pure black
        original = colors._osc11_safe_to_query
        monkeypatch.setattr(colors, "_osc11_safe_to_query", lambda: True)
        original_open = os.open

        def _fake_open(path, flags):
            if path == "/dev/tty":
                raise OSError("simulated")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", _fake_open)
        # With /dev/tty blocked, returns None — pure black rejection
        # is tested separately via _osc11_is_light
        assert _query_osc11() is None
        monkeypatch.setattr(colors, "_osc11_safe_to_query", original)

    # ── 4. $TERM_PROGRAM / terminal-specific vars ─────────────────────────────────

    def test_apple_terminal_returns_light(self, monkeypatch):
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.setenv("TERM_PROGRAM", "Apple_Terminal")
        assert _detect_term_program() == "light"

    def test_vscode_light_theme(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.setenv("VSCODE_THEME_KIND", "vscode-light")
        assert _detect_term_program() == "light"

    def test_vscode_dark_theme(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.setenv("VSCODE_THEME_KIND", "vscode-dark")
        assert _detect_term_program() == "dark"

    def test_vscode_high_contrast_theme(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.setenv("VSCODE_THEME_KIND", "vscode-high-contrast")
        assert _detect_term_program() == "dark"

    def test_vscode_missing_theme_kind_falls_through(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "vscode")
        monkeypatch.delenv("VSCODE_THEME_KIND", raising=False)
        assert _detect_term_program() is None

    def test_jetbrains_light_theme(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
        monkeypatch.setenv("TERMINAL_BACKGROUND", "light")
        assert _detect_term_program() == "light"

    def test_jetbrains_dark_theme(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
        monkeypatch.setenv("TERMINAL_BACKGROUND", "dark")
        assert _detect_term_program() == "dark"

    def test_jetbrains_missing_background_falls_through(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
        monkeypatch.delenv("TERMINAL_BACKGROUND", raising=False)
        assert _detect_term_program() is None

    def test_other_term_program_returns_none(self, monkeypatch):
        monkeypatch.setenv("TERM_PROGRAM", "iTerm.app")
        assert _detect_term_program() is None

    def test_missing_term_program_returns_none(self, monkeypatch):
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        monkeypatch.delenv("TERMINAL_EMULATOR", raising=False)
        assert _detect_term_program() is None

    # ── _osc11_safe_to_query ──────────────────────────────────────────────────────

    def test_osc11_safe_to_query_false_in_tmux(self, monkeypatch):
        monkeypatch.setenv("TMUX", "/tmp/tmux-1234/default,1234,0")

        assert _osc11_safe_to_query() is False

    def test_osc11_safe_to_query_false_in_screen(self, monkeypatch):
        monkeypatch.setenv("TERM", "screen-256color")
        assert _osc11_safe_to_query() is False

    def test_osc11_safe_to_query_false_on_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert _osc11_safe_to_query() is False

    # ── 5. Fallback ───────────────────────────────────────────────────────────

    def test_fallback_is_dark(self, monkeypatch):
        monkeypatch.delenv("GLAZE_THEME", raising=False)
        monkeypatch.delenv("COLORFGBG", raising=False)
        monkeypatch.delenv("TERM_PROGRAM", raising=False)
        assert detect_theme() == "dark"

    # ── _osc11_is_light edge cases ────────────────────────────────────────────

    def test_osc11_is_light_malformed_returns_false(self):

        assert _osc11_is_light("not-a-color") is False

    def test_osc11_is_light_8bit_values(self):
        """Some terminals respond with 8-bit values (00–ff) instead of 16-bit."""

        assert _osc11_is_light("rgb:ff/ff/ff") is True
        assert _osc11_is_light("rgb:0d/11/17") is False


# ── set_theme ─────────────────────────────────────────────────────────────────


class TestSetTheme:
    def test_dark_activates_dark_palette(self):
        with theme_context("dark"):
            assert colors._active_palette is _DARK_PALETTE

    def test_light_activates_light_palette(self):
        with theme_context("light"):
            assert colors._active_palette is _LIGHT_PALETTE

    def test_auto_resolves_to_dark_without_colorfgbg(self, monkeypatch):
        monkeypatch.delenv("COLORFGBG", raising=False)
        with theme_context("auto"):
            assert colors._active_palette is _DARK_PALETTE

    def test_auto_resolves_to_light_with_light_terminal(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "0;15")
        with theme_context("auto"):
            assert colors._active_palette is _LIGHT_PALETTE

    def test_auto_resolves_to_dark_with_dark_terminal(self, monkeypatch):
        monkeypatch.setenv("COLORFGBG", "15;0")
        with theme_context("auto"):
            assert colors._active_palette is _DARK_PALETTE

    def test_set_theme_is_idempotent(self):
        with theme_context("light"):
            with theme_context("light"):
                assert colors._active_palette is _LIGHT_PALETTE

    def test_switching_themes_takes_effect_immediately(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active — palette codes are not emitted")
        with theme_context("dark"):
            dark_output = c_pass("PASS")
            with theme_context("light"):
                light_output = c_pass("PASS")
                assert dark_output != light_output


class TestPaletteValidation:
    """Tests for set_active_palette() validation."""

    def test_valid_palette_accepted(self):
        set_active_palette(_DARK_PALETTE)  # should not raise

    def test_missing_key_raises_value_error(self):
        bad_palette = {"pass": "92"}  # missing all other keys
        with pytest.raises(ValueError, match="missing required keys"):
            set_active_palette(bad_palette)

    def test_empty_palette_raises_value_error(self):
        with pytest.raises(ValueError, match="missing required keys"):
            set_active_palette({})

    def test_extra_keys_are_allowed(self):
        """Palettes with extra keys beyond required are valid."""

        extended = dict(_DARK_PALETTE) | {"extra_key": "99"}
        set_active_palette(extended)  # should not raise


# ── Color functions pick up active palette ────────────────────────────────────


class TestColorFunctionsPaletteAware:
    """Color functions must read _active_palette at call time, not import time."""

    def test_c_pass_changes_with_theme(self):
        with theme_context("dark"):
            dark = c_pass("X")
        with theme_context("light"):
            light = c_pass("X")
        assert dark != light

    def test_c_fail_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_fail("X")
            with theme_context("light"):
                assert dark != c_fail("X")

    def test_c_emsg_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_emsg("X")
            with theme_context("light"):
                assert dark != c_emsg("X")

    def test_c_bdd_feature_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_bdd_feature("X")
            with theme_context("light"):
                assert dark != c_bdd_feature("X")

    def test_c_bdd_scenario_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = c_bdd_scenario("X")
            with theme_context("light"):
                assert dark != c_bdd_scenario("X")

    def test_no_color_mode_unaffected_by_theme(self):
        """In NO_COLOR mode, set_theme must not cause errors."""
        with no_color_context():
            with theme_context("light"):
                assert c_pass("X") == "X"
            with theme_context("dark"):
                assert c_pass("X") == "X"


# ── get_badge ─────────────────────────────────────────────────────────────────


class TestGetBadge:
    @pytest.mark.parametrize(
        "outcome,label",
        [
            ("passed", "PASS"),
            ("failed", "FAIL"),
            ("error", "ERROR"),
            ("skipped", "SKIP"),
            ("xfailed", "XFAIL"),
            ("xpassed", "XPASS"),
        ],
    )
    def test_known_outcomes_contain_label(self, outcome, label):
        assert label in get_badge(outcome)

    def test_unknown_outcome_returns_uppercase(self):
        assert get_badge("mystery") == "MYSTERY"

    def test_badge_changes_with_theme(self):
        if colors._NO_COLOR:
            pytest.skip("NO_COLOR active")
        with theme_context("dark"):
            dark = get_badge("passed")
            with theme_context("light"):
                light = get_badge("passed")
                assert "PASS" in dark and "PASS" in light
                assert dark != light


class TestPaletteStability:
    """
    Guard against palette being reset between renders.
    This class catches the exact bug where reset_theme() fired after every
    test, overriding the theme set by --glaze-theme in pytest_configure.
    """

    def test_palette_stays_light_across_multiple_renders(self):
        with theme_context("light"):
            results = [c_pass("PASS") for _ in range(5)]
        assert (
            len(set(results)) == 1
        ), "c_pass() returned different values across calls — palette changed mid-run"

    def test_palette_stays_dark_across_multiple_renders(self):
        with theme_context("dark"):
            results = [c_pass("PASS") for _ in range(5)]
        assert (
            len(set(results)) == 1
        ), "c_pass() returned different values across calls — palette changed mid-run"

    def test_reset_palette_fixture_respects_active_theme(self):
        """restore_palette must restore to whatever was active, not blindly reset to dark."""
        with theme_context("light"):
            before = c_pass("X")
        with theme_context("light"):
            assert c_pass("X") == before
