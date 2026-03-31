"""Guard payload parsing delegation between iterative.py and registry.py, and URL error handling.

_parse_str_list, _parse_positive_int, and _parse_optional_str were previously
duplicated in both iterative.py and registry.py. These tests assert identity (is)
rather than equality, ensuring iterative.py uses the exact same function objects
from registry.py. If a future refactor re-introduces a local copy, the two parsers
could silently diverge for edge cases (e.g., handling of None vs missing key).
_normalize_and_deduplicate tests protect the tool selection normalisation
that feeds the AI's tool-use context: if deduplication is lost, the AI context
could receive duplicate tool descriptions. _raise_url_error tests ensure HTTP and
network errors produce consistent, contextual error messages for users.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand
from helping_hands.lib.meta.tools.registry import (
    _normalize_and_deduplicate,
    _parse_optional_str,
    _parse_positive_int,
    _parse_str_list,
)
from helping_hands.lib.meta.tools.web import _raise_url_error

# ---------------------------------------------------------------------------
# 1. iterative.py payload validators delegate to registry.py
# ---------------------------------------------------------------------------


class TestIterativePayloadDelegation:
    """Verify iterative.py _parse_* methods delegate to registry.py."""

    def test_parse_str_list_is_same_function(self) -> None:
        assert _BasicIterativeHand._parse_str_list is _parse_str_list

    def test_parse_positive_int_is_same_function(self) -> None:
        assert _BasicIterativeHand._parse_positive_int is _parse_positive_int

    def test_parse_optional_str_is_same_function(self) -> None:
        assert _BasicIterativeHand._parse_optional_str is _parse_optional_str

    def test_parse_str_list_still_callable_on_class(self) -> None:
        result = _BasicIterativeHand._parse_str_list({"args": ["a", "b"]}, key="args")
        assert result == ["a", "b"]

    def test_parse_positive_int_still_callable_on_class(self) -> None:
        result = _BasicIterativeHand._parse_positive_int({"n": 5}, key="n", default=1)
        assert result == 5

    def test_parse_optional_str_still_callable_on_class(self) -> None:
        result = _BasicIterativeHand._parse_optional_str({"k": "hello"}, key="k")
        assert result == "hello"


# ---------------------------------------------------------------------------
# 2. _normalize_and_deduplicate shared helper
# ---------------------------------------------------------------------------


class TestNormalizeAndDeduplicate:
    """Verify the shared normalization/deduplication helper."""

    def test_none_returns_empty(self) -> None:
        assert _normalize_and_deduplicate(None, label="items") == ()

    def test_string_split_on_comma(self) -> None:
        result = _normalize_and_deduplicate("a,b,c", label="items")
        assert result == ("a", "b", "c")

    def test_list_input(self) -> None:
        result = _normalize_and_deduplicate(["a", "b"], label="items")
        assert result == ("a", "b")

    def test_tuple_input(self) -> None:
        result = _normalize_and_deduplicate(("a", "b"), label="items")
        assert result == ("a", "b")

    def test_deduplication_preserves_order(self) -> None:
        result = _normalize_and_deduplicate("b,a,b,a", label="items")
        assert result == ("b", "a")

    def test_lowercases_and_replaces_underscores(self) -> None:
        result = _normalize_and_deduplicate("My_Tool", label="items")
        assert result == ("my-tool",)

    def test_strips_whitespace(self) -> None:
        result = _normalize_and_deduplicate("  a , b  ", label="items")
        assert result == ("a", "b")

    def test_skips_empty_tokens(self) -> None:
        result = _normalize_and_deduplicate(",a,,b,", label="items")
        assert result == ("a", "b")

    def test_rejects_non_string_list_tuple_none(self) -> None:
        with pytest.raises(TypeError, match="items must be a string, list, or tuple"):
            _normalize_and_deduplicate(42, label="items")  # type: ignore[arg-type]

    def test_rejects_dict(self) -> None:
        with pytest.raises(TypeError, match="items must be a string, list, or tuple"):
            _normalize_and_deduplicate({"a": 1}, label="items")  # type: ignore[arg-type]

    def test_rejects_non_string_elements(self) -> None:
        with pytest.raises(ValueError, match="items must contain only strings"):
            _normalize_and_deduplicate([1, 2], label="items")  # type: ignore[list-item]

    def test_label_appears_in_error_messages(self) -> None:
        with pytest.raises(TypeError, match="tools must be"):
            _normalize_and_deduplicate(42, label="tools")  # type: ignore[arg-type]

    def test_tool_selection_uses_shared_helper(self) -> None:
        from helping_hands.lib.meta.tools.registry import normalize_tool_selection

        source = inspect.getsource(normalize_tool_selection)
        assert "_normalize_and_deduplicate" in source

    def test_in_registry_all(self) -> None:
        from helping_hands.lib.meta.tools.registry import __all__

        assert "_normalize_and_deduplicate" in __all__

    def test_has_docstring(self) -> None:
        doc = inspect.getdoc(_normalize_and_deduplicate)
        assert doc
        for section in ("Args:", "Returns:", "Raises:"):
            assert section in doc, f"Missing '{section}' in docstring"


# ---------------------------------------------------------------------------
# 3. _raise_url_error shared helper
# ---------------------------------------------------------------------------


class TestRaiseUrlError:
    """Verify the shared URL error handler."""

    def test_http_error_raises_runtime_error(self) -> None:
        exc = HTTPError(
            url="http://example.com",
            code=404,
            msg="Not Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError, match="search request failed with HTTP 404"):
            _raise_url_error(exc, operation="search")

    def test_url_error_raises_runtime_error(self) -> None:
        exc = URLError(reason="connection refused")
        with pytest.raises(
            RuntimeError, match="browse request failed: connection refused"
        ):
            _raise_url_error(exc, operation="browse")

    def test_http_error_includes_reason(self) -> None:
        exc = HTTPError(
            url="http://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(
            RuntimeError,
            match="test request failed with HTTP 500: Internal Server Error",
        ):
            _raise_url_error(exc, operation="test")

    def test_url_error_includes_reason(self) -> None:
        exc = URLError(reason="DNS resolution failed")
        with pytest.raises(
            RuntimeError, match="test request failed: DNS resolution failed"
        ):
            _raise_url_error(exc, operation="test")

    def test_http_error_chains_original(self) -> None:
        original = HTTPError(
            url="http://example.com",
            code=403,
            msg="Forbidden",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError) as exc_info:
            _raise_url_error(original, operation="search")
        assert exc_info.value.__cause__ is original

    def test_url_error_chains_original(self) -> None:
        original = URLError(reason="timeout")
        with pytest.raises(RuntimeError) as exc_info:
            _raise_url_error(original, operation="browse")
        assert exc_info.value.__cause__ is original

    @patch("helping_hands.lib.meta.tools.web.logger")
    def test_http_error_logs_debug(self, mock_logger) -> None:
        exc = HTTPError(
            url="http://example.com",
            code=404,
            msg="Not Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError):
            _raise_url_error(exc, operation="search")
        mock_logger.debug.assert_called_once()
        # Operation name is passed as a format arg, not in the template
        assert "search" in mock_logger.debug.call_args[0][1]

    @patch("helping_hands.lib.meta.tools.web.logger")
    def test_url_error_logs_debug(self, mock_logger) -> None:
        exc = URLError(reason="timeout")
        with pytest.raises(RuntimeError):
            _raise_url_error(exc, operation="browse")
        mock_logger.debug.assert_called_once()
        assert "browse" in mock_logger.debug.call_args[0][1]

    def test_has_docstring(self) -> None:
        doc = inspect.getdoc(_raise_url_error)
        assert doc
        for section in ("Args:", "Raises:"):
            assert section in doc, f"Missing '{section}' in docstring"
