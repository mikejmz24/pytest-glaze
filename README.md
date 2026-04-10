# pytest-glaze

> A thin, transparent coat that makes your test output shine.

pytest-glaze is a drop-in pytest output formatter that replaces the default
terminal reporter with a compact, color-semantic display. Failures surface
inline — no scrolling to a deferred block — and every color carries a
consistent meaning across every line type.

```
collected 57 tests

tests/test_assertions.py
  --- PASS  test_pass_int                                    0.2ms
  --- PASS  test_pass_string                                 0.2ms
  --- FAIL  test_fail_int_equality                           0.4ms
    E  assert 3 == 30
  --- FAIL  test_fail_none_check                             0.3ms
    E  assert None is not None
  --- FAIL  test_fail_dict                                   0.6ms
    E  AssertionError: assert {'a': 1, 'b': 2} == {'a': 1, 'b': 999}
    E  Differing items:
    E  {'b': 2} != {'b': 999}
  => 2 passed, 3 failed

Total: 2 passed, 3 failed  in 0.18s
```

---

## Why pytest-glaze?

The default pytest reporter is designed for completeness. pytest-glaze is
designed for **reading speed**. When you are deep in a debugging session, the
question is always the same: _what failed, and what exactly was wrong?_

|                               | Default reporter   | pytest-rich / pytest-pretty | **pytest-glaze** |
| ----------------------------- | ------------------ | --------------------------- | ---------------- |
| Failures inline               | ✗ (deferred block) | Partial                     | ✓                |
| Consistent color semantics    | ✗                  | Partial                     | ✓                |
| Zero extra dependencies       | ✓                  | ✗ (Rich)                    | ✓                |
| Compact — one line per result | ✗                  | ✗                           | ✓                |
| Per-file summaries            | ✗                  | ✗                           | ✓                |

**Color semantics** are applied uniformly across every line type:

| Color           | Meaning                                   | Examples                                                        |
| --------------- | ----------------------------------------- | --------------------------------------------------------------- |
| 🔴 Bright red   | Received / wrong value / expected failure | assert line left side, `Obtained:`, `+` diff lines, XFAIL badge |
| 🟢 Green        | Expected / target value                   | assert line right side, `Expected:`, `-` diff lines             |
| 🟡 Yellow       | Skipped / unexpected pass                 | SKIP badge, XPASS badge, skip reason                            |
| ⬜ Soft peach   | Context / prose                           | Exception messages, diff context, `E` prefix                    |
| 🔴 Standard red | Collection / setup errors                 | ERROR badge, collection error messages                          |
| 🔅 Dim          | Metadata                                  | Duration, collection count                                      |

---

## Installation

```bash
pip install pytest-glaze
```

pytest-glaze registers itself automatically via pytest's plugin system.
No configuration required — install and run.

### Requirements

- Python ≥ 3.10
- pytest ≥ 7.0

---

## Usage

### Automatic (recommended)

Once installed, pytest-glaze activates for every `pytest` invocation:

```bash
pytest tests/
```

### Makefile (strongly recommended)

For teams and projects with a Makefile-driven workflow, the following pattern
gives you precise control: glaze on by default, raw output available when you
need to debug the formatter itself.

```makefile
PYTHON := python
PYTEST := uv run pytest          # or: python -m pytest
TESTS  := tests/

# Core formatter flags
FMT := -p no:terminal -p pytest_glaze

# Optional filters
SUITE ?=
CASE  ?=
K     ?=
ARGS  ?=

_PATH  := $(if $(SUITE),$(SUITE),$(TESTS))
_KFLAG := $(if $(K),-k "$(K)",$(if $(CASE),-k "$(CASE)",))

.PHONY: test test-fast test-unit test-raw

## test        Run suite with glaze output.
##             SUITE=, CASE=, K= for filtering.
test:
	@PYTHONPATH=. $(PYTEST) $(FMT) $(_PATH) $(_KFLAG) $(ARGS)

## test-fast   Stop on first failure.
test-fast:
	@PYTHONPATH=. $(PYTEST) $(FMT) -x $(_PATH) $(_KFLAG) $(ARGS)

## test-unit   Unit tests only — clean pass/fail signal.
test-unit:
	@PYTHONPATH=. $(PYTEST) $(FMT) tests/test_parsers.py tests/test_colorizer.py tests/test_plugin.py

## test-raw    Default pytest output. Useful for debugging the formatter.
test-raw:
	@$(PYTEST) $(_PATH) $(_KFLAG) $(ARGS)
```

