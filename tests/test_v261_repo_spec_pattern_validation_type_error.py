"""Guards centralised repo-spec validation and type-error formatting so the
CLI and Celery server never diverge on what constitutes a valid input.

REPO_SPEC_PATTERN must be the single regex for owner/repo matching; if
cli/main.py or celery_app.py re-introduce local copies the two entry points
can silently accept different repo formats. invalid_repo_msg() must include
both "directory" and "owner/repo" so users know the valid input shapes.
format_type_error() must be used by all require_* validators; inline format
strings would require touching every validator for a wording change.
"""

from __future__ import annotations

import re

import pytest

# ---------------------------------------------------------------------------
# REPO_SPEC_PATTERN centralised in github_url
# ---------------------------------------------------------------------------


class TestRepoSpecPattern:
    """Verify the shared REPO_SPEC_PATTERN constant."""

    def test_pattern_is_string(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts type, not behavior
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert isinstance(REPO_SPEC_PATTERN, str)

    def test_pattern_matches_simple_owner_repo(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert re.fullmatch(REPO_SPEC_PATTERN, "owner/repo")

    def test_pattern_matches_dotted_names(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert re.fullmatch(REPO_SPEC_PATTERN, "my-org/my.repo-name")

    def test_pattern_matches_underscores_hyphens(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert re.fullmatch(REPO_SPEC_PATTERN, "A_B-C/D.E_F")

    def test_pattern_rejects_bare_name(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert not re.fullmatch(REPO_SPEC_PATTERN, "just-a-name")

    def test_pattern_rejects_triple_slash(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert not re.fullmatch(REPO_SPEC_PATTERN, "a/b/c")

    def test_pattern_rejects_empty(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert not re.fullmatch(REPO_SPEC_PATTERN, "")

    def test_pattern_rejects_slash_only(self) -> None:
        from helping_hands.lib.github_url import REPO_SPEC_PATTERN

        assert not re.fullmatch(REPO_SPEC_PATTERN, "/")

    def test_pattern_in_all(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — stylistic __all__ check
        from helping_hands.lib import github_url

        assert "REPO_SPEC_PATTERN" in github_url.__all__

    def test_cli_no_local_pattern(self) -> None:
        """cli/main.py should not define its own _REPO_SPEC_PATTERN."""
        import inspect

        import helping_hands.cli.main as cli_mod

        src = inspect.getsource(cli_mod)
        # Should import it, not define it locally
        assert '_REPO_SPEC_PATTERN = r"' not in src

    def test_celery_uses_constant(self) -> None:
        """celery_app.py should not have an inline regex for owner/repo."""
        pytest.importorskip("celery")
        import inspect

        from helping_hands.server import celery_app as ca_mod

        src = inspect.getsource(ca_mod)
        # The raw regex literal should no longer appear as a string argument
        assert 'r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"' not in src


# ---------------------------------------------------------------------------
# invalid_repo_msg centralised in github_url
# ---------------------------------------------------------------------------


class TestInvalidRepoMsg:
    """Verify the shared invalid_repo_msg helper."""

    def test_returns_string(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts return type, not content
        from helping_hands.lib.github_url import invalid_repo_msg

        result = invalid_repo_msg("bad-input")
        assert isinstance(result, str)

    def test_message_contains_repo(self) -> None:
        from helping_hands.lib.github_url import invalid_repo_msg

        msg = invalid_repo_msg("not-a-repo")
        assert "not-a-repo" in msg

    def test_message_mentions_directory(self) -> None:
        from helping_hands.lib.github_url import invalid_repo_msg

        msg = invalid_repo_msg("xyz")
        assert "directory" in msg

    def test_message_mentions_owner_repo(self) -> None:
        from helping_hands.lib.github_url import invalid_repo_msg

        msg = invalid_repo_msg("xyz")
        assert "owner/repo" in msg

    def test_in_all(self) -> None:  # TODO: CLEANUP CANDIDATE — stylistic __all__ check
        from helping_hands.lib import github_url

        assert "invalid_repo_msg" in github_url.__all__

    def test_cli_uses_helper(self) -> None:
        """cli/main.py should not have a hardcoded error message."""
        import inspect

        import helping_hands.cli.main as cli_mod

        src = inspect.getsource(cli_mod)
        assert "is not a directory or owner/repo reference" not in src

    def test_celery_uses_helper(self) -> None:
        """celery_app.py should not have a hardcoded error message."""
        pytest.importorskip("celery")
        import inspect

        from helping_hands.server import celery_app as ca_mod

        src = inspect.getsource(ca_mod)
        assert "is not a directory or owner/repo reference" not in src


# ---------------------------------------------------------------------------
# format_type_error centralised in validation
# ---------------------------------------------------------------------------


class TestFormatTypeError:
    """Verify the shared format_type_error helper."""

    def test_returns_string(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts return type, not content
        from helping_hands.lib.validation import format_type_error

        assert isinstance(format_type_error("x", "a string", 42), str)

    def test_includes_name(self) -> None:
        from helping_hands.lib.validation import format_type_error

        assert "my_param" in format_type_error("my_param", "a string", 42)

    def test_includes_expected(self) -> None:
        from helping_hands.lib.validation import format_type_error

        assert "a string" in format_type_error("x", "a string", 42)

    def test_includes_actual_type(self) -> None:
        from helping_hands.lib.validation import format_type_error

        assert "int" in format_type_error("x", "a string", 42)

    def test_format_for_list(self) -> None:
        from helping_hands.lib.validation import format_type_error

        assert "list" in format_type_error("x", "an int", [])

    def test_format_for_none(self) -> None:
        from helping_hands.lib.validation import format_type_error

        assert "NoneType" in format_type_error("x", "a string", None)

    def test_in_all(self) -> None:  # TODO: CLEANUP CANDIDATE — stylistic __all__ check
        from helping_hands.lib import validation

        assert "format_type_error" in validation.__all__

    def test_require_non_empty_string_uses_helper(self) -> None:
        """require_non_empty_string should raise TypeError via format_type_error."""
        from helping_hands.lib.validation import require_non_empty_string

        with pytest.raises(TypeError, match="must be a string, got int"):
            require_non_empty_string(42, "test_param")  # type: ignore[arg-type]

    def test_require_positive_float_uses_helper(self) -> None:
        """require_positive_float should raise TypeError via format_type_error."""
        from helping_hands.lib.validation import require_positive_float

        with pytest.raises(TypeError, match="must be a number, got str"):
            require_positive_float("nope", "test_param")  # type: ignore[arg-type]

    def test_require_positive_int_uses_helper(self) -> None:
        """require_positive_int should raise TypeError via format_type_error."""
        from helping_hands.lib.validation import require_positive_int

        with pytest.raises(TypeError, match="must be an int, got str"):
            require_positive_int("nope", "test_param")  # type: ignore[arg-type]

    def test_no_inline_format_strings(self) -> None:
        """validation.py should not have inline type-error format strings."""
        import inspect

        from helping_hands.lib import validation

        src = inspect.getsource(validation)
        # The old inline patterns should be gone
        assert 'f"{name} must be a string, got {type(value).__name__}"' not in src
        assert 'f"{name} must be a number, got {type(value).__name__}"' not in src
        assert 'f"{name} must be an int, got {type(value).__name__}"' not in src
