"""
pytest_glaze — Opinionated pytest output formatter.

Public API re-exported from private modules.
"""
from pytest_glaze._types import MAX_E_LINES, TestResult, _BDDStep  # noqa: F401
from pytest_glaze._colors import _NO_COLOR, c_bdd_scenario  # noqa: F401
from pytest_glaze._colorizer import LineColorizer  # noqa: F401
from pytest_glaze._formatter import FormatterPlugin  # noqa: F401
from pytest_glaze._hooks import (  # noqa: F401
    _GLAZE_PLUGIN as _glaze_plugin,
    pytest_addoption,
    pytest_configure,
    pytest_bdd_before_scenario,
    pytest_bdd_before_step,
    pytest_bdd_after_step,
    pytest_bdd_step_error,
    pytest_bdd_step_func_lookup_error,
)
