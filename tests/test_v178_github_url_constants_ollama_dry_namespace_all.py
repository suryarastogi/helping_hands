"""Tests for v178: GitHub URL constants, Ollama base URL DRY, namespace __all__."""

from __future__ import annotations

import importlib

import pytest

# ---------------------------------------------------------------------------
# _GITHUB_TOKEN_USER constant tests
# ---------------------------------------------------------------------------


class TestGitHubTokenUserConstant:
    """Verify _GITHUB_TOKEN_USER exists and has correct value in all 4 modules."""

    def test_github_py_value(self) -> None:
        from helping_hands.lib.github import _GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER == "x-access-token"

    def test_github_py_type(self) -> None:
        from helping_hands.lib.github import _GITHUB_TOKEN_USER

        assert isinstance(_GITHUB_TOKEN_USER, str)

    def test_base_py_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER == "x-access-token"

    def test_cli_main_py_value(self) -> None:
        from helping_hands.cli.main import _GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER == "x-access-token"

    @pytest.mark.skipif(
        not importlib.util.find_spec("celery"),
        reason="celery not installed",
    )
    def test_celery_app_py_value(self) -> None:
        from helping_hands.server.celery_app import _GITHUB_TOKEN_USER

        assert _GITHUB_TOKEN_USER == "x-access-token"

    def test_cross_module_sync_github_base(self) -> None:
        """github.py and base.py constants must be identical."""
        from helping_hands.lib.github import (
            _GITHUB_TOKEN_USER as _GITHUB_VAL,
        )
        from helping_hands.lib.hands.v1.hand.base import (
            _GITHUB_TOKEN_USER as _BASE_VAL,
        )

        assert _GITHUB_VAL == _BASE_VAL

    def test_cross_module_sync_github_cli(self) -> None:
        """github.py and cli/main.py constants must be identical."""
        from helping_hands.cli.main import (
            _GITHUB_TOKEN_USER as _CLI_VAL,
        )
        from helping_hands.lib.github import (
            _GITHUB_TOKEN_USER as _GITHUB_VAL,
        )

        assert _GITHUB_VAL == _CLI_VAL

    @pytest.mark.skipif(
        not importlib.util.find_spec("celery"),
        reason="celery not installed",
    )
    def test_cross_module_sync_github_celery(self) -> None:
        """github.py and celery_app.py constants must be identical."""
        from helping_hands.lib.github import (
            _GITHUB_TOKEN_USER as _GITHUB_VAL,
        )
        from helping_hands.server.celery_app import (
            _GITHUB_TOKEN_USER as _CELERY_VAL,
        )

        assert _GITHUB_VAL == _CELERY_VAL


# ---------------------------------------------------------------------------
# _GITHUB_HOSTNAME constant tests
# ---------------------------------------------------------------------------


class TestGitHubHostnameConstant:
    """Verify _GITHUB_HOSTNAME exists and has correct value in base.py."""

    def test_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_HOSTNAME

        assert _GITHUB_HOSTNAME == "github.com"

    def test_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_HOSTNAME

        assert isinstance(_GITHUB_HOSTNAME, str)

    def test_no_scheme(self) -> None:
        """Hostname constant should not include a protocol scheme."""
        from helping_hands.lib.hands.v1.hand.base import _GITHUB_HOSTNAME

        assert "://" not in _GITHUB_HOSTNAME


# ---------------------------------------------------------------------------
# _GITHUB_TOKEN_USER usage in redaction (github.py)
# ---------------------------------------------------------------------------


class TestRedactSensitiveUsesConstant:
    """Ensure _redact_sensitive still works correctly with the constant."""

    def test_redacts_token_url(self) -> None:
        from helping_hands.lib.github import _redact_sensitive

        url = "https://x-access-token:ghp_secret123@github.com/owner/repo.git"
        result = _redact_sensitive(url)
        assert "ghp_secret123" not in result
        assert "***" in result

    def test_preserves_non_token_url(self) -> None:
        from helping_hands.lib.github import _redact_sensitive

        url = "https://github.com/owner/repo.git"
        assert _redact_sensitive(url) == url


# ---------------------------------------------------------------------------
# _DEFAULT_OLLAMA_BASE_URL and _DEFAULT_OLLAMA_API_KEY tests
# ---------------------------------------------------------------------------


