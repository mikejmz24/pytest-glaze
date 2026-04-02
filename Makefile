# ── Settings ─────────────────────────────────────────────────────────────────

PYTHON   := python
PYTEST   := uv run pytest
TESTS    := tests/

# Core formatter flags.
# -p no:terminal   → silence the default reporter
# -p pytest_formatter → load our plugin (PYTHONPATH=. makes it importable)
FMT := -p no:terminal -p pytest_formatter

# Optional pass-through vars:
#   make test SUITE=tests/test_entities.py   → single suite
#   make test CASE=test_return_statuses_dict → single test by name
#   make test K="sprint and not slow"        → keyword expression
#   make test ARGS="--co -q"                 → arbitrary extra flags
SUITE ?=
CASE  ?=
K     ?=
ARGS  ?=

# Build the target path: SUITE if given, otherwise the whole TESTS dir.
_PATH := $(if $(SUITE),$(SUITE),$(TESTS))

# Build the -k filter: prefer K, fall back to CASE.
_KFLAG := $(if $(K),-k "$(K)",$(if $(CASE),-k "$(CASE)",))

# ── Primary targets ───────────────────────────────────────────────────────────

.PHONY: test test-fast test-corpus test-raw help

## test           Run suite with custom output.
##                SUITE=, CASE=, K= for filtering.  ARGS= for raw pytest flags.
##                Examples:
##                  make test
##                  make test SUITE=tests/test_entities.py
##                  make test CASE=test_return_statuses_dict
##                  make test K="sprint and not slow"
test:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(_PATH) $(_KFLAG) $(ARGS)

## test-fast      Stop on first failure (-x). Accepts same filters as `test`.
test-fast:
	@PYTHONPATH=. $(PYTEST) $(FMT) -x $(_PATH) $(_KFLAG) $(ARGS)

## test-corpus    Run the formatter's own validation corpus (tests/corpus/).
##                These tests are designed to exercise every output type —
##                intentional failures are expected and correct.
test-corpus:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/corpus/ $(ARGS)

## test-raw       Raw default pytest output. Useful for debugging the formatter.
test-raw:
	@$(PYTEST) $(_PATH) $(_KFLAG) $(ARGS)

## help           List all targets.
help:
	@grep -E '^##' Makefile | sed 's/^## /  /'
