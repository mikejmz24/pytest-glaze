# tests/corpus/test_capture.py
"""
Covers captured output surfacing in the formatter's section blocks:
  stdout on fail, stderr on fail, logging on fail, capsys, caplog,
  combined stdout+stderr, long output, and passing tests where output
  is captured silently.

The formatter renders report.sections (──Captured stdout──, etc.) only
for non-passing outcomes. NOTE: do not run with --log-cli-level — it requires the full terminal reporter
interface which the formatter stub does not implement.

Every failing test here must produce at least
one visible section in the output.
"""
import logging
import sys

log = logging.getLogger(__name__)


# ── Output captured silently (test passes) ────────────────────────────────────

def test_pass_with_stdout():
    """Captured stdout on a passing test — formatter must not show sections."""
    print("captured stdout — not shown because the test passes")
    assert True


def test_pass_with_logging():
    """Captured log on a passing test — sections suppressed on pass."""
    log.warning("suppressed warning log")
    assert True


# ── Stdout ────────────────────────────────────────────────────────────────────

def test_fail_with_stdout():
    """Single print — exercises the ──Captured stdout call── section."""
    print("this stdout should appear in the formatter's E section")
    assert False, "intentional failure with stdout"


def test_fail_with_stdout_multiline():
    """Multiple print statements — section must render all lines, not truncate."""
    for i in range(8):
        print(f"stdout line {i + 1:02}: payload {'x' * 40}")
    assert False, "intentional failure with multi-line stdout"


def test_fail_with_long_stdout():
    """Very long output — verifies the formatter does not clip section content."""
    for i in range(25):
        print(f"line {i:03}: {'a' * 80}")
    assert False, "intentional failure with long captured output"


# ── Stderr ────────────────────────────────────────────────────────────────────

def test_fail_with_stderr():
    """Stderr output — exercises the ──Captured stderr call── section."""
    print("error output attached to this failure", file=sys.stderr)
    assert False, "intentional failure with stderr"


# ── Combined stdout + stderr ──────────────────────────────────────────────────

def test_fail_with_stdout_and_stderr():
    """Both stdout and stderr in one failing test — verifies that the formatter
    renders two separate section headers, in the correct order (stdout first)."""
    print("stdout payload for combined capture test")
    print("stderr payload for combined capture test", file=sys.stderr)
    assert False, "intentional failure with stdout and stderr"


# ── Logging ───────────────────────────────────────────────────────────────────

def test_fail_with_logging():
    """Multiple log levels — exercises the ──Captured log call── section.
    All levels from DEBUG through ERROR must appear in the section."""
    log.debug("debug-level message")
    log.info("info-level message")
    log.warning("warning-level log attached to this failure")
    log.error("error-level log attached to this failure")
    assert False, "intentional failure with log output"


# ── capsys ────────────────────────────────────────────────────────────────────

def test_capsys_pass(capsys):
    """capsys readouterr — passing case; formatter shows no section."""
    print("hello capsys")
    out, _ = capsys.readouterr()
    assert out.strip() == "hello capsys"


def test_capsys_fail(capsys):
    """capsys assertion failure — no stdout section because capsys consumed it,
    but the assertion E-line is still colored normally."""
    print("actual output")
    out, _ = capsys.readouterr()
    assert out.strip() == "expected different output"


# ── caplog ────────────────────────────────────────────────────────────────────

def test_caplog_pass(caplog):
    """caplog — passing case; confirms structured log capture works."""
    with caplog.at_level(logging.INFO):
        log.info("structured log message")
    assert "structured log message" in caplog.text


def test_caplog_fail_wrong_message(caplog):
    """caplog assertion failure — exercises the E-line for a caplog-based assert."""
    with caplog.at_level(logging.WARNING):
        log.warning("actual warning text")
    assert "expected warning text" in caplog.text


def test_caplog_fail_wrong_level(caplog):
    """caplog level filtering — only captures at WARNING and above; DEBUG is absent."""
    with caplog.at_level(logging.WARNING):
        log.debug("this debug line is filtered out")
    assert len(caplog.records) == 1, f"expected 1 record, got {len(caplog.records)}"
