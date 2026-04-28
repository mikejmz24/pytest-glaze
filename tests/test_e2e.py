# ── Plugin activation ─────────────────────────────────────────────────────────

def test_glaze_flag_activates_formatter(pytester):
    """--glaze flag must activate the formatter and suppress default output."""
    pytester.makepyfile("""
        def test_pass():
            assert 1 == 1
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*PASS*test_pass*"])
    assert "passed" in result.stdout.str()


def test_without_glaze_uses_default_output(pytester):
    """Without --glaze the default pytest output must be used."""
    pytester.makepyfile("""
        def test_pass():
            assert 1 == 1
    """)
    result = pytester.runpytest()
    assert "PASS" not in result.stdout.str()
    assert "passed" in result.stdout.str()


# ── Pass / Fail / Skip / Error ────────────────────────────────────────────────

def test_passing_test_shows_pass_badge(pytester):
    pytester.makepyfile("""
        def test_something():
            assert True
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*PASS*test_something*"])


def test_failing_test_shows_fail_badge_and_inline_error(pytester):
    pytester.makepyfile("""
        def test_bad():
            assert 3 == 30
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*FAIL*test_bad*"])
    result.stdout.fnmatch_lines(["*assert*3*==*30*"])


def test_skipped_test_shows_skip_badge(pytester):
    pytester.makepyfile("""
        import pytest
        @pytest.mark.skip(reason="not today")
        def test_skip():
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*SKIP*test_skip*"])
    assert "not today" in result.stdout.str()


def test_error_in_setup_shows_error_badge(pytester):
    pytester.makepyfile("""
        import pytest
        @pytest.fixture
        def broken():
            raise RuntimeError("setup exploded")
        def test_with_broken(broken):
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    result.stdout.fnmatch_lines(["*ERROR*test_with_broken*"])
    assert "setup exploded" in result.stdout.str()


# ── Session summary ───────────────────────────────────────────────────────────

def test_total_line_appears_at_end(pytester):
    pytester.makepyfile("""
        def test_a(): pass
        def test_b(): assert False
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "Total:" in result.stdout.str()
    assert "1 passed" in result.stdout.str()
    assert "1 failed" in result.stdout.str()


def test_per_file_summary_appears(pytester):
    pytester.makepyfile("""
        def test_a(): pass
        def test_b(): pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "=>" in result.stdout.str()
    assert "2 passed" in result.stdout.str()


# ── Collection errors ─────────────────────────────────────────────────────────

def test_collection_error_surfaced(pytester):
    pytester.makepyfile("""
        import nonexistent_module_xyz
        def test_something(): pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    assert "COLLECTION ERRORS" in result.stdout.str()


# ── Terminal safety ───────────────────────────────────────────────────────────

def test_ansi_injection_in_test_name_does_not_corrupt_output(pytester):
    """A test name containing ANSI escape sequences must not corrupt output."""
    pytester.makepyfile(r"""
        def test_normal():
            pass
    """)
    result = pytester.runpytest("--glaze", "-p", "no:terminal")
    # Output must contain readable content — not garbled by control sequences
    assert "PASS" in result.stdout.str()
    assert "Total:" in result.stdout.str()
