"""Tests for v208 — DRY bool_str, git clone error constant, resolve_github_token.

Validates:
- ``bool_str()`` helper returns ``"true"``/``"false"``
- ``DEFAULT_GIT_CLONE_ERROR_MSG`` constant value
- ``resolve_github_token()`` fallback chain
- Consumer modules import from shared ``github_url`` instead of inline logic
"""

from __future__ import annotations

import pytest


def _has_fastapi() -> bool:
    try:
        import fastapi  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# bool_str
# ---------------------------------------------------------------------------


class TestBoolStr:
    """Verify ``bool_str()`` converts booleans to lowercase strings."""

    def test_true(self) -> None:
        from helping_hands.lib.github_url import bool_str

        assert bool_str(True) == "true"

    def test_false(self) -> None:
        from helping_hands.lib.github_url import bool_str

        assert bool_str(False) == "false"

    def test_return_type(self) -> None:
        from helping_hands.lib.github_url import bool_str

        assert isinstance(bool_str(True), str)
        assert isinstance(bool_str(False), str)


# ---------------------------------------------------------------------------
# DEFAULT_GIT_CLONE_ERROR_MSG
# ---------------------------------------------------------------------------


class TestDefaultGitCloneErrorMsg:
    """Verify the clone error constant value and consumer usage."""

    def test_constant_value(self) -> None:
        from helping_hands.lib.github_url import DEFAULT_GIT_CLONE_ERROR_MSG

        assert DEFAULT_GIT_CLONE_ERROR_MSG == "unknown git clone error"

    def test_cli_imports_constant(self) -> None:
        """cli/main.py uses the shared constant, not an inline string."""
        import helping_hands.cli.main as cli_mod

        assert hasattr(cli_mod, "_DEFAULT_GIT_CLONE_ERROR_MSG")

    @pytest.mark.skipif(
        not _has_fastapi(),
        reason="fastapi not installed",
    )
    def test_celery_imports_constant(self) -> None:
        """celery_app.py uses the shared constant, not an inline string."""
        import helping_hands.server.celery_app as celery_mod

        assert hasattr(celery_mod, "_DEFAULT_GIT_CLONE_ERROR_MSG")


# ---------------------------------------------------------------------------
# resolve_github_token
# ---------------------------------------------------------------------------


class TestResolveGithubToken:
    """Verify ``resolve_github_token()`` fallback chain."""

    def test_explicit_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token("my-token") == "my-token"

    def test_explicit_token_with_whitespace(self) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        assert resolve_github_token("  my-token  ") == "my-token"

    def test_github_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token() == "env-token"

    def test_gh_token_env_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh-token")
        assert resolve_github_token() == "gh-token"

    def test_explicit_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert resolve_github_token("explicit") == "explicit"

    def test_none_token_falls_back_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert resolve_github_token(None) == "env-token"

    def test_empty_string_falls_back_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert resolve_github_token("") == "env-token"

    def test_whitespace_only_falls_back_to_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        assert resolve_github_token("   ") == "env-token"

    def test_no_token_anywhere(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from helping_hands.lib.github_url import resolve_github_token

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        assert resolve_github_token() == ""

    def test_github_client_uses_resolve(self) -> None:
        """github.py imports resolve_github_token from github_url."""
        import helping_hands.lib.github as gh_mod

        assert hasattr(gh_mod, "_resolve_github_token")

    def test_build_clone_url_uses_resolve(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """build_clone_url delegates token resolution to resolve_github_token."""
        from helping_hands.lib.github_url import build_clone_url

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        # With explicit token, URL includes credentials
        url = build_clone_url("owner/repo", token="tk")
        assert "tk" in url
        # Without token, URL has no credentials
        url_no_token = build_clone_url("owner/repo")
        assert "x-access-token" not in url_no_token


# ---------------------------------------------------------------------------
# Updated __all__ exports
# ---------------------------------------------------------------------------


class TestUpdatedExports:
    """Verify __all__ includes new helpers."""

    def test_all_exports_include_new_helpers(self) -> None:
        from helping_hands.lib import github_url

        expected = {
            "DEFAULT_GIT_CLONE_ERROR_MSG",
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "bool_str",
            "build_clone_url",
            "noninteractive_env",
            "redact_credentials",
            "resolve_github_token",
            "validate_repo_spec",
        }
        assert set(github_url.__all__) == expected


# ---------------------------------------------------------------------------
# Consumer module import checks
# ---------------------------------------------------------------------------


class TestConsumerImports:
    """Verify consumer modules import from shared github_url."""

    def test_e2e_imports_bool_str(self) -> None:
        import helping_hands.lib.hands.v1.hand.e2e as e2e_mod

        assert hasattr(e2e_mod, "_bool_str")

    def test_iterative_imports_bool_str(self) -> None:
        import helping_hands.lib.hands.v1.hand.iterative as iter_mod

        assert hasattr(iter_mod, "_bool_str")

    def test_base_hand_imports_bool_str(self) -> None:
        import helping_hands.lib.hands.v1.hand.base as base_mod

        assert hasattr(base_mod, "_bool_str")

    def test_cli_base_imports_bool_str(self) -> None:
        import helping_hands.lib.hands.v1.hand.cli.base as cli_base_mod

        assert hasattr(cli_base_mod, "_bool_str")
