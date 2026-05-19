# tests/corpus

This directory contains **intentional failure fixtures** — test files designed
to produce specific outcomes (failures, errors, skips, xfails) so pytest-glaze
can render them correctly.

These are NOT broken tests. They are the ground truth for glaze's output rendering.

## Structure

| Directory     | Purpose                                                              |
| ------------- | -------------------------------------------------------------------- |
| `exceptions/` | Assertions, exceptions, skips, xfail, parametrize, capture, warnings |
| `bdd/`        | pytest-bdd scenarios covering all BDD rendering paths                |
| `acceptance/` | BDD acceptance tests that verify glaze's own rendering behavior      |

## Expected outcomes

When running `make test`, you will see intentional failures in the summary:

    Total: 495 passed, 85 failed, 4 errors, 7 skipped, 5 xfailed, 2 xpassed

The 85 failed, 4 errors, 7 skipped, 5 xfailed, 2 xpassed are all intentional
corpus fixtures — they exist to exercise glaze's rendering of each outcome type.

## Running clean tests only

To run only real tests with a clean pass/fail signal, use the mark taxonomy:

    make test-marks MARK=unit        # fast isolated unit tests
    make test-marks MARK=integration # multi-component wiring tests
    make test-marks MARK=acceptance  # BDD rendering acceptance tests
    make test-marks MARK=e2e         # pytester subprocess tests
    make test-marks MARK=security    # sanitization and hostile input tests
