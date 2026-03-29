"""Tests for v270: has_cli_flag(), install_hint(), and _check_optional_dep().

has_cli_flag() is used to detect whether a flag is already present in a
command token list before injecting it again. The exact-match vs prefix-match
semantics are critical: "--model-name" must not match "--model", otherwise
injecting --model after the user has already supplied --model-name produces
a duplicate-flag CLI error.

install_hint() generates the "uv add X" message shown when an optional
dependency is missing. If the format changes, users receive malformed install
commands.

_check_optional_dep() gates Celery schedule functionality; if it stops raising
ImportError for missing packages rather than propagating the error, the
schedules endpoint returns 500 instead of a clear "install celery" message.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.validation import has_cli_flag, install_hint

celery = pytest.importorskip("celery")
from helping_hands.server.schedules import _check_optional_dep  # noqa: E402

# ---------------------------------------------------------------------------
# has_cli_flag
# ---------------------------------------------------------------------------


class TestHasCliFlag:
    """Tests for has_cli_flag()."""

    def test_exact_match(self) -> None:
        assert has_cli_flag(["--model", "gpt-4"], "model") is True

    def test_prefix_match(self) -> None:
        assert has_cli_flag(["--model=gpt-4"], "model") is True

    def test_no_match(self) -> None:
        assert has_cli_flag(["--verbose", "--debug"], "model") is False

    def test_empty_list(self) -> None:
        assert has_cli_flag([], "model") is False

    def test_substring_not_matched(self) -> None:
        """--model-name should not match --model."""
        assert has_cli_flag(["--model-name", "foo"], "model") is False

    def test_prefix_with_equals_value(self) -> None:
        assert has_cli_flag(["--sandbox=docker"], "sandbox") is True

    def test_flag_among_many_tokens(self) -> None:
        tokens = ["gemini", "run", "--approval-mode", "auto_edit", "-p", "hi"]
        assert has_cli_flag(tokens, "approval-mode") is True

    def test_flag_not_among_many_tokens(self) -> None:
        tokens = ["gemini", "run", "-p", "hi"]
        assert has_cli_flag(tokens, "approval-mode") is False

    def test_equals_form_among_many(self) -> None:
        tokens = ["goose", "run", "--with-builtin=developer"]
        assert has_cli_flag(tokens, "with-builtin") is True

    def test_output_format_match(self) -> None:
        tokens = ["claude", "-p", "hi", "--output-format", "stream-json"]
        assert has_cli_flag(tokens, "output-format") is True

    def test_output_format_equals_match(self) -> None:
        tokens = ["claude", "-p", "hi", "--output-format=stream-json"]
        assert has_cli_flag(tokens, "output-format") is True

    def test_partial_flag_name_no_match(self) -> None:
        """--out should not match --output-format."""
        assert has_cli_flag(["--output-format", "json"], "out") is False

    def test_double_dash_only_no_match(self) -> None:
        assert has_cli_flag(["--"], "model") is False

    def test_single_dash_no_match(self) -> None:
        assert has_cli_flag(["-model"], "model") is False


# ---------------------------------------------------------------------------
# install_hint
# ---------------------------------------------------------------------------


class TestInstallHint:
    """Tests for install_hint()."""

    def test_server_extra(self) -> None:
        assert install_hint("server") == "Install with: uv sync --extra server"

    def test_langchain_extra(self) -> None:
        assert install_hint("langchain") == "Install with: uv sync --extra langchain"

    def test_atomic_extra(self) -> None:
        assert install_hint("atomic") == "Install with: uv sync --extra atomic"

    def test_custom_extra(self) -> None:
        result = install_hint("my-custom-extra")
        assert result == "Install with: uv sync --extra my-custom-extra"

    def test_returns_string(self) -> None:
        assert isinstance(install_hint("server"), str)


# ---------------------------------------------------------------------------
# _check_optional_dep
# ---------------------------------------------------------------------------


class TestCheckOptionalDep:
    """Tests for _check_optional_dep()."""

    def test_available_truthy_does_not_raise(self) -> None:
        _check_optional_dep(True, "test-package is required", "server")

    def test_available_object_does_not_raise(self) -> None:
        """A non-None module object should be treated as available."""
        _check_optional_dep(object(), "croniter is required", "server")

    def test_unavailable_false_raises(self) -> None:
        with pytest.raises(ImportError, match="croniter is required"):
            _check_optional_dep(False, "croniter is required", "server")

    def test_unavailable_none_raises(self) -> None:
        with pytest.raises(ImportError, match="redbeat is required"):
            _check_optional_dep(None, "redbeat is required", "server")

    def test_error_includes_install_hint(self) -> None:
        with pytest.raises(ImportError, match="uv sync --extra server"):
            _check_optional_dep(False, "missing dep", "server")

    def test_error_includes_custom_extra(self) -> None:
        with pytest.raises(ImportError, match="uv sync --extra langchain"):
            _check_optional_dep(False, "missing dep", "langchain")

    def test_zero_is_falsy(self) -> None:
        with pytest.raises(ImportError):
            _check_optional_dep(0, "dep needed", "server")

    def test_empty_string_is_falsy(self) -> None:
        with pytest.raises(ImportError):
            _check_optional_dep("", "dep needed", "server")

    def test_nonempty_string_is_truthy(self) -> None:
        _check_optional_dep("loaded", "dep needed", "server")
