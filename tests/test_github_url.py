"""Dedicated unit tests for helping_hands.lib.github_url.

Covers all public functions and constants: validate_repo_spec, build_clone_url,
redact_credentials, noninteractive_env, and module-level constants.
"""

from __future__ import annotations

import os

import pytest

from helping_hands.lib.github_url import (
    GIT_CLONE_TIMEOUT_S,
    GITHUB_HOSTNAME,
    GITHUB_TOKEN_USER,
    build_clone_url,
    noninteractive_env,
    redact_credentials,
    validate_repo_spec,
)
from helping_hands.lib.github_url import (
    __all__ as github_url_all,
)

# ---------------------------------------------------------------------------
# Module __all__
# ---------------------------------------------------------------------------


class TestModuleAll:
    """Ensure public API surface is explicit."""

    def test_all_contains_expected_names(self) -> None:
        assert set(github_url_all) == {
            "DEFAULT_CLONE_DEPTH",
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "build_clone_url",
            "noninteractive_env",
            "redact_credentials",
            "run_git_clone",
            "validate_repo_spec",
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Smoke tests for module-level constants."""

    def test_github_hostname(self) -> None:
        assert GITHUB_HOSTNAME == "github.com"

    def test_github_token_user(self) -> None:
        assert GITHUB_TOKEN_USER == "x-access-token"

    def test_git_clone_timeout_positive(self) -> None:
        assert GIT_CLONE_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# validate_repo_spec
# ---------------------------------------------------------------------------


class TestValidateRepoSpec:
    """Tests for validate_repo_spec()."""

    def test_valid_owner_repo(self) -> None:
        validate_repo_spec("owner/repo")  # should not raise

    def test_valid_with_dashes(self) -> None:
        validate_repo_spec("my-org/my-repo")

    def test_valid_with_dots(self) -> None:
        validate_repo_spec("org/repo.js")

    def test_valid_with_underscores(self) -> None:
        validate_repo_spec("org_name/repo_name")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            validate_repo_spec("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError):
            validate_repo_spec("   ")

    def test_rejects_single_segment(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("justrepo")

    def test_rejects_three_segments(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("a/b/c")

    def test_rejects_trailing_slash(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("owner/")

    def test_rejects_leading_slash(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("/repo")

    def test_strips_whitespace_before_validation(self) -> None:
        validate_repo_spec("  owner/repo  ")  # should not raise


# ---------------------------------------------------------------------------
# build_clone_url
# ---------------------------------------------------------------------------


class TestBuildCloneUrl:
    """Tests for build_clone_url()."""

    def test_no_token_returns_public_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_explicit_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo", token="ghp_abc123")
        assert url == "https://x-access-token:ghp_abc123@github.com/owner/repo.git"

    def test_github_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_tok")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo")
        assert "ghp_env_tok" in url
        assert url.startswith("https://x-access-token:")

    def test_gh_token_env_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_gh_tok")
        url = build_clone_url("owner/repo")
        assert "ghp_gh_tok" in url

    def test_explicit_token_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env")
        url = build_clone_url("owner/repo", token="ghp_explicit")
        assert "ghp_explicit" in url
        assert "ghp_env" not in url

    def test_whitespace_token_treated_as_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo", token="   ")
        assert url == "https://github.com/owner/repo.git"

    def test_invalid_repo_raises(self) -> None:
        with pytest.raises(ValueError):
            build_clone_url("invalid")


# ---------------------------------------------------------------------------
# redact_credentials
# ---------------------------------------------------------------------------


class TestRedactCredentials:
    """Tests for redact_credentials()."""

    def test_redacts_token_in_url(self) -> None:
        url = "https://x-access-token:ghp_secret123@github.com/owner/repo.git"
        result = redact_credentials(url)
        assert "ghp_secret123" not in result
        assert "***" in result
        assert "github.com/owner/repo.git" in result

    def test_preserves_url_without_token(self) -> None:
        url = "https://github.com/owner/repo.git"
        assert redact_credentials(url) == url

    def test_redacts_multiple_urls(self) -> None:
        text = (
            "cloned https://x-access-token:tok1@github.com/a/b.git "
            "and https://x-access-token:tok2@github.com/c/d.git"
        )
        result = redact_credentials(text)
        assert "tok1" not in result
        assert "tok2" not in result
        assert result.count("***") == 2

    def test_preserves_surrounding_text(self) -> None:
        text = "prefix https://x-access-token:secret@github.com/o/r suffix"
        result = redact_credentials(text)
        assert result.startswith("prefix ")
        assert result.endswith(" suffix")

    def test_empty_string(self) -> None:
        assert redact_credentials("") == ""

    def test_no_github_urls(self) -> None:
        text = "just some random text with no URLs"
        assert redact_credentials(text) == text


# ---------------------------------------------------------------------------
# noninteractive_env
# ---------------------------------------------------------------------------


class TestNoninteractiveEnv:
    """Tests for noninteractive_env()."""

    def test_sets_git_terminal_prompt(self) -> None:
        env = noninteractive_env()
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_sets_gcm_interactive(self) -> None:
        env = noninteractive_env()
        assert env["GCM_INTERACTIVE"] == "never"

    def test_preserves_existing_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_CUSTOM_VAR", "my_value")
        env = noninteractive_env()
        assert env["MY_CUSTOM_VAR"] == "my_value"

    def test_returns_copy_not_original(self) -> None:
        env = noninteractive_env()
        env["SHOULD_NOT_LEAK"] = "true"
        assert "SHOULD_NOT_LEAK" not in os.environ

    def test_returns_dict(self) -> None:
        assert isinstance(noninteractive_env(), dict)
