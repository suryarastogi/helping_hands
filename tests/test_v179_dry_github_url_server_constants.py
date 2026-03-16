"""Tests for v179 — DRY GitHub URL helpers and server constants.

Validates:
- ``lib/github_url`` shared module (build_clone_url, validate_repo_spec,
  redact_credentials, noninteractive_env, constants)
- ``server/constants`` shared module (Anthropic, Keychain, JWT constants)
- Consumer modules import from shared sources (no local duplicates)
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# lib/github_url — constants
# ---------------------------------------------------------------------------


class TestGitHubUrlConstants:
    """Verify exported constants in lib/github_url."""

    def test_github_token_user_value(self) -> None:
        from helping_hands.lib.github_url import GITHUB_TOKEN_USER

        assert GITHUB_TOKEN_USER == "x-access-token"

    def test_github_hostname_value(self) -> None:
        from helping_hands.lib.github_url import GITHUB_HOSTNAME

        assert GITHUB_HOSTNAME == "github.com"

    def test_all_exports(self) -> None:
        from helping_hands.lib import github_url

        expected = {
            "DEFAULT_CLONE_ERROR_MSG",
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "build_clone_url",
            "noninteractive_env",
            "redact_credentials",
            "validate_repo_spec",
        }
        assert set(github_url.__all__) == expected


# ---------------------------------------------------------------------------
# lib/github_url — validate_repo_spec
# ---------------------------------------------------------------------------


class TestValidateRepoSpec:
    """Validate repo spec validation logic."""

    def test_valid_spec(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        validate_repo_spec("owner/repo")  # should not raise

    def test_empty_raises(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        with pytest.raises(ValueError, match="must not be empty"):
            validate_repo_spec("")

    def test_whitespace_only_raises(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        with pytest.raises(ValueError, match="must not be empty"):
            validate_repo_spec("   ")

    def test_no_slash_raises(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("noslash")

    def test_too_many_parts_raises(self) -> None:
        from helping_hands.lib.github_url import validate_repo_spec

        with pytest.raises(ValueError, match="owner/repo"):
            validate_repo_spec("a/b/c")


# ---------------------------------------------------------------------------
# lib/github_url — build_clone_url
# ---------------------------------------------------------------------------


class TestBuildCloneUrl:
    """Validate clone URL construction."""

    def test_with_explicit_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo", token="ghp_abc")
        assert url == "https://x-access-token:ghp_abc@github.com/owner/repo.git"

    def test_with_env_github_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_env@github.com/owner/repo.git"

    def test_with_env_gh_token_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_fall")
        url = build_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_fall@github.com/owner/repo.git"

    def test_without_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_invalid_spec_raises(self) -> None:
        from helping_hands.lib.github_url import build_clone_url

        with pytest.raises(ValueError):
            build_clone_url("invalid")

    def test_whitespace_token_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo", token="   ")
        assert url == "https://github.com/owner/repo.git"


# ---------------------------------------------------------------------------
# lib/github_url — redact_credentials
# ---------------------------------------------------------------------------


class TestRedactCredentials:
    """Validate credential redaction in URLs."""

    def test_redacts_token(self) -> None:
        from helping_hands.lib.github_url import redact_credentials

        text = "https://x-access-token:ghp_secret@github.com/o/r.git"
        result = redact_credentials(text)
        assert "ghp_secret" not in result
        assert "***" in result

    def test_no_token_unchanged(self) -> None:
        from helping_hands.lib.github_url import redact_credentials

        text = "https://github.com/owner/repo.git"
        assert redact_credentials(text) == text

    def test_multiple_urls(self) -> None:
        from helping_hands.lib.github_url import redact_credentials

        text = (
            "https://x-access-token:aaa@github.com/a/b "
            "https://x-access-token:bbb@github.com/c/d"
        )
        result = redact_credentials(text)
        assert "aaa" not in result
        assert "bbb" not in result


# ---------------------------------------------------------------------------
# lib/github_url — noninteractive_env
# ---------------------------------------------------------------------------


class TestNoninteractiveEnv:
    """Validate non-interactive git environment."""

    def test_sets_git_terminal_prompt(self) -> None:
        from helping_hands.lib.github_url import noninteractive_env

        env = noninteractive_env()
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_sets_gcm_interactive(self) -> None:
        from helping_hands.lib.github_url import noninteractive_env

        env = noninteractive_env()
        assert env["GCM_INTERACTIVE"] == "never"

    def test_inherits_current_env(self) -> None:
        from helping_hands.lib.github_url import noninteractive_env

        env = noninteractive_env()
        assert "PATH" in env


# ---------------------------------------------------------------------------
# server/constants — Anthropic usage API
# ---------------------------------------------------------------------------


class TestServerConstants:
    """Validate shared server constants."""

    def test_anthropic_usage_url(self) -> None:
        from helping_hands.server.constants import ANTHROPIC_USAGE_URL

        assert ANTHROPIC_USAGE_URL == "https://api.anthropic.com/api/oauth/usage"

    def test_anthropic_beta_header(self) -> None:
        from helping_hands.server.constants import ANTHROPIC_BETA_HEADER

        assert ANTHROPIC_BETA_HEADER == "oauth-2025-04-20"

    def test_usage_user_agent(self) -> None:
        from helping_hands.server.constants import USAGE_USER_AGENT

        assert USAGE_USER_AGENT == "claude-code/2.0.32"

    def test_keychain_service_name(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_SERVICE_NAME

        assert KEYCHAIN_SERVICE_NAME == "Claude Code-credentials"

    def test_keychain_oauth_key(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_OAUTH_KEY

        assert KEYCHAIN_OAUTH_KEY == "claudeAiOauth"

    def test_keychain_access_token_key(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_ACCESS_TOKEN_KEY

        assert KEYCHAIN_ACCESS_TOKEN_KEY == "accessToken"

    def test_jwt_token_prefix(self) -> None:
        from helping_hands.server.constants import JWT_TOKEN_PREFIX

        assert JWT_TOKEN_PREFIX == "ey"

    def test_all_exports(self) -> None:
        from helping_hands.server import constants

        # Superset check: at minimum these must be present (v232 added more)
        required = {
            "ANTHROPIC_BETA_HEADER",
            "ANTHROPIC_USAGE_URL",
            "DEFAULT_BACKEND",
            "DEFAULT_CI_WAIT_MINUTES",
            "DEFAULT_MAX_ITERATIONS",
            "JWT_TOKEN_PREFIX",
            "KEYCHAIN_ACCESS_TOKEN_KEY",
            "KEYCHAIN_OAUTH_KEY",
            "KEYCHAIN_SERVICE_NAME",
            "MAX_CI_WAIT_MINUTES",
            "MAX_GITHUB_TOKEN_LENGTH",
            "MAX_ITERATIONS_UPPER_BOUND",
            "MAX_MODEL_LENGTH",
            "MAX_PROMPT_LENGTH",
            "MAX_REFERENCE_REPOS",
            "MAX_REPO_PATH_LENGTH",
            "MIN_CI_WAIT_MINUTES",
            "KEYCHAIN_TIMEOUT_S",
            "USAGE_API_TIMEOUT_S",
            "USAGE_CACHE_TTL_S",
            "USAGE_USER_AGENT",
        }
        assert required <= set(constants.__all__)


# ---------------------------------------------------------------------------
# Consumer import consistency — verify no local duplicates
# ---------------------------------------------------------------------------


class TestConsumerImportConsistency:
    """Ensure consumer modules use the shared constants, not local copies."""

    def test_github_py_uses_shared_token_user(self) -> None:
        from helping_hands.lib.github import _GITHUB_TOKEN_USER
        from helping_hands.lib.github_url import GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER is GITHUB_TOKEN_USER

    def test_base_py_uses_shared_token_user(self) -> None:
        from helping_hands.lib.github_url import GITHUB_TOKEN_USER
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER is GITHUB_TOKEN_USER

    def test_base_py_uses_shared_hostname(self) -> None:
        from helping_hands.lib.github_url import GITHUB_HOSTNAME
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_HOSTNAME

        assert _GITHUB_HOSTNAME is GITHUB_HOSTNAME

    def test_cli_delegates_to_shared_clone_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.cli.main import _github_clone_url
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert _github_clone_url("owner/repo") == build_clone_url("owner/repo")

    def test_celery_delegates_to_shared_clone_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("celery")
        from helping_hands.lib.github_url import build_clone_url
        from helping_hands.server.celery_app import _github_clone_url

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert _github_clone_url("owner/repo") == build_clone_url("owner/repo")
