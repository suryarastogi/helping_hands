"""Tests for helping_hands.lib.validation."""

from __future__ import annotations

import pytest

from helping_hands.lib.validation import (
    parse_optional_str,
    parse_positive_int,
    parse_str_list,
)


class TestParseStrList:
    """Tests for parse_str_list."""

    def test_returns_list_of_strings(self) -> None:
        result = parse_str_list({"paths": ["a.py", "b.py"]}, key="paths")
        assert result == ["a.py", "b.py"]

    def test_missing_key_returns_empty_list(self) -> None:
        assert parse_str_list({}, key="paths") == []

    def test_none_value_returns_empty_list(self) -> None:
        assert parse_str_list({"paths": None}, key="paths") == []

    def test_empty_list_returns_empty_list(self) -> None:
        assert parse_str_list({"paths": []}, key="paths") == []

    def test_single_item_list(self) -> None:
        assert parse_str_list({"x": ["only"]}, key="x") == ["only"]

    def test_raises_on_non_list_value(self) -> None:
        with pytest.raises(ValueError, match="paths must be a list"):
            parse_str_list({"paths": "not-a-list"}, key="paths")

    def test_raises_on_int_value(self) -> None:
        with pytest.raises(ValueError, match="paths must be a list"):
            parse_str_list({"paths": 42}, key="paths")

    def test_raises_on_non_string_item(self) -> None:
        with pytest.raises(ValueError, match="paths must contain only strings"):
            parse_str_list({"paths": ["ok", 123]}, key="paths")

    def test_raises_on_bool_item(self) -> None:
        with pytest.raises(ValueError, match="paths must contain only strings"):
            parse_str_list({"paths": [True]}, key="paths")

    def test_raises_on_dict_value(self) -> None:
        with pytest.raises(ValueError, match="paths must be a list"):
            parse_str_list({"paths": {"a": 1}}, key="paths")

    def test_preserves_whitespace_in_items(self) -> None:
        result = parse_str_list({"x": [" spaced "]}, key="x")
        assert result == [" spaced "]


class TestParsePositiveInt:
    """Tests for parse_positive_int."""

    def test_returns_valid_positive_int(self) -> None:
        assert parse_positive_int({"n": 5}, key="n", default=1) == 5

    def test_uses_default_when_missing(self) -> None:
        assert parse_positive_int({}, key="n", default=10) == 10

    def test_raises_on_zero(self) -> None:
        with pytest.raises(ValueError, match="n must be > 0"):
            parse_positive_int({"n": 0}, key="n", default=1)

    def test_raises_on_negative(self) -> None:
        with pytest.raises(ValueError, match="n must be > 0"):
            parse_positive_int({"n": -3}, key="n", default=1)

    def test_raises_on_bool_true(self) -> None:
        with pytest.raises(ValueError, match="n must be an integer"):
            parse_positive_int({"n": True}, key="n", default=1)

    def test_raises_on_bool_false(self) -> None:
        with pytest.raises(ValueError, match="n must be an integer"):
            parse_positive_int({"n": False}, key="n", default=1)

    def test_raises_on_float(self) -> None:
        with pytest.raises(ValueError, match="n must be an integer"):
            parse_positive_int({"n": 3.14}, key="n", default=1)

    def test_raises_on_string(self) -> None:
        with pytest.raises(ValueError, match="n must be an integer"):
            parse_positive_int({"n": "5"}, key="n", default=1)

    def test_raises_on_none_value(self) -> None:
        with pytest.raises(ValueError, match="n must be an integer"):
            parse_positive_int({"n": None}, key="n", default=1)

    def test_large_positive_int(self) -> None:
        assert parse_positive_int({"n": 999999}, key="n", default=1) == 999999

    def test_one_is_valid(self) -> None:
        assert parse_positive_int({"n": 1}, key="n", default=10) == 1


class TestParseOptionalStr:
    """Tests for parse_optional_str."""

    def test_returns_trimmed_string(self) -> None:
        assert parse_optional_str({"q": "  hello  "}, key="q") == "hello"

    def test_missing_key_returns_none(self) -> None:
        assert parse_optional_str({}, key="q") is None

    def test_none_value_returns_none(self) -> None:
        assert parse_optional_str({"q": None}, key="q") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_optional_str({"q": ""}, key="q") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_optional_str({"q": "   "}, key="q") is None

    def test_raises_on_non_string_int(self) -> None:
        with pytest.raises(ValueError, match="q must be a string"):
            parse_optional_str({"q": 42}, key="q")

    def test_raises_on_non_string_list(self) -> None:
        with pytest.raises(ValueError, match="q must be a string"):
            parse_optional_str({"q": ["a"]}, key="q")

    def test_raises_on_bool(self) -> None:
        with pytest.raises(ValueError, match="q must be a string"):
            parse_optional_str({"q": True}, key="q")

    def test_preserves_internal_whitespace(self) -> None:
        assert parse_optional_str({"q": "a  b"}, key="q") == "a  b"

    def test_single_char_string(self) -> None:
        assert parse_optional_str({"q": "x"}, key="q") == "x"