### Disabling per-invocation

If you need the default reporter for a single run:

```bash
pytest -p no:pytest_glaze tests/
```

---

## What it formats

### Passing tests

```
--- PASS  test_user_login                                  0.8ms
--- PASS  test_token_refresh                               1.2ms
```

### Failing assertions — inline, never deferred

```
--- FAIL  test_fail_int_equality                           0.4ms
  E  assert 3 == 30

--- FAIL  test_fail_string                                 0.6ms
  E  AssertionError: assert 'INTGPT-109' == 'INTGPT-1091'
  E  - INTGPT-1091
  E  + INTGPT-109

--- FAIL  test_fail_none_check                             0.3ms
  E  assert None is not None

--- FAIL  test_fail_bool                                   0.3ms
  E  AssertionError: this flag should be True
  E  assert False
```

### Dict and list diffs

```
--- FAIL  test_fail_dict                                   0.6ms
  E  AssertionError: assert {'a': 1, 'b': 2, 'c': 3} == {'a': 1, 'b': 999, 'd': 4}
  E  Differing items:
  E  {'b': 2} != {'b': 999}
  E  Left contains 1 more item:
  E  {'c': 3}
```

### Approximate equality (pytest.approx)

```
--- FAIL  test_fail_approx_abs                             0.2ms
  E  assert 3.141592653589793 == 3.14 ± 0.001
  E  comparison failed
  E  Obtained: 3.141592653589793
  E  Expected: 3.14 ± 0.001
```

### Skips, xfail, and xpass

```
--- SKIP   test_skip_platform_conditional                  0.2ms
  E  Skipped: Windows-only feature

--- XFAIL  test_xfail_expected_failure                     0.3ms
  E  xfailed: known bug — assert will fail as expected

--- XPASS  test_xpass_unexpected_pass                      0.2ms
  E  xpassed: this test unexpectedly passes
```

XFAIL renders in bright red — an expected failure is still a red signal
worth tracking. XPASS renders in yellow — an unexpected pass is a surprise
worth investigating, but not an error.

### Fixture errors

```
--- PASS   test_error_in_fixture_teardown                  0.2ms
--- ERROR  test_error_in_fixture_teardown                  0.3ms
  E  RuntimeError: Teardown exploded intentionally
```

### Captured output (shown only on failures)

```
--- FAIL  test_fail_with_stdout_and_stderr                 0.4ms
  E  AssertionError: intentional failure with stdout and stderr
  E  assert False
  ── Captured stdout call ──
  stdout payload for combined capture test
  ── Captured stderr call ──
  stderr payload for combined capture test
```

### Per-file summaries

```
tests/test_entities.py
  --- PASS  test_user_create                               0.3ms
  --- FAIL  test_user_update                               0.8ms
    E  assert 'inactive' == 'active'
  --- PASS  test_user_delete                               0.2ms
  => 2 passed, 1 failed

tests/test_auth.py
  --- PASS  test_login                                     0.4ms
  --- PASS  test_logout                                    0.3ms
  => 2 passed

Total: 4 passed, 1 failed  in 0.42s
```

---

## Noise suppression

pytest-glaze automatically suppresses lines that add no value in compact
output:

- `Omitting N identical items, use -vv to show`
- `Use -v to get more diff`
- `Full diff:`

These are filtered before rendering. The meaningful diff lines remain.

---

## Compatibility

pytest-glaze is a pure formatter. It has no opinion on how you write your
tests, which fixtures you use, or how you organize your suite. It works
alongside:

- `pytest-cov` — coverage reporting is unaffected
- `pytest-xdist` — parallel runs are supported
- `pytest-mock`, `pytest-asyncio`, and any other plugin that doesn't
  replace the terminal reporter

The one incompatibility: any other plugin that also replaces the terminal
reporter (e.g. `pytest-rich`) will conflict. Use one formatter at a time.

---

## Contributing

pytest-glaze is currently a personal project. Pull requests are welcome —
if you find a failure shape the formatter doesn't handle well, open an issue
with the raw pytest output and I'll take a look.

---

## License

MIT — see [LICENSE](LICENSE).

---

_pytest-glaze — because your test output deserves a coat of glaze._
