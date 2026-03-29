"""Tests for registry payload validator helpers.

Protects _parse_str_list, _parse_positive_int, and _parse_optional_str — the
shared validation primitives that all registry runner wrappers delegate to.
These functions are the last line of defense before AI-generated JSON payloads
reach subprocess execution: they must reject type mismatches (bool is not int),
zero/negative numeric values, non-string list items, and whitespace-only strings,
while gracefully returning defaults for missing keys.  A regression here would
allow invalid payloads to propagate silently into commands with confusing effects.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools.registry import (
    _parse_optional_str,
    _parse_positive_int,
    _parse_str_list,
)


class TestParseStrList:
    def test_valid_list(self) -> None:
        assert _parse_str_list({"args": ["a", "b"]}, key="args") == ["a", "b"]

    def test_empty_list(self) -> None:
        assert _parse_str_list({"args": []}, key="args") == []

    def test_missing_key_returns_empty(self) -> None:
        assert _parse_str_list({}, key="args") == []

    def test_none_returns_empty(self) -> None:
        assert _parse_str_list({"args": None}, key="args") == []

    def test_rejects_non_list(self) -> None:
        with pytest.raises(ValueError, match="list of strings"):
            _parse_str_list({"args": "not-a-list"}, key="args")

    def test_rejects_non_string_items(self) -> None:
        with pytest.raises(ValueError, match="only strings"):
            _parse_str_list({"args": [1, 2]}, key="args")

    def test_rejects_empty_string_items(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            _parse_str_list({"args": ["valid", ""]}, key="args")

    def test_rejects_whitespace_only_items(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            _parse_str_list({"args": ["  ", "valid"]}, key="args")

    def test_strips_whitespace_from_items(self) -> None:
        assert _parse_str_list({"args": [" a ", " b "]}, key="args") == ["a", "b"]


class TestParsePositiveInt:
    def test_valid_int(self) -> None:
        assert _parse_positive_int({"n": 5}, key="n", default=1) == 5

    def test_uses_default_when_missing(self) -> None:
        assert _parse_positive_int({}, key="n", default=10) == 10

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            _parse_positive_int({"n": 0}, key="n", default=1)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            _parse_positive_int({"n": -5}, key="n", default=1)

    def test_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_positive_int({"n": True}, key="n", default=1)

    def test_rejects_string(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            _parse_positive_int({"n": "5"}, key="n", default=1)


class TestParseOptionalStr:
    def test_returns_value(self) -> None:
        assert _parse_optional_str({"k": "hello"}, key="k") == "hello"

    def test_returns_none_when_missing(self) -> None:
        assert _parse_optional_str({}, key="k") is None

    def test_returns_none_for_none(self) -> None:
        assert _parse_optional_str({"k": None}, key="k") is None

    def test_returns_none_for_empty_string(self) -> None:
        assert _parse_optional_str({"k": ""}, key="k") is None

    def test_strips_whitespace(self) -> None:
        assert _parse_optional_str({"k": "  hello  "}, key="k") == "hello"

    def test_whitespace_only_returns_none(self) -> None:
        assert _parse_optional_str({"k": "   "}, key="k") is None

    def test_rejects_non_string(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            _parse_optional_str({"k": 42}, key="k")
