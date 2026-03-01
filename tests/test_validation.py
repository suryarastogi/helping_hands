"""Tests for ``helping_hands.lib.validation`` helpers."""

import pytest

from helping_hands.lib.validation import (
    parse_optional_str,
    parse_positive_int,
    parse_str_list,
)

# --- parse_str_list ---


class TestParseStrList:
    def test_returns_list_of_strings(self) -> None:
        assert parse_str_list({"k": ["a", "b"]}, key="k") == ["a", "b"]

    def test_missing_key_returns_empty(self) -> None:
        assert parse_str_list({}, key="k") == []

    def test_none_value_returns_empty(self) -> None:
        assert parse_str_list({"k": None}, key="k") == []

    def test_rejects_non_list(self) -> None:
        with pytest.raises(ValueError, match="must be a list"):
            parse_str_list({"k": "not-a-list"}, key="k")

    def test_rejects_non_string_items(self) -> None:
        with pytest.raises(ValueError, match="must contain only strings"):
            parse_str_list({"k": ["ok", 123]}, key="k")

    def test_empty_list_returns_empty(self) -> None:
        assert parse_str_list({"k": []}, key="k") == []

    def test_rejects_dict_value(self) -> None:
        with pytest.raises(ValueError, match="must be a list"):
            parse_str_list({"k": {"a": 1}}, key="k")


# --- parse_positive_int ---


class TestParsePositiveInt:
    def test_returns_positive_int(self) -> None:
        assert parse_positive_int({"k": 5}, key="k", default=1) == 5

    def test_missing_key_returns_default(self) -> None:
        assert parse_positive_int({}, key="k", default=42) == 42

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            parse_positive_int({"k": 0}, key="k", default=1)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="must be > 0"):
            parse_positive_int({"k": -3}, key="k", default=1)

    def test_rejects_bool_true(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            parse_positive_int({"k": True}, key="k", default=1)

    def test_rejects_bool_false(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            parse_positive_int({"k": False}, key="k", default=1)

    def test_rejects_float(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            parse_positive_int({"k": 3.5}, key="k", default=1)

    def test_rejects_string(self) -> None:
        with pytest.raises(ValueError, match="must be an integer"):
            parse_positive_int({"k": "5"}, key="k", default=1)


# --- parse_optional_str ---


class TestParseOptionalStr:
    def test_returns_trimmed_string(self) -> None:
        assert parse_optional_str({"k": "  hello  "}, key="k") == "hello"

    def test_missing_key_returns_none(self) -> None:
        assert parse_optional_str({}, key="k") is None

    def test_none_value_returns_none(self) -> None:
        assert parse_optional_str({"k": None}, key="k") is None

    def test_blank_string_returns_none(self) -> None:
        assert parse_optional_str({"k": "   "}, key="k") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_optional_str({"k": ""}, key="k") is None

    def test_rejects_non_string(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            parse_optional_str({"k": 123}, key="k")

    def test_rejects_list_value(self) -> None:
        with pytest.raises(ValueError, match="must be a string"):
            parse_optional_str({"k": ["a"]}, key="k")
