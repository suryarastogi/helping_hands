"""Guard require_non_empty_string and require_positive_int as the shared validation layer.

These helpers in lib/validation.py are the single point of input validation for
path parameters, schedule fields, and config values across the server and CLI.
If require_non_empty_string stops stripping before checking, whitespace-only values
would pass through and reach database/Redis operations as keys. If require_positive_int
accepts zero or negative values, iteration counts and timeouts would silently produce
invalid states. The __all__ test ensures both helpers remain importable from the
validation module's public namespace — a removal would cause ImportError in any
code that does `from helping_hands.lib.validation import require_non_empty_string`.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.validation import require_non_empty_string, require_positive_int

# ---------------------------------------------------------------------------
# require_non_empty_string
# ---------------------------------------------------------------------------


class TestRequireNonEmptyString:
    """Tests for require_non_empty_string()."""

    def test_valid_string_returned_stripped(self) -> None:
        assert require_non_empty_string("  hello  ", "x") == "hello"

    def test_plain_string(self) -> None:
        assert require_non_empty_string("hello", "x") == "hello"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="x must not be empty"):
            require_non_empty_string("", "x")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            require_non_empty_string("   ", "name")

    def test_rejects_tab_only(self) -> None:
        with pytest.raises(ValueError, match="field must not be empty"):
            require_non_empty_string("\t", "field")

    def test_rejects_newline_only(self) -> None:
        with pytest.raises(ValueError, match="val must not be empty"):
            require_non_empty_string("\n", "val")

    def test_rejects_mixed_whitespace(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            require_non_empty_string(" \t\n ", "param")

    def test_name_appears_in_error(self) -> None:
        with pytest.raises(ValueError, match="my_param"):
            require_non_empty_string("", "my_param")

    def test_single_char(self) -> None:
        assert require_non_empty_string("a", "x") == "a"

    def test_module_all(self) -> None:
        from helping_hands.lib import validation

        assert "require_non_empty_string" in validation.__all__


# ---------------------------------------------------------------------------
# require_positive_int
# ---------------------------------------------------------------------------


class TestRequirePositiveInt:
    """Tests for require_positive_int()."""

    def test_positive_value_returned(self) -> None:
        assert require_positive_int(1, "x") == 1

    def test_large_positive(self) -> None:
        assert require_positive_int(999_999, "big") == 999_999

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="x must be positive, got 0"):
            require_positive_int(0, "x")

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="n must be positive, got -5"):
            require_positive_int(-5, "n")

    def test_name_and_value_in_error(self) -> None:
        with pytest.raises(ValueError, match=r"timeout.*-1"):
            require_positive_int(-1, "timeout")

    def test_module_all(self) -> None:
        from helping_hands.lib import validation

        assert "require_positive_int" in validation.__all__


_has_fastapi = True
try:
    import fastapi as _fastapi  # noqa: F401
except ModuleNotFoundError:
    _has_fastapi = False

_skip_no_fastapi = pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")


@_skip_no_fastapi
class TestDelegationAppValidatePathParam:
    """Verify app.py _validate_path_param delegates to shared validator."""

    def test_returns_stripped(self) -> None:
        from helping_hands.server.app import _validate_path_param

        assert _validate_path_param("  abc-123  ", "task_id") == "abc-123"

    def test_rejects_empty(self) -> None:
        from helping_hands.server.app import _validate_path_param

        with pytest.raises(ValueError):
            _validate_path_param("", "task_id")

    def test_rejects_whitespace(self) -> None:
        from helping_hands.server.app import _validate_path_param

        with pytest.raises(ValueError):
            _validate_path_param("   ", "schedule_id")
