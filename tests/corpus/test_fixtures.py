# tests/corpus/test_fixtures.py
"""
Covers fixture failure shapes and fixture integration:
  setup error, teardown error, chained fixture error, slow fixture,
  fixture-level parametrize (params= on @pytest.fixture),
  and the request object pattern.

All ERROR outcomes should surface with the RuntimeError message inline.
Fixtures are defined in conftest.py.
"""
import pytest


# ── Passing baseline ──────────────────────────────────────────────────────────

def test_pass_with_clean_fixture(clean_fixture):
    """Baseline: fixture works, test passes, duration includes fixture overhead."""
    assert clean_fixture["value"] == 42


def test_pass_slow_fixture(slow_fixture):
    """slow_fixture sleeps 20ms — verifies fixture overhead shows in duration."""
    assert slow_fixture == "slow"


# ── Setup errors ──────────────────────────────────────────────────────────────

def test_error_broken_setup(broken_setup):
    """Fixture raises on setup → ERROR outcome (not FAIL); test body never runs.
    Exercises the when='setup' branch of classify()."""
    pass  # never reached


# ── Teardown errors ───────────────────────────────────────────────────────────

def test_error_broken_teardown(broken_teardown):
    """Test body passes, fixture raises on teardown.
    Expected output: PASS line for the call phase immediately followed by
    an ERROR line for teardown — both from the same test, same file group.
    Exercises the when='teardown' branch of classify()."""
    assert broken_teardown == "value"


# ── Chained fixture failure ───────────────────────────────────────────────────

@pytest.fixture
def depends_on_broken(broken_setup):
    """Depends on a fixture that always explodes."""
    return broken_setup  # never reached

def test_error_chained_fixture(depends_on_broken):
    """A fixture dependency chain fails at an intermediate node.
    Error propagates from broken_setup through depends_on_broken."""
    pass  # never reached


# ── Fixture-level parametrize (params= on @pytest.fixture) ───────────────────
# This is distinct from @pytest.mark.parametrize: the param is declared on the
# fixture, not the test. Node IDs look like test_name[alpha], test_name[beta].

def test_pass_parametrized_fixture(parametrized_fixture):
    """All three fixture params satisfy this assertion — three PASS lines."""
    assert len(parametrized_fixture["label"]) == parametrized_fixture["value"]

def test_fail_parametrized_fixture(parametrized_fixture):
    """Always fails — shows [alpha], [beta], [gamma] variants in the output,
    each with its own E-line colored independently."""
    assert parametrized_fixture["value"] == 99


# ── Request object ────────────────────────────────────────────────────────────
# The request object gives fixtures access to test context. This pattern is
# ubiquitous in real codebases; the formatter must handle its output shapes.

@pytest.fixture
def request_aware_fixture(request):
    """Uses request.node.name to inject test-context data."""
    return {"test_name": request.node.name, "status": "initialized"}

def test_pass_request_fixture(request_aware_fixture):
    """Fixture built with request.node.name — verifies request pattern works."""
    assert "test_pass_request_fixture" in request_aware_fixture["test_name"]

def test_fail_request_fixture(request_aware_fixture):
    """Failing test with a request-aware fixture — E-line shows assertion failure,
    not a fixture error."""
    assert request_aware_fixture["status"] == "finalized"  # wrong value
