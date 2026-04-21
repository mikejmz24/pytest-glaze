"""
pytest_glaze/_colors.py — ANSI color helpers and outcome tables.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
Change the escape codes here to retheme everything.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Dict

_NO_COLOR = not sys.stdout.isatty() or bool(os.environ.get("NO_COLOR"))

# ── ANSI palette ──────────────────────────────────────────────────────────────

_RED_SOFT      = "0;38;2;252;205;174"   # 24-bit peach — c_emsg / context lines
_BRIGHT_GREEN  = "92"
_BRIGHT_RED    = "91"
_BRIGHT_YELLOW = "93"
_STANDARD_RED  = "31"
_GRAY          = "90"
_DIM           = "2"
_BOLD          = "1"
_BABY_BLUE     = "0;38;2;220;248;255"   # near-white bright blue — Feature
_STEEL_BLUE    = "0;38;2;170;225;255"   # sky blue — Scenario


# ── Escape helper ─────────────────────────────────────────────────────────────

def _esc(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


# ── Color functions ───────────────────────────────────────────────────────────

def c_pass(t: str) -> str:
    """Bright green — passing tests / expected values."""
    return _esc(_BRIGHT_GREEN, t)


def c_fail(t: str) -> str:
    """Bright red — FAIL badge, received values in assertions."""
    return _esc(_BRIGHT_RED, t)


def c_error(t: str) -> str:
    """Standard red — ERROR badge, collection errors, setup/teardown crashes."""
    return _esc(_STANDARD_RED, t)


def c_skip(t: str) -> str:
    """Bright yellow — skipped tests."""
    return _esc(_BRIGHT_YELLOW, t)


def c_xfail(t: str) -> str:
    """Bright red — expected failures."""
    return _esc(_BRIGHT_RED, t)


def c_xpass(t: str) -> str:
    """Yellow — unexpected passes."""
    return _esc(_BRIGHT_YELLOW, t)


def c_emsg(t: str) -> str:
    """Peach / soft red — E-line messages, context lines, assert keywords."""
    return _esc(_RED_SOFT, t)


def c_section(t: str) -> str:
    """Gray — captured output section headers."""
    return _esc(_GRAY, t)


def c_dim(t: str) -> str:
    """Dim — metadata, timing, context lines."""
    return _esc(_DIM, t)


def c_bold(t: str) -> str:
    """Bold — totals label."""
    return _esc(_BOLD, t)


def c_bdd_feature(t: str) -> str:
    """Baby blue — BDD Feature: label and name."""
    return _esc(_BABY_BLUE, t)


def c_bdd_scenario(t: str) -> str:
    """Steel blue — BDD Scenario: label and name."""
    return _esc(_STEEL_BLUE, t)


# ── Outcome tables ────────────────────────────────────────────────────────────

_OUTCOME_ORDER = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")

_BADGE: Dict[str, str] = {
    "passed":  c_pass("PASS"),
    "failed":  c_fail("FAIL"),
    "error":   c_error("ERROR"),
    "skipped": c_skip("SKIP"),
    "xfailed": c_xfail("XFAIL"),
    "xpassed": c_xpass("XPASS"),
}

_OUTCOME_COLOR: Dict[str, Callable[[str], str]] = {
    "passed":  c_pass,
    "failed":  c_fail,
    "error":   c_error,
    "skipped": c_skip,
    "xfailed": c_xfail,
    "xpassed": c_xpass,
}

_SUMMARY_FMT: Dict[str, Callable[[int], str]] = {
    "passed":  lambda n: c_pass(f"{n} passed"),
    "failed":  lambda n: c_fail(f"{n} failed"),
    "error":   lambda n: c_error(f"{n} error" if n == 1 else f"{n} errors"),
    "skipped": lambda n: c_skip(f"{n} skipped"),
    "xfailed": lambda n: c_xfail(f"{n} xfailed"),
    "xpassed": lambda n: c_xpass(f"{n} xpassed"),
}
