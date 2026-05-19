"""
tests/helpers.py — Shared test utilities for all pytest-glaze test files.

Single source of truth for:
  - ANSI color constants (derived from _colors.py)
  - strip_ansi / is_colorless / has_color helpers
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pytest_glaze._colors import _DARK_PALETTE
from pytest_glaze._types import Outcome, TestResult, _BDDStep

GREEN = f"\033[{_DARK_PALETTE['pass']}m"
BRIGHT_RED = f"\033[{_DARK_PALETTE['fail']}m"
YELLOW = f"\033[{_DARK_PALETTE['skip']}m"
STANDARD_RED = f"\033[{_DARK_PALETTE['error']}m"
SOFT_PEACH = f"\033[{_DARK_PALETTE['emsg']}m"
DIM = f"\033[{_DARK_PALETTE['dim']}m"
BABY_BLUE = f"\033[{_DARK_PALETTE['bdd_feature']}m"
STEEL_BLUE = f"\033[{_DARK_PALETTE['bdd_scenario']}m"


# ── ANSI helpers ──────────────────────────────────────────────────────────────


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return re.sub(r"\033\[[\d;]*m?", "", text)


def is_colorless(text: str) -> bool:
    """Return True if text contains no ANSI escape sequences."""
    return not re.search(r"\033\[[\d;]*m", text)


def has_color(text: str, color: str) -> bool:
    """Return True if text contains the given ANSI color code."""
    return color in text


def name_is_uncolored(line: str, name: str) -> bool:
    """Return True if `name` appears in `line` outside any ANSI color block.

    Unlike is_colorless(), this checks a specific substring rather than
    the entire line — useful for lines that are partially colored.
    """
    segments = re.split(r"(\033\[[\d;]*m)", line)
    in_color = False
    for seg in segments:
        if re.match(r"\033\[[\d;]*m", seg):
            in_color = seg != "\033[0m"
        elif name in seg and not in_color:
            return True
    return False


# ── Test result factories ─────────────────────────────────────────────────────


def make_result(
    name: str = "test_example",
    outcome: Outcome = "passed",
    short_msg: str | None = None,
    duration: float = 0.1,
    sections: list | None = None,
    file: str = "tests/test_example.py",
) -> TestResult:
    return TestResult(
        nodeid=f"{file}::{name}",
        file=file,
        name=name,
        outcome=outcome,
        duration=duration,
        short_msg=short_msg,
        sections=sections or [],
    )


@dataclass
class _StepStub:
    """Test double for _StepLike protocol."""

    keyword: str = "Given"
    name: str = "the cart contains 2 items"


def _make_step(
    keyword: str = "Given", name: str = "the cart contains 2 items"
) -> _StepStub:
    return _StepStub(keyword=keyword, name=name)


def make_bdd_step(
    keyword: str = "Given",
    name: str = "step",
    outcome: Outcome = "passed",
    duration: float = 0.1,
    short_msg: str | None = None,
) -> _BDDStep:
    return _BDDStep(
        step=_make_step(keyword, name),
        outcome=outcome,
        duration=duration,
        short_msg=short_msg,
    )
