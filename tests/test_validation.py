"""Dedicated unit tests for helping_hands.lib.validation.

Covers all branches of require_non_empty_string and require_positive_int,
including edge cases and return-value semantics.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.validation import (
    __all__ as validation_all,
)
from helping_hands.lib.validation import (
    require_non_empty_string,
    require_positive_int,
)

# ---------------------------------------------------------------------------
# Module __all__
# ---------------------------------------------------------------------------


class TestModuleAll:
    """Ensure public API surface is explicit."""

    def test_all_contains_expected_names(self) -> None:
        assert set(validation_all) == {
            "require_non_empty_string",
            "require_positive_int",
        }


# ---------------------------------------------------------------------------
# require_non_empty_string
# ---------------------------------------------------------------------------


class TestRequireNonEmptyString:
    """Tests for require_non_empty_string()."""

    def test_returns_stripped_value(self) -> None:
        assert require_non_empty_string("  hello  ", "x") == "hello"

    def test_plain_string_unchanged(self) -> None:
        assert require_non_empty_string("hello", "x") == "hello"

    def test_single_char(self) -> None:
        assert require_non_empty_string("a", "x") == "a"

    def test_leading_whitespace_stripped(self) -> None:
        assert require_non_empty_string("  hi", "x") == "hi"

    def test_trailing_whitespace_stripped(self) -> None:
        assert require_non_empty_string("hi  ", "x") == "hi"

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="field must not be empty"):
            require_non_empty_string("", "field")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            require_non_empty_string("   ", "name")

    def test_rejects_tab_only(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            require_non_empty_string("\t", "param")

    def test_rejects_newline_only(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            require_non_empty_string("\n", "val")

    def test_rejects_mixed_whitespace(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            require_non_empty_string(" \t\n\r ", "arg")

    def test_error_message_includes_param_name(self) -> None:
        with pytest.raises(ValueError, match="my_param must not be empty"):
            require_non_empty_string("", "my_param")

    def test_unicode_string(self) -> None:
        assert require_non_empty_string("  caf\u00e9  ", "x") == "caf\u00e9"

    def test_multiline_string(self) -> None:
        result = require_non_empty_string("  line1\nline2  ", "x")
        assert result == "line1\nline2"


# ---------------------------------------------------------------------------
# require_positive_int
# ---------------------------------------------------------------------------


class TestRequirePositiveInt:
    """Tests for require_positive_int()."""

    def test_positive_returns_value(self) -> None:
        assert require_positive_int(1, "x") == 1

    def test_large_positive(self) -> None:
        assert require_positive_int(999999, "x") == 999999

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="count must be positive, got 0"):
            require_positive_int(0, "count")

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="limit must be positive, got -1"):
            require_positive_int(-1, "limit")

    def test_rejects_large_negative(self) -> None:
        with pytest.raises(ValueError, match="n must be positive, got -100"):
            require_positive_int(-100, "n")

    def test_error_message_includes_value(self) -> None:
        with pytest.raises(ValueError, match="got -42"):
            require_positive_int(-42, "retries")

    def test_error_message_includes_param_name(self) -> None:
        with pytest.raises(ValueError, match="max_retries must be positive"):
            require_positive_int(-1, "max_retries")
