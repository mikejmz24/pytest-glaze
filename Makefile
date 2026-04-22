# ── Settings ─────────────────────────────────────────────────────────────────

PYTHON   := python
PYTEST   := uv run python -m pytest
TESTS    := tests/

# Core formatter flags.
# -p no:terminal   → silence the default reporter
# -p pytest_glaze → load our plugin (PYTHONPATH=. makes it importable)
FMT := --glaze

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

# ── BDD settings ──────────────────────────────────────────────────────────────
# Three levels of filtering — all optional, combinable.
# Translate directly to pytest primitives — no registry, no indirection.
#
#   FILE=     corpus file without .py extension → scopes to that file path
#             make test-bdd-gherkin FILE=test_bdd
#             make test-bdd-gherkin FILE=test_bdd_background
#             make test-bdd-gherkin FILE=test_bdd_edge_cases
#
#   FEATURE=  feature title from the .feature file → passed to pytest -k
#             make test-bdd-gherkin FEATURE="Shopping cart checkout"
#             make test-bdd-gherkin FEATURE="User authentication flows"
#
#   SCENARIO= scenario name from the .feature file → passed to pytest -k
#             make test-bdd-gherkin SCENARIO="Guest completes a purchase"
#             make test-bdd-gherkin SCENARIO="Discount code reduces the cart total"
#
#   FILE + SCENARIO can be combined to narrow scope:
#             make test-bdd-gherkin FILE=test_bdd SCENARIO="Guest completes a purchase"

BDD_TESTS := tests/corpus/bdd/


FILE     ?=
FEATURE  ?=
SCENARIO ?=

_BDD_PATH  := $(if $(FILE),tests/corpus/bdd/$(FILE).py,$(BDD_TESTS))
_BDD_KFLAG := $(if $(SCENARIO),-k "$(SCENARIO)",$(if $(FEATURE),-k "$(FEATURE)",))

# ── Primary targets ───────────────────────────────────────────────────────────

.PHONY: test test-fast test-corpus test-bdd test-bdd-steps test-bdd-gherkin \
				test-bdd-gherkin-vv test-bdd-json test-bdd-json-expanded \
				test-unit test-raw help

## test              Run suite with custom output.
##                   SUITE=, CASE=, K= for filtering.  ARGS= for raw pytest flags.
##                   Examples:
##                     make test
##                     make test SUITE=tests/test_entities.py
##                     make test CASE=test_return_statuses_dict
##                     make test K="sprint and not slow"
test:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(_PATH) $(_KFLAG) $(ARGS)

## test-fast         Stop on first failure (-x). Accepts same filters as `test`.
test-fast:
	@PYTHONPATH=. $(PYTEST) $(FMT) -x $(_PATH) $(_KFLAG) $(ARGS)

## test-corpus       Run the full corpus (tests/corpus/).
##                   Covers assertions, exceptions, skips, parametrize, capture,
##                   fixtures, warnings, and BDD scenarios.
##                   Intentional failures are expected and correct.
test-corpus:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/corpus/ $(ARGS)

## test-bdd          Run BDD corpus through glaze formatter (compact mode — default).
##                   FILE=, SCENARIO= for filtering.
##                   Use test-bdd-steps for full step-by-step output.
##                   Examples:
##                     make test-bdd
##                     make test-bdd FILE=test_bdd
##                     make test-bdd FEATURE="Shopping cart checkout"
##                     make test-bdd SCENARIO="Guest completes a purchase"
##                     make test-bdd FILE=test_bdd SCENARIO="Discount code reduces the cart total"
test-bdd:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)

## test-bdd-gherkin  BDD corpus with pytest-bdd's Gherkin terminal reporter (-v).
##                   Shows Feature/Scenario/step lines natively.
##                   FILE=, FEATURE=, SCENARIO= for filtering.
test-bdd-gherkin:
	@PYTHONPATH=. $(PYTEST) --gherkin-terminal-reporter -v $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)

## test-bdd-gherkin-vv  Same with full assertion diffs (-vv).
##                      FILE=, FEATURE=, SCENARIO= for filtering.
test-bdd-gherkin-vv:
	@PYTHONPATH=. $(PYTEST) --gherkin-terminal-reporter -vv $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)

## test-bdd-steps    Run BDD corpus with full step-by-step output (--bdd-steps flag).
##                   FILE=, SCENARIO= for filtering.
##                   Examples:
##                     make test-bdd-steps
##                     make test-bdd-steps FILE=test_checkout
##                     make test-bdd-steps FILE=test_checkout SCENARIO="Guest completes a purchase"
test-bdd-steps:
	@PYTHONPATH=. $(PYTEST) $(FMT) --bdd-steps $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)

## test-bdd-json     Cucumber JSON output → bdd-report.json
##                   FILE=, FEATURE=, SCENARIO= for filtering.
test-bdd-json:
	@PYTHONPATH=. $(PYTEST) --cucumber-json=bdd-report.json $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)
	@echo "Report written to bdd-report.json"

## test-bdd-json-expanded  Cucumber JSON with Outlines expanded → bdd-report-expanded.json
##                          FILE=, FEATURE=, SCENARIO= for filtering.
test-bdd-json-expanded:
	@PYTHONPATH=. $(PYTEST) --cucumber-json-expanded=bdd-report-expanded.json $(_BDD_PATH) $(_BDD_KFLAG) $(ARGS)
	@echo "Report written to bdd-report-expanded.json"

## test-unit         Run unit tests only (test_parsers, test_colorizer, test_plugin).
##                   No intentional failures — clean pass/fail signal.
test-unit:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/test_parsers.py tests/test_colorizer.py tests/test_plugin.py $(_KFLAG) $(ARGS)

## test-raw          Raw default pytest output. Useful for debugging the formatter.
##                   Accepts SUITE=, CASE=, K= for filtering.
test-raw:
	@$(PYTEST) $(_PATH) $(_KFLAG) $(ARGS)

## help              List all targets.
help:
	@grep -E '^##' Makefile | sed 's/^## /  /'
