"""Tests for v225: validation type guards and _normalize_args container check.

The require_* validators are called at every public API boundary. If they stop
raising TypeError for wrong-type arguments, callers receive cryptic AttributeError
or arithmetic errors deep inside hand logic instead of an immediate, descriptive
failure at the entry point.

The bool-rejection test for require_positive_int is non-obvious: in Python
bool is a subclass of int, so True/False would be silently accepted as 1/0
without an explicit isinstance check — 0 is not a valid iteration count.

_normalize_args must reject arbitrary containers (dict, set) and only accept
list or tuple, otherwise the CLI subprocess command builder receives a
non-sequence and fails at the os.execv layer.
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.meta.tools.command import _normalize_args
from helping_hands.lib.validation import require_non_empty_string, require_positive_int

# ---------------------------------------------------------------------------
# require_non_empty_string — type guard
# ---------------------------------------------------------------------------


class TestRequireNonEmptyStringTypeGuard:
    """Verify require_non_empty_string rejects non-string inputs with TypeError."""

    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="field must be a string, got NoneType"):
            require_non_empty_string(None, "field")  # type: ignore[arg-type]

    def test_int_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="x must be a string, got int"):
            require_non_empty_string(42, "x")  # type: ignore[arg-type]

    def test_bool_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="flag must be a string, got bool"):
            require_non_empty_string(True, "flag")  # type: ignore[arg-type]

    def test_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="items must be a string, got list"):
            require_non_empty_string(["a", "b"], "items")  # type: ignore[arg-type]

    def test_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="data must be a string, got dict"):
            require_non_empty_string({"k": "v"}, "data")  # type: ignore[arg-type]

    def test_float_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="val must be a string, got float"):
            require_non_empty_string(3.14, "val")  # type: ignore[arg-type]

    def test_bytes_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="raw must be a string, got bytes"):
            require_non_empty_string(b"hello", "raw")  # type: ignore[arg-type]

    def test_valid_string_still_works(self) -> None:
        assert require_non_empty_string("hello", "x") == "hello"

    def test_empty_string_still_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            require_non_empty_string("", "x")


# ---------------------------------------------------------------------------
# require_positive_int — type guard
# ---------------------------------------------------------------------------


class TestRequirePositiveIntTypeGuard:
    """Verify require_positive_int rejects non-int and bool inputs with TypeError."""

    def test_bool_true_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="flag must be an int, got bool"):
            require_positive_int(True, "flag")  # type: ignore[arg-type]

    def test_bool_false_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="flag must be an int, got bool"):
            require_positive_int(False, "flag")  # type: ignore[arg-type]

    def test_string_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="count must be an int, got str"):
            require_positive_int("5", "count")  # type: ignore[arg-type]

    def test_float_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="n must be an int, got float"):
            require_positive_int(3.5, "n")  # type: ignore[arg-type]

    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got NoneType"):
            require_positive_int(None, "x")  # type: ignore[arg-type]

    def test_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="vals must be an int, got list"):
            require_positive_int([1], "vals")  # type: ignore[arg-type]

    def test_valid_int_still_works(self) -> None:
        assert require_positive_int(5, "x") == 5

    def test_zero_still_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            require_positive_int(0, "x")


# ---------------------------------------------------------------------------
# _normalize_args — container type guard
# ---------------------------------------------------------------------------


class TestNormalizeArgsContainerGuard:
    """Verify _normalize_args rejects non-list/tuple containers."""

    def test_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="args must be a list or tuple, got dict"):
            _normalize_args({"a": 1, "b": 2})  # type: ignore[arg-type]

    def test_set_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="args must be a list or tuple, got set"):
            _normalize_args({"a", "b"})  # type: ignore[arg-type]

    def test_string_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="args must be a list or tuple, got str"):
            _normalize_args("hello")  # type: ignore[arg-type]

    def test_int_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="args must be a list or tuple, got int"):
            _normalize_args(42)  # type: ignore[arg-type]

    def test_generator_raises_type_error(self) -> None:
        gen = (x for x in ["a", "b"])
        with pytest.raises(
            TypeError, match="args must be a list or tuple, got generator"
        ):
            _normalize_args(gen)  # type: ignore[arg-type]

    def test_none_returns_empty(self) -> None:
        assert _normalize_args(None) == []

    def test_empty_list_returns_empty(self) -> None:
        assert _normalize_args([]) == []

    def test_empty_tuple_returns_empty(self) -> None:
        assert _normalize_args(()) == []

    def test_valid_list_still_works(self) -> None:
        assert _normalize_args(["a", "b"]) == ["a", "b"]

    def test_valid_tuple_still_works(self) -> None:
        assert _normalize_args(("a", "b")) == ["a", "b"]

    def test_non_string_element_still_raises(self) -> None:
        with pytest.raises(TypeError, match="args must contain only strings"):
            _normalize_args([1, 2])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Source consistency: web.py uses require_non_empty_string
# ---------------------------------------------------------------------------


class TestWebUsesRequireNonEmptyString:
    """Verify search_web and _require_http_url delegate to require_non_empty_string."""

    @staticmethod
    def _web_source(func_name: str) -> str:
        import helping_hands.lib.meta.tools.web as mod

        return inspect.getsource(getattr(mod, func_name))

    def test_search_web_uses_require_non_empty_string(self) -> None:
        src = self._web_source("search_web")
        assert "require_non_empty_string" in src

    def test_require_http_url_uses_require_non_empty_string(self) -> None:
        src = self._web_source("_require_http_url")
        assert "require_non_empty_string" in src

    def test_search_web_no_inline_strip_check(self) -> None:
        """search_web should not have its own 'query must be non-empty' check."""
        src = self._web_source("search_web")
        assert "query must be non-empty" not in src

    def test_require_http_url_no_inline_strip_check(self) -> None:
        """_require_http_url should not have its own 'url must be non-empty' check."""
        src = self._web_source("_require_http_url")
        assert "url must be non-empty" not in src


# ---------------------------------------------------------------------------
# Source consistency: validation.py type guards present
# ---------------------------------------------------------------------------


class TestValidationSourceConsistency:
    """Verify validation helpers include isinstance type guards."""

    @staticmethod
    def _validation_source(func_name: str) -> str:
        import helping_hands.lib.validation as mod

        return inspect.getsource(getattr(mod, func_name))

    def test_require_non_empty_string_has_isinstance_check(self) -> None:
        src = self._validation_source("require_non_empty_string")
        assert "isinstance(value, str)" in src

    def test_require_positive_int_has_isinstance_check(self) -> None:
        src = self._validation_source("require_positive_int")
        assert "isinstance(value, int)" in src

    def test_require_positive_int_rejects_bool(self) -> None:
        src = self._validation_source("require_positive_int")
        assert "isinstance(value, bool)" in src


# ---------------------------------------------------------------------------
# _normalize_args source consistency
# ---------------------------------------------------------------------------


class TestNormalizeArgsSourceConsistency:
    """Verify _normalize_args has container type guard in source."""

    def test_has_isinstance_list_tuple_check(self) -> None:
        src = inspect.getsource(_normalize_args)
        assert "isinstance(args, (list, tuple))" in src
