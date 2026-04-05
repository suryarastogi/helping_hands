"""Dedicated unit tests for helping_hands.lib.validation.

Protects the shared validation primitives used throughout the library to guard
API boundaries: require_non_empty_string (strips whitespace and raises with the
parameter name in the message), require_positive_int and require_positive_float
(reject zero, negatives, NaN, and infinity with clear messages), and
parse_comma_list (used to normalise env-var lists for tools/repos).
These helpers are called in Config.from_env, GitHubClient methods, and server
endpoints; silent regressions would allow empty branch names, zero depths, or
NaN timeouts to reach git and AI provider calls.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.validation import (
    __all__ as validation_all,
    format_type_error,
    has_cli_flag,
    install_hint,
    parse_comma_list,
    require_non_empty_string,
    require_positive_float,
    require_positive_int,
    validate_repo_value,
)

# ---------------------------------------------------------------------------
# Module __all__
# ---------------------------------------------------------------------------


class TestModuleAll:
    """Ensure public API surface is explicit."""

    def test_all_contains_expected_names(self) -> None:
        assert set(validation_all) == {
            "format_type_error",
            "has_cli_flag",
            "install_hint",
            "parse_comma_list",
            "require_non_empty_string",
            "require_positive_float",
            "require_positive_int",
            "validate_repo_value",
        }


# ---------------------------------------------------------------------------
# has_cli_flag
# ---------------------------------------------------------------------------


class TestHasCliFlag:
    """Tests for has_cli_flag()."""

    def test_bare_flag_present(self) -> None:
        assert has_cli_flag(["--model", "gpt-4"], "model") is True

    def test_flag_with_equals(self) -> None:
        assert has_cli_flag(["--model=gpt-4"], "model") is True

    def test_flag_absent(self) -> None:
        assert has_cli_flag(["--verbose", "--dry-run"], "model") is False

    def test_empty_tokens(self) -> None:
        assert has_cli_flag([], "model") is False

    def test_partial_match_not_matched(self) -> None:
        assert has_cli_flag(["--model-name=foo"], "model") is False

    def test_single_dash_not_matched(self) -> None:
        assert has_cli_flag(["-model"], "model") is False

    def test_flag_among_many(self) -> None:
        tokens = ["--verbose", "--backend=langgraph", "--model", "gpt-4"]
        assert has_cli_flag(tokens, "backend") is True


# ---------------------------------------------------------------------------
# install_hint
# ---------------------------------------------------------------------------


class TestInstallHint:
    """Tests for install_hint()."""

    def test_server_extra(self) -> None:
        assert install_hint("server") == "Install with: uv sync --extra server"

    def test_langchain_extra(self) -> None:
        assert install_hint("langchain") == "Install with: uv sync --extra langchain"

    def test_contains_extra_name(self) -> None:
        result = install_hint("atomic")
        assert "atomic" in result
        assert "uv sync" in result


# ---------------------------------------------------------------------------
# format_type_error
# ---------------------------------------------------------------------------


class TestFormatTypeError:
    """Direct unit tests for format_type_error()."""

    def test_includes_param_name(self) -> None:
        msg = format_type_error("my_param", "a string", 42)
        assert "my_param" in msg

    def test_includes_expected_type(self) -> None:
        msg = format_type_error("x", "a string", 42)
        assert "a string" in msg

    def test_includes_actual_type(self) -> None:
        msg = format_type_error("x", "a string", 42)
        assert "int" in msg

    def test_format_with_none(self) -> None:
        assert format_type_error("x", "a string", None) == (
            "x must be a string, got NoneType"
        )

    def test_format_with_dict(self) -> None:
        assert format_type_error("cfg", "a list", {}) == (
            "cfg must be a list, got dict"
        )

    def test_format_with_custom_class(self) -> None:
        class Widget:
            pass

        msg = format_type_error("item", "a string", Widget())
        assert msg == "item must be a string, got Widget"


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

    def test_rejects_int(self) -> None:
        with pytest.raises(TypeError, match="field must be a string, got int"):
            require_non_empty_string(42, "field")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="field must be a string, got NoneType"):
            require_non_empty_string(None, "field")  # type: ignore[arg-type]

    def test_rejects_bool(self) -> None:
        with pytest.raises(TypeError, match="flag must be a string, got bool"):
            require_non_empty_string(True, "flag")  # type: ignore[arg-type]

    def test_rejects_list(self) -> None:
        with pytest.raises(TypeError, match="items must be a string, got list"):
            require_non_empty_string(["a"], "items")  # type: ignore[arg-type]


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

    def test_rejects_bool_true(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got bool"):
            require_positive_int(True, "x")  # type: ignore[arg-type]

    def test_rejects_bool_false(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got bool"):
            require_positive_int(False, "x")  # type: ignore[arg-type]

    def test_rejects_float(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got float"):
            require_positive_int(1.5, "x")  # type: ignore[arg-type]

    def test_rejects_string(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got str"):
            require_positive_int("5", "x")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="x must be an int, got NoneType"):
            require_positive_int(None, "x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# require_positive_float
# ---------------------------------------------------------------------------


class TestRequirePositiveFloat:
    """Tests for require_positive_float()."""

    def test_positive_float_returns_float(self) -> None:
        assert require_positive_float(1.5, "x") == 1.5
        assert isinstance(require_positive_float(1.5, "x"), float)

    def test_positive_int_coerced_to_float(self) -> None:
        result = require_positive_float(3, "x")
        assert result == 3.0
        assert isinstance(result, float)

    def test_small_positive_float(self) -> None:
        assert require_positive_float(0.001, "x") == 0.001

    def test_large_positive_float(self) -> None:
        assert require_positive_float(1e10, "x") == 1e10

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="timeout must be positive, got 0"):
            require_positive_float(0, "timeout")

    def test_rejects_zero_float(self) -> None:
        with pytest.raises(ValueError, match=r"timeout must be positive, got 0\.0"):
            require_positive_float(0.0, "timeout")

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match=r"delay must be positive, got -1\.5"):
            require_positive_float(-1.5, "delay")

    def test_rejects_negative_int(self) -> None:
        with pytest.raises(ValueError, match="n must be positive, got -1"):
            require_positive_float(-1, "n")

    def test_rejects_nan(self) -> None:
        with pytest.raises(ValueError, match="val must be finite"):
            require_positive_float(float("nan"), "val")

    def test_rejects_positive_infinity(self) -> None:
        with pytest.raises(ValueError, match="limit must be finite"):
            require_positive_float(float("inf"), "limit")

    def test_rejects_negative_infinity(self) -> None:
        with pytest.raises(ValueError, match="limit must be finite"):
            require_positive_float(float("-inf"), "limit")

    def test_rejects_bool_true(self) -> None:
        with pytest.raises(TypeError, match="x must be a number, got bool"):
            require_positive_float(True, "x")  # type: ignore[arg-type]

    def test_rejects_bool_false(self) -> None:
        with pytest.raises(TypeError, match="x must be a number, got bool"):
            require_positive_float(False, "x")  # type: ignore[arg-type]

    def test_rejects_string(self) -> None:
        with pytest.raises(TypeError, match="x must be a number, got str"):
            require_positive_float("1.5", "x")  # type: ignore[arg-type]

    def test_rejects_none(self) -> None:
        with pytest.raises(TypeError, match="x must be a number, got NoneType"):
            require_positive_float(None, "x")  # type: ignore[arg-type]

    def test_error_message_includes_param_name(self) -> None:
        with pytest.raises(ValueError, match="my_timeout must be positive"):
            require_positive_float(-0.5, "my_timeout")


# ---------------------------------------------------------------------------
# parse_comma_list
# ---------------------------------------------------------------------------


class TestParseCommaList:
    """Tests for parse_comma_list()."""

    def test_empty_string(self) -> None:
        assert parse_comma_list("") == ()

    def test_whitespace_only(self) -> None:
        assert parse_comma_list("   ") == ()

    def test_single_item(self) -> None:
        assert parse_comma_list("foo") == ("foo",)

    def test_single_item_with_whitespace(self) -> None:
        assert parse_comma_list("  foo  ") == ("foo",)

    def test_multiple_items(self) -> None:
        assert parse_comma_list("a, b, c") == ("a", "b", "c")

    def test_strips_whitespace(self) -> None:
        assert parse_comma_list("  x , y , z  ") == ("x", "y", "z")

    def test_trailing_comma(self) -> None:
        assert parse_comma_list("a, b,") == ("a", "b")

    def test_leading_comma(self) -> None:
        assert parse_comma_list(",a, b") == ("a", "b")

    def test_consecutive_commas(self) -> None:
        assert parse_comma_list("a,,b") == ("a", "b")

    def test_only_commas(self) -> None:
        assert parse_comma_list(",,,") == ()

    def test_returns_tuple(self) -> None:
        result = parse_comma_list("a,b")
        assert isinstance(result, tuple)

    def test_preserves_order(self) -> None:
        assert parse_comma_list("c,a,b") == ("c", "a", "b")

    def test_repo_style_input(self) -> None:
        """Matches the reference_repos use case."""
        assert parse_comma_list("owner/repo1, owner/repo2") == (
            "owner/repo1",
            "owner/repo2",
        )


# ---------------------------------------------------------------------------
# validate_repo_value
# ---------------------------------------------------------------------------


class TestValidateRepoValue:
    """Tests for validate_repo_value()."""

    def test_valid_local_path(self) -> None:
        assert validate_repo_value("/tmp/my-repo") == "/tmp/my-repo"

    def test_valid_owner_repo(self) -> None:
        assert validate_repo_value("owner/repo") == "owner/repo"

    def test_strips_whitespace(self) -> None:
        assert validate_repo_value("  owner/repo  ") == "owner/repo"

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_repo_value("")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_repo_value("   ")

    def test_null_byte_rejected(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            validate_repo_value("owner/repo\x00")

    def test_newline_rejected(self) -> None:
        with pytest.raises(ValueError, match="newlines"):
            validate_repo_value("owner/repo\nmalicious")

    def test_carriage_return_rejected(self) -> None:
        with pytest.raises(ValueError, match="newlines"):
            validate_repo_value("owner/repo\rmalicious")

    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            validate_repo_value("../../etc/passwd")

    def test_path_traversal_middle_rejected(self) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            validate_repo_value("/tmp/../etc/passwd")

    def test_backslash_traversal_rejected(self) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            validate_repo_value("..\\..\\etc\\passwd")

    def test_relative_path_accepted(self) -> None:
        """Single dots (current dir) are fine."""
        assert validate_repo_value("./my-repo") == "./my-repo"

    def test_deep_path_accepted(self) -> None:
        assert (
            validate_repo_value("/home/user/repos/my-repo")
            == "/home/user/repos/my-repo"
        )

    # --- Type guard (v368) ---

    def test_non_string_int_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="repo must be a string, got int"):
            validate_repo_value(42)  # type: ignore[arg-type]

    def test_non_string_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="repo must be a string, got NoneType"):
            validate_repo_value(None)  # type: ignore[arg-type]

    def test_non_string_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="repo must be a string, got list"):
            validate_repo_value(["owner/repo"])  # type: ignore[arg-type]

    def test_non_string_bool_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="repo must be a string, got bool"):
            validate_repo_value(True)  # type: ignore[arg-type]
