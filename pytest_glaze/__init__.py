"""
pytest_glaze — Opinionated pytest output formatter.

Public API surface (what users explicitly import):
    - FormatterPlugin
    - LineColorizer

Pytest discovers hook functions by introspecting this module via the
pytest11 entry point, so they must be importable here even though they
are not part of the user-facing API.
"""

from pytest_glaze._colorizer import LineColorizer
from pytest_glaze._formatter import FormatterPlugin

# Hooks: imported so pytest's name-based discovery can find them via
# getattr(pytest_glaze, "pytest_*"). NOT in __all__ — not for user import.
from pytest_glaze._hooks import (  # noqa: F401  pylint: disable=unused-import
    pytest_addoption,
    pytest_bdd_after_step,
    pytest_bdd_before_scenario,
    pytest_bdd_before_step,
    pytest_bdd_step_error,
    pytest_bdd_step_func_lookup_error,
    pytest_configure,
)

__all__ = [
    "FormatterPlugin",
    "LineColorizer",
]
