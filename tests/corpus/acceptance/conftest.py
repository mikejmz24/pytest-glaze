import pytest
import pytest_glaze._colors as _colors_module

@pytest.fixture(autouse=True)
def force_colors():
    """Force ANSI color output regardless of TTY detection."""
    original = _colors_module._NO_COLOR
    _colors_module._NO_COLOR = False
    # Rebuild color functions that closed over _NO_COLOR
    import pytest_glaze._colors as c
    c._NO_COLOR = False
    yield
    _colors_module._NO_COLOR = original
