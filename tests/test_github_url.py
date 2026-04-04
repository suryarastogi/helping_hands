"""Dedicated unit tests for helping_hands.lib.github_url.

Protects the URL-building and credential-safety helpers used whenever a repo
is cloned: build_clone_url must embed tokens for authenticated clones and fall
back to a public URL gracefully; redact_credentials must scrub tokens from log
output even when multiple URLs appear in the same string (to prevent token
leakage in CI logs); noninteractive_env must set GIT_TERMINAL_PROMPT and
GCM_INTERACTIVE to suppress credential prompts in headless environments.
validate_repo_spec guards the owner/repo input contract consumed by all
downstream GitHub API calls.
"""

from __future__ import annotations

import os

import pytest

from helping_hands.lib.github_url import (
    GIT_CLONE_TIMEOUT_S,
    GITHUB_HOSTNAME,
    GITHUB_TOKEN_USER,
    __all__ as github_url_all,
    build_clone_url,
    invalid_repo_msg,
    noninteractive_env,
    redact_credentials,
    repo_tmp_dir,
    resolve_github_token,
    validate_repo_spec,
)

# ---------------------------------------------------------------------------
# Module __all__
# ---------------------------------------------------------------------------


class TestModuleAll:
    """Ensure public API surface is explicit."""

    def test_all_contains_expected_names(self) -> None:
        assert set(github_url_all) == {
            "DEFAULT_CLONE_ERROR_MSG",
            "ENV_GCM_INTERACTIVE",
            "ENV_GIT_TERMINAL_PROMPT",
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "REPO_SPEC_PATTERN",
            "build_clone_url",
            "invalid_repo_msg",
            "noninteractive_env",
            "redact_credentials",
            "repo_tmp_dir",
            "resolve_github_token",
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
# invalid_repo_msg
# ---------------------------------------------------------------------------


class TestInvalidRepoMsg:
    """Tests for invalid_repo_msg()."""

    def test_includes_repo_arg(self) -> None:
        msg = invalid_repo_msg("badrepo")
        assert "badrepo" in msg

    def test_mentions_owner_repo(self) -> None:
        msg = invalid_repo_msg("/tmp/foo")
        assert "directory" in msg or "owner/repo" in msg

    def test_returns_string(self) -> None:
        assert isinstance(invalid_repo_msg("x"), str)


# ---------------------------------------------------------------------------
# resolve_github_token
# ---------------------------------------------------------------------------


class TestResolveGithubToken:
    """Tests for resolve_github_token()."""

    def test_explicit_token_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token("ghp_explicit") == "ghp_explicit"

    def test_github_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token() == "ghp_from_env"

    def test_gh_token_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_gh")
        assert resolve_github_token() == "ghp_gh"

    def test_explicit_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env")
        assert resolve_github_token("ghp_arg") == "ghp_arg"

    def test_no_token_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token() == ""

    def test_whitespace_token_treated_as_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token("   ") == ""

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token("  ghp_tok  ") == "ghp_tok"

    def test_github_token_priority_over_gh(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_primary")
        monkeypatch.setenv("GH_TOKEN", "ghp_secondary")
        assert resolve_github_token() == "ghp_primary"


# ---------------------------------------------------------------------------
# repo_tmp_dir
# ---------------------------------------------------------------------------


class TestRepoTmpDir:
    """Tests for repo_tmp_dir()."""

    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_REPO_TMP", raising=False)
        assert repo_tmp_dir() is None

    def test_returns_path_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: os.PathLike
    ) -> None:
        target = str(tmp_path / "clone_dir")
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", target)
        result = repo_tmp_dir()
        assert result is not None
        assert str(result) == target
        assert result.is_dir()

    def test_creates_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: os.PathLike
    ) -> None:
        target = str(tmp_path / "nested" / "deep" / "dir")
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", target)
        result = repo_tmp_dir()
        assert result is not None
        assert result.is_dir()

    def test_whitespace_only_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "   ")
        assert repo_tmp_dir() is None


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
