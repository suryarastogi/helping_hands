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

import inspect

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

    def test_has_docstring(self) -> None:
        assert require_non_empty_string.__doc__ is not None
        assert len(require_non_empty_string.__doc__) > 20

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

    def test_has_docstring(self) -> None:
        assert require_positive_int.__doc__ is not None
        assert len(require_positive_int.__doc__) > 20

    def test_module_all(self) -> None:
        from helping_hands.lib import validation

        assert "require_positive_int" in validation.__all__


# ---------------------------------------------------------------------------
# Delegation verification — confirm refactored sites import the helpers
# ---------------------------------------------------------------------------


class TestDelegationGithub:
    """Verify github.py delegates to shared validators."""

    def test_validate_full_name_uses_helper(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        source = inspect.getsource(_validate_full_name)
        assert "require_non_empty_string" in source

    def test_validate_branch_name_uses_helper(self) -> None:
        from helping_hands.lib.github import _validate_branch_name

        source = inspect.getsource(_validate_branch_name)
        assert "require_non_empty_string" in source


class TestDelegationMcpServer:
    """Verify mcp_server.py delegates to shared validators."""

    def test_build_feature_uses_helper(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        source = inspect.getsource(build_feature)
        assert "require_non_empty_string" in source

    def test_get_task_status_uses_helper(self) -> None:
        from helping_hands.server.mcp_server import get_task_status

        source = inspect.getsource(get_task_status)
        assert "require_non_empty_string" in source


class TestDelegationBase:
    """Verify base.py Hand delegates to shared validators."""

    def test_build_generic_pr_body_uses_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        source = inspect.getsource(Hand._build_generic_pr_body)
        assert "require_non_empty_string" in source

    def test_configure_push_remote_uses_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand

        source = inspect.getsource(Hand._configure_authenticated_push_remote)
        assert "require_non_empty_string" in source


class TestDelegationPrDescription:
    """Verify pr_description.py delegates to shared validators."""

    def test_truncate_text_uses_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_text

        source = inspect.getsource(_truncate_text)
        assert "require_positive_int" in source

    def test_truncate_diff_uses_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import _truncate_diff

        source = inspect.getsource(_truncate_diff)
        assert "require_positive_int" in source

    def test_generate_pr_description_uses_helper(self) -> None:
        from helping_hands.lib.hands.v1.hand.pr_description import (
            generate_pr_description,
        )

        source = inspect.getsource(generate_pr_description)
        assert "require_non_empty_string" in source


_has_fastapi = True
try:
    import fastapi as _fastapi  # noqa: F401
except ModuleNotFoundError:
    _has_fastapi = False

_skip_no_fastapi = pytest.mark.skipif(not _has_fastapi, reason="fastapi not installed")


@_skip_no_fastapi
class TestDelegationAppValidatePathParam:
    """Verify app.py _validate_path_param delegates to shared validator."""

    def test_delegates_to_require_non_empty_string(self) -> None:
        from helping_hands.server.app import _validate_path_param

        source = inspect.getsource(_validate_path_param)
        assert "require_non_empty_string" in source

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


class TestDelegationFilesystem:
    """Verify filesystem.py delegates to shared validators."""

    def test_read_text_file_uses_helper(self) -> None:
        from helping_hands.lib.meta.tools.filesystem import read_text_file

        source = inspect.getsource(read_text_file)
        assert "require_positive_int" in source


class TestDelegationWeb:
    """Verify web.py delegates to shared validators."""

    def test_search_web_uses_helper(self) -> None:
        from helping_hands.lib.meta.tools.web import search_web

        source = inspect.getsource(search_web)
        assert "require_positive_int" in source

    def test_browse_url_uses_helper(self) -> None:
        from helping_hands.lib.meta.tools.web import browse_url

        source = inspect.getsource(browse_url)
        assert "require_positive_int" in source


class TestDelegationCommand:
    """Verify command.py delegates to shared validators."""

    def test_run_command_uses_helper(self) -> None:
        from helping_hands.lib.meta.tools.command import _run_command

        source = inspect.getsource(_run_command)
        assert "require_positive_int" in source


class TestDelegationGithubUrl:
    """Verify github_url.py delegates to shared validators."""

    def test_validate_repo_spec_uses_helper(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        source = inspect.getsource(validate_repo_spec)
        assert "require_non_empty_string" in source
