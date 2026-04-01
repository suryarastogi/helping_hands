"""Guards that validation delegation, exception tuples, and env-var name
constants remain centralised so changes propagate consistently.

_validate_full_name() must delegate to validate_repo_spec(); if it
re-implements its own rules, the GitHub API client and CLI can diverge on
which owner/repo strings are legal. _TOOL_EXECUTION_ERRORS and
_RUN_ASYNC_ERRORS must be shared tuples (atomic.py imports from
iterative.py); adding a recoverable exception in one place must cover all
handlers. Config _ENV_* constants must match the actual env var names read
by Config.from_env(); drift silently disables feature flags.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# 1. _validate_full_name delegates to validate_repo_spec
# ---------------------------------------------------------------------------


class TestValidateFullNameDelegation:
    """_validate_full_name still enforces owner/repo + whitespace checks."""

    def test_valid_full_name(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        _validate_full_name("owner/repo")  # should not raise

    def test_valid_full_name_with_dots(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        _validate_full_name("my-org/my.repo")  # should not raise

    def test_empty_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="full_name"):
            _validate_full_name("")

    def test_whitespace_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="whitespace"):
            _validate_full_name("owner /repo")

    def test_tab_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="whitespace"):
            _validate_full_name("owner\t/repo")

    def test_no_slash_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("justaname")

    def test_empty_owner_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("/repo")

    def test_empty_repo_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("owner/")

    def test_too_many_slashes_raises(self) -> None:
        from helping_hands.lib.github import _validate_full_name

        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("a/b/c")


# ---------------------------------------------------------------------------
# 2. _TOOL_EXECUTION_ERRORS constant
# ---------------------------------------------------------------------------


class TestToolExecutionErrors:
    """_TOOL_EXECUTION_ERRORS contains the expected exception types."""

    def test_is_tuple(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts container type, not behavior
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_EXECUTION_ERRORS

        assert isinstance(_TOOL_EXECUTION_ERRORS, tuple)

    def test_contains_expected_types(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_EXECUTION_ERRORS

        expected = {
            FileNotFoundError,
            IsADirectoryError,
            NotADirectoryError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        }
        assert set(_TOOL_EXECUTION_ERRORS) == expected

    def test_all_are_exception_subclasses(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_EXECUTION_ERRORS

        for exc_type in _TOOL_EXECUTION_ERRORS:
            assert issubclass(exc_type, Exception)

    def test_catches_file_not_found(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_EXECUTION_ERRORS

        with pytest.raises(_TOOL_EXECUTION_ERRORS):
            raise FileNotFoundError("test")

    def test_catches_value_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_EXECUTION_ERRORS

        with pytest.raises(_TOOL_EXECUTION_ERRORS):
            raise ValueError("test")


# ---------------------------------------------------------------------------
# 3. _RUN_ASYNC_ERRORS constant
# ---------------------------------------------------------------------------


class TestRunAsyncErrors:
    """_RUN_ASYNC_ERRORS is shared between iterative.py and atomic.py."""

    def test_is_tuple(
        self,
    ) -> None:  # TODO: CLEANUP CANDIDATE — asserts container type, not behavior
        from helping_hands.lib.hands.v1.hand.iterative import _RUN_ASYNC_ERRORS

        assert isinstance(_RUN_ASYNC_ERRORS, tuple)

    def test_contains_expected_types(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _RUN_ASYNC_ERRORS

        expected = {RuntimeError, TypeError, ValueError, AttributeError, OSError}
        assert set(_RUN_ASYNC_ERRORS) == expected

    def test_all_are_exception_subclasses(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _RUN_ASYNC_ERRORS

        for exc_type in _RUN_ASYNC_ERRORS:
            assert issubclass(exc_type, Exception)

    def test_catches_runtime_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _RUN_ASYNC_ERRORS

        with pytest.raises(_RUN_ASYNC_ERRORS):
            raise RuntimeError("test")

    def test_catches_attribute_error(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _RUN_ASYNC_ERRORS

        with pytest.raises(_RUN_ASYNC_ERRORS):
            raise AttributeError("test")

    def test_atomic_imports_same_constant(self) -> None:
        """atomic.py imports _RUN_ASYNC_ERRORS from iterative.py."""
        from helping_hands.lib.hands.v1.hand import (
            atomic as _atomic_mod,
            iterative as _iter_mod,
        )

        assert _atomic_mod._RUN_ASYNC_ERRORS is _iter_mod._RUN_ASYNC_ERRORS


# ---------------------------------------------------------------------------
# 4. _ENV_* constants in config.py
# ---------------------------------------------------------------------------


class TestConfigEnvConstants:  # TODO: CLEANUP CANDIDATE — asserts string literal equality of private constants; the from_env integration tests below are the meaningful ones
    """Env var name constants exist and match the expected values."""

    def test_env_model(self) -> None:
        from helping_hands.lib.config import _ENV_MODEL

        assert _ENV_MODEL == "HELPING_HANDS_MODEL"

    def test_env_verbose(self) -> None:
        from helping_hands.lib.config import _ENV_VERBOSE

        assert _ENV_VERBOSE == "HELPING_HANDS_VERBOSE"

    def test_env_enable_execution(self) -> None:
        from helping_hands.lib.config import _ENV_ENABLE_EXECUTION

        assert _ENV_ENABLE_EXECUTION == "HELPING_HANDS_ENABLE_EXECUTION"

    def test_env_enable_web(self) -> None:
        from helping_hands.lib.config import _ENV_ENABLE_WEB

        assert _ENV_ENABLE_WEB == "HELPING_HANDS_ENABLE_WEB"

    def test_env_use_native_cli_auth(self) -> None:
        from helping_hands.lib.config import _ENV_USE_NATIVE_CLI_AUTH

        assert _ENV_USE_NATIVE_CLI_AUTH == "HELPING_HANDS_USE_NATIVE_CLI_AUTH"

    def test_env_tools(self) -> None:
        from helping_hands.lib.config import _ENV_TOOLS

        assert _ENV_TOOLS == "HELPING_HANDS_TOOLS"

    def test_env_skills(self) -> None:
        from helping_hands.lib.config import _ENV_SKILLS

        assert _ENV_SKILLS == "HELPING_HANDS_SKILLS"

    def test_env_github_token(self) -> None:
        from helping_hands.lib.config import _ENV_GITHUB_TOKEN

        assert _ENV_GITHUB_TOKEN == "HELPING_HANDS_GITHUB_TOKEN"

    def test_env_reference_repos(self) -> None:
        from helping_hands.lib.config import _ENV_REFERENCE_REPOS

        assert _ENV_REFERENCE_REPOS == "HELPING_HANDS_REFERENCE_REPOS"

    def test_from_env_reads_model_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config.from_env() uses _ENV_MODEL to read the model."""
        from helping_hands.lib.config import _ENV_MODEL, Config

        monkeypatch.setenv(_ENV_MODEL, "test-model-v264")
        cfg = Config.from_env()
        assert cfg.model == "test-model-v264"

    def test_from_env_reads_verbose_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config.from_env() uses _ENV_VERBOSE to read verbose flag."""
        from helping_hands.lib.config import _ENV_VERBOSE, Config

        monkeypatch.setenv(_ENV_VERBOSE, "true")
        cfg = Config.from_env()
        assert cfg.verbose is True

    def test_from_env_reads_github_token_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config.from_env() uses _ENV_GITHUB_TOKEN to read the token."""
        from helping_hands.lib.config import _ENV_GITHUB_TOKEN, Config

        monkeypatch.setenv(_ENV_GITHUB_TOKEN, "ghp_test264")
        cfg = Config.from_env()
        assert cfg.github_token == "ghp_test264"

    def test_from_env_reads_reference_repos_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config.from_env() uses _ENV_REFERENCE_REPOS to read refs."""
        from helping_hands.lib.config import _ENV_REFERENCE_REPOS, Config

        monkeypatch.setenv(_ENV_REFERENCE_REPOS, "org/a,org/b")
        cfg = Config.from_env()
        assert cfg.reference_repos == ("org/a", "org/b")