class TestOllamaConstants:
    """Verify Ollama constants in model_provider.py."""

    def test_base_url_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import (
            _DEFAULT_OLLAMA_BASE_URL,
        )

        assert _DEFAULT_OLLAMA_BASE_URL == "http://localhost:11434/v1"

    def test_base_url_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import (
            _DEFAULT_OLLAMA_BASE_URL,
        )

        assert isinstance(_DEFAULT_OLLAMA_BASE_URL, str)

    def test_api_key_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import (
            _DEFAULT_OLLAMA_API_KEY,
        )

        assert _DEFAULT_OLLAMA_API_KEY == "ollama"

    def test_api_key_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.model_provider import (
            _DEFAULT_OLLAMA_API_KEY,
        )

        assert isinstance(_DEFAULT_OLLAMA_API_KEY, str)

    def test_base_url_matches_ollama_provider(self) -> None:
        """model_provider and ollama provider should agree on default URL."""
        from helping_hands.lib.ai_providers.ollama import OllamaProvider
        from helping_hands.lib.hands.v1.hand.model_provider import (
            _DEFAULT_OLLAMA_BASE_URL,
        )

        assert OllamaProvider.default_base_url == _DEFAULT_OLLAMA_BASE_URL


# ---------------------------------------------------------------------------
# Namespace __init__.py __all__ tests
# ---------------------------------------------------------------------------


class TestNamespacePackageAll:
    """Verify namespace packages have __all__ declarations."""

    def test_lib_init_has_all(self) -> None:
        import helping_hands.lib

        assert hasattr(helping_hands.lib, "__all__")
        assert isinstance(helping_hands.lib.__all__, list)

    def test_lib_init_no_private(self) -> None:
        import helping_hands.lib

        for name in helping_hands.lib.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_hands_init_has_all(self) -> None:
        import helping_hands.lib.hands

        assert hasattr(helping_hands.lib.hands, "__all__")
        assert isinstance(helping_hands.lib.hands.__all__, list)

    def test_hands_init_no_private(self) -> None:
        import helping_hands.lib.hands

        for name in helping_hands.lib.hands.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_server_init_has_all(self) -> None:
        import helping_hands.server

        assert hasattr(helping_hands.server, "__all__")
        assert isinstance(helping_hands.server.__all__, list)

    def test_server_init_no_private(self) -> None:
        import helping_hands.server

        for name in helping_hands.server.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_cli_init_has_all(self) -> None:
        import helping_hands.cli

        assert hasattr(helping_hands.cli, "__all__")
        assert isinstance(helping_hands.cli.__all__, list)

    def test_cli_init_no_private(self) -> None:
        import helping_hands.cli

        for name in helping_hands.cli.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"


# ---------------------------------------------------------------------------
# _github_repo_from_origin uses _GITHUB_HOSTNAME constant
# ---------------------------------------------------------------------------


class TestGitHubRepoFromOriginUsesConstant:
    """Verify _github_repo_from_origin still works with extracted constants."""

    def test_https_origin(self, tmp_path, monkeypatch) -> None:
        """HTTPS remote is parsed correctly using _GITHUB_HOSTNAME constant."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        monkeypatch.setattr(
            Hand,
            "_run_git_read",
            staticmethod(lambda _dir, *_args: "https://github.com/owner/repo.git"),
        )
        result = Hand._github_repo_from_origin(tmp_path)
        assert result == "owner/repo"

    def test_scp_origin(self, tmp_path, monkeypatch) -> None:
        """SCP-style remote is parsed correctly using _GITHUB_HOSTNAME constant."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        monkeypatch.setattr(
            Hand,
            "_run_git_read",
            staticmethod(lambda _dir, *_args: "git@github.com:owner/repo.git"),
        )
        result = Hand._github_repo_from_origin(tmp_path)
        assert result == "owner/repo"

    def test_non_github_origin(self, tmp_path, monkeypatch) -> None:
        """Non-GitHub remote returns empty string."""
        from helping_hands.lib.hands.v1.hand.base import Hand

        monkeypatch.setattr(
            Hand,
            "_run_git_read",
            staticmethod(lambda _dir, *_args: "https://gitlab.com/owner/repo.git"),
        )
        result = Hand._github_repo_from_origin(tmp_path)
        assert result == ""
