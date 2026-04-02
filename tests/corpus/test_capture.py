# tests/corpus/test_capture.py
"""
Covers captured output surfacing:
  stdout on fail, stderr on fail, logging on fail, capsys usage.
Passing tests with output are captured silently (as pytest normally does).
"""
import logging
import sys
import pytest

log = logging.getLogger(__name__)


# ── Output captured silently (test passes) ────────────────────────────────────

def test_pass_with_stdout():
    print("captured stdout — not shown because the test passes")
    assert True


# ── Output surfaced in formatter (test fails) ─────────────────────────────────

def test_fail_with_stdout():
    print("this stdout should appear in the formatter's E section")
    assert False, "intentional failure with stdout"


def test_fail_with_stderr():
    print("error output attached to this failure", file=sys.stderr)
    assert False, "intentional failure with stderr"


def test_fail_with_logging():
    log.warning("warning-level log attached to this failure")
    log.error("error-level log attached to this failure")
    assert False, "intentional failure with log output"


# ── capsys ────────────────────────────────────────────────────────────────────

def test_capsys_pass(capsys):
    print("hello capsys")
    out, _ = capsys.readouterr()
    assert out.strip() == "hello capsys"


def test_capsys_fail(capsys):
    print("actual output")
    out, _ = capsys.readouterr()
    assert out.strip() == "expected different output"
