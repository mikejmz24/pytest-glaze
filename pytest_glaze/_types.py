"""
pytest_glaze/_types.py — Shared types and constants.

No dependencies on other pytest_glaze modules — safe to import from anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

MAX_E_LINES: int = 15


@dataclass
class TestResult:
    """Normalised result for a single test, ready for rendering."""

    nodeid:    str
    file:      str
    name:      str
    outcome:   str                        # one of _OUTCOME_ORDER
    duration:  float                      # seconds
    short_msg: Optional[str] = None       # one-liner shown on the E line
    sections:  List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class _BDDStep:
    """Buffered BDD step waiting to be rendered at scenario flush time."""

    step:      Any
    outcome:   str
    duration:  float
    short_msg: Optional[str]
    test_outcome:  str            = "passed"   # expected outcome for flush — testing only
    test_short_msg: Optional[str] = None       # expected short_msg for flush — testing only


@dataclass
class _BDDState:  # pylint: disable=too-many-instance-attributes
    """
    Mutable BDD rendering state — owned by FormatterPlugin.

    Extracted from FormatterPlugin to:
      - Reduce instance attribute count (fixes too-many-instance-attributes)
      - Provide a clean boundary for BDD-specific state
      - Allow tests to access state through plugin.bdd without touching
        protected members
    """

    # Step timing — maps id(step) → start time, consumed in after/error hooks
    step_t0:             Dict[int, float] = field(default_factory=dict)

    # nodeids rendered via BDD hooks — skip normal rendering for these
    handled:             Set[str]         = field(default_factory=set)

    # Spacing — True until the first scenario in a file has been processed
    first_in_file:       bool             = True

    # Buffer of strings and _BDDStep items for the current scenario
    scenario_buf:        List             = field(default_factory=list)

    # Index of the last _BDDStep in scenario_buf (-1 if none)
    last_step_idx:       int              = -1

    # nodeid → scenario name (for skip rendering)
    # nodeid + "__feature__" → feature name
    scenario_names:      Dict[str, str]   = field(default_factory=dict)

    # Currently printed feature name — prevents duplicate Feature headers
    cur_feature:         Optional[str]    = None

    # True once at least one Feature header has been printed
    any_feature_printed: bool             = False

    # File path deferred from before_scenario until render time
    pending_file:        Optional[str]    = None

    # True = --bdd-steps flag: show all steps. False = compact (default)
    steps_mode:          bool             = False

    # True when the last scenario was rendered in full-step mode
    last_was_full_step:  bool             = False

    # Test-only fields — used by acceptance tests to set expected flush outcome
    test_outcome:   str            = "passed"
    test_short_msg: Optional[str]  = None


@dataclass
class _SessionState:
    """
    Session-level state for FormatterPlugin.

    Extracted to:
      - Reduce FormatterPlugin instance attribute count
      - Group session-scoped data cleanly
      - Allow tests to access session state through plugin.session
    """

    t0:         float                         = 0.0
    results:    List["TestResult"]            = field(default_factory=list)
    col_errors: List[Tuple[str, str]]         = field(default_factory=list)
    output_buf: Optional[List[str]]           = None


__all__ = ["MAX_E_LINES", "TestResult", "_BDDStep", "_BDDState", "_SessionState"]
