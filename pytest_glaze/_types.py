"""
pytest_glaze/_types.py — Shared types and constants.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Protocol, Set, Tuple, Union

MAX_E_LINES: int = 15

# Canonical outcome strings — must stay aligned with _OUTCOME_ORDER in _colors.
Outcome = Literal["passed", "failed", "skipped", "error", "xfailed", "xpassed"]


class _StepLike(Protocol):
    """
    Structural type for pytest-bdd Step objects — only attrs we read.

    Using a Protocol instead of importing pytest_bdd.parser.Step keeps this
    module dependency-free and decoupled from pytest-bdd's internal API.
    """

    name: str
    keyword: str


@dataclass(slots=True)
class TestResult:
    """Normalised result for a single test, ready for rendering."""

    nodeid: str
    file: str
    name: str
    outcome: Outcome
    duration: float  # seconds
    short_msg: Optional[str] = None  # one-liner shown on the E line
    sections: List[Tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class ScenarioMeta:
    """
    Metadata captured at collection time for a single BDD scenario.

    Replaces the previous magic-key pattern where feature names were stored
    under `nodeid + "__feature__"` in the same dict as scenario names.
    """

    scenario_name: str
    feature_name: Optional[str] = None


@dataclass(slots=True)
class _BDDStep:
    """Buffered BDD step waiting to be rendered at scenario flush time."""

    step: _StepLike
    outcome: Outcome
    duration: float
    short_msg: Optional[str]


@dataclass(slots=True)
class _BDDState:  # pylint: disable=too-many-instance-attributes
    """
    Mutable BDD rendering state — owned by FormatterPlugin.

    Extracted from FormatterPlugin to:
      - Reduce instance attribute count
      - Provide a clean boundary for BDD-specific state
      - Allow tests to access state through plugin.bdd without touching
        protected members
    """

    step_t0: Dict[int, float] = field(default_factory=dict)
    handled: Set[str] = field(default_factory=set)
    first_in_file: bool = True
    scenario_buf: List[Union[str, _BDDStep]] = field(default_factory=list)
    last_step_idx: int = -1
    scenario_meta: Dict[str, ScenarioMeta] = field(default_factory=dict)
    cur_feature: Optional[str] = None
    any_feature_printed: bool = False
    pending_file: Optional[str] = None
    steps_mode: bool = False
    last_was_full_step: bool = False


@dataclass(slots=True)
class _SessionState:
    """Session-level state for FormatterPlugin."""

    t0: float = 0.0
    col_errors: List[Tuple[str, str]] = field(default_factory=list)
    output_buf: Optional[List[str]] = None
    counts: Dict[str, int] = field(default_factory=dict)


__all__ = [
    "MAX_E_LINES",
    "Outcome",
    "TestResult",
    "ScenarioMeta",
    "_BDDStep",
    "_BDDState",
    "_SessionState",
]
