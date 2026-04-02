# tests/corpus/test_fixtures.py
"""
Covers fixture failure shapes:
  setup error, teardown error, chained fixture error, slow fixture.
All ERROR outcomes should surface with the RuntimeError message inline.
"""
import pytest


def test_pass_with_clean_fixture(clean_fixture):
    """Baseline: fixture works, test passes."""
    assert clean_fixture["value"] == 42


def test_error_broken_setup(broken_setup):
    """
    Fixture raises on setup.
    Expected outcome: ERROR (not FAIL) — the test body never runs.
    """
    pass   # never reached


def test_error_broken_teardown(broken_teardown):
    """
    Test body passes, but fixture raises on teardown.
    Expected outcome: PASS for call phase + ERROR for teardown phase.
    Both should appear in formatter output.
    """
    assert broken_teardown == "value"


def test_pass_slow_fixture(slow_fixture):
    """Verifies that fixture overhead shows up in duration."""
    assert slow_fixture == "slow"


# ── Chained fixture failure ───────────────────────────────────────────────────

@pytest.fixture
def depends_on_broken(broken_setup):
    """Depends on a fixture that always explodes."""
    return broken_setup  # never reached


def test_error_chained_fixture(depends_on_broken):
    """
    A fixture dependency chain fails at an intermediate node.
    Expected outcome: ERROR propagated from broken_setup.
    """
    pass
