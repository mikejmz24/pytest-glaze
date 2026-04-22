"""
pytest_glaze/_hooks.py — Module-level pytest hooks and plugin registration.

Module-level BDD hooks are required by pytest-bdd 8's strict hookspec
validation which rejects 'self' in hookimpl signatures. They delegate to
the FormatterPlugin instance via _GLAZE_PLUGIN.

pytest_addoption and pytest_configure handle plugin registration.
"""
from __future__ import annotations

import io
from typing import Optional

import pytest

from pytest_glaze._formatter import FormatterPlugin

try:
    from _pytest._io import TerminalWriter as _PytestTerminalWriter
except ImportError:  # pragma: no cover
    _PytestTerminalWriter = None  # type: ignore[assignment,misc]

# Plugin instance — set in pytest_configure, None when glaze is inactive.
# BDD hook functions gate on this so they are no-ops without --glaze.
_GLAZE_PLUGIN: Optional[FormatterPlugin] = None


# ── BDD hooks (module-level) ──────────────────────────────────────────────────

def pytest_bdd_before_scenario(request, feature, scenario) -> None:
    if _GLAZE_PLUGIN is not None:
        _GLAZE_PLUGIN._bdd_before_scenario(request, feature, scenario)


def pytest_bdd_before_step(request, feature, scenario, step, step_func) -> None:
    if _GLAZE_PLUGIN is not None:
        _GLAZE_PLUGIN._bdd_before_step(request, feature, scenario, step, step_func)


def pytest_bdd_after_step(
    request, feature, scenario, step, step_func, step_func_args
) -> None:
    if _GLAZE_PLUGIN is not None:
        _GLAZE_PLUGIN._bdd_after_step(
            request, feature, scenario, step, step_func, step_func_args
        )


def pytest_bdd_step_error(
    request, feature, scenario, step, step_func, step_func_args, exception
) -> None:
    if _GLAZE_PLUGIN is not None:
        _GLAZE_PLUGIN._bdd_step_error(
            request, feature, scenario, step, step_func, step_func_args, exception
        )


def pytest_bdd_step_func_lookup_error(
    request, feature, scenario, step, exception
) -> None:
    if _GLAZE_PLUGIN is not None:
        _GLAZE_PLUGIN._bdd_step_func_lookup_error(
            request, feature, scenario, step, exception
        )


# ── Registration ──────────────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    """Declare the --glaze and --bdd-steps flags."""
    group = parser.getgroup("terminal reporting")
    group.addoption(
        "--glaze",
        action="store_true",
        default=False,
        help="Enable pytest-glaze compact, color-semantic output formatter.",
    )
    group.addoption(
        "--bdd-steps",
        action="store_true",
        default=False,
        help="Show full step-by-step BDD output. Default is compact (scenario lines only).",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """Activate glaze only when --glaze is explicitly requested.

    ``trylast=True`` guarantees this runs after the default terminal reporter
    has registered itself, so we can safely unregister it without racing
    against load order.

    When --glaze is passed:
      1. The default terminal reporter is unregistered and blocked.
      2. FormatterPlugin is registered to handle all output hooks.
      3. A TerminalReporterStub is registered so plugins that call
         config.get_terminal_writer() (e.g. pytest-cov) do not crash.

    When --glaze is absent the function returns immediately.
    """
    global _GLAZE_PLUGIN

    try:
        enabled = config.getoption("--glaze")
    except (ValueError, AttributeError):
        return

    if not enabled:
        return

    existing = config.pluginmanager.get_plugin("terminalreporter")
    if existing is not None:
        config.pluginmanager.unregister(existing)

    if not config.pluginmanager.is_blocked("terminal"):
        config.pluginmanager.set_blocked("terminal")

    _plugin_key = "_pytest_glaze_instance"
    existing = config.pluginmanager.get_plugin(_plugin_key)
    if existing is None:
        plugin = FormatterPlugin()
        plugin._bdd_steps_mode = config.getoption("--bdd-steps", default=False)
        config.pluginmanager.register(plugin, _plugin_key)
    else:
        plugin = existing

    _GLAZE_PLUGIN = plugin

    if (
        config.pluginmanager.get_plugin("terminalreporter") is None
        and _PytestTerminalWriter is not None
    ):
        _writer_cls = _PytestTerminalWriter

        class _TerminalReporterStub:  # pylint: disable=too-few-public-methods
            """Satisfies config.get_terminal_writer() without rendering anything."""

            def __init__(self) -> None:
                self._tw = _writer_cls(io.StringIO())

        config.pluginmanager.register(_TerminalReporterStub(), "terminalreporter")
