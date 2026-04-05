"""Dedicated unit tests for helping_hands.lib.hands.v1.hand.factory.

Protects the centralised backend dispatch table that both CLI and server use
to instantiate Hand subclasses.  Regressions here would silently route users
to the wrong backend or raise confusing errors for valid backend names.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_BASIC_AGENT,
    BACKEND_BASIC_ATOMIC,
    BACKEND_BASIC_LANGGRAPH,
    BACKEND_CLAUDECODECLI,
    BACKEND_CODEXCLI,
    BACKEND_DEVINCLI,
    BACKEND_DOCKER_SANDBOX_CLAUDE,
    BACKEND_E2E,
    BACKEND_GEMINICLI,
    BACKEND_GOOSE,
    BACKEND_OPENCODECLI,
    SUPPORTED_BACKENDS,
    __all__ as factory_all,
    create_hand,
    get_enabled_backends,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Module __all__
# ---------------------------------------------------------------------------


class TestModuleAll:
    """Ensure public API surface is explicit."""

    def test_all_contains_expected_names(self) -> None:
        assert set(factory_all) == {
            "BACKEND_BASIC_AGENT",
            "BACKEND_BASIC_ATOMIC",
            "BACKEND_BASIC_LANGGRAPH",
            "BACKEND_CLAUDECODECLI",
            "BACKEND_CODEXCLI",
            "BACKEND_DEVINCLI",
            "BACKEND_DOCKER_SANDBOX_CLAUDE",
            "BACKEND_E2E",
            "BACKEND_GEMINICLI",
            "BACKEND_GOOSE",
            "BACKEND_OPENCODECLI",
            "SUPPORTED_BACKENDS",
            "create_hand",
            "get_enabled_backends",
            "is_backend_enabled",
        }


# ---------------------------------------------------------------------------
# SUPPORTED_BACKENDS constant
# ---------------------------------------------------------------------------


class TestSupportedBackends:
    """Smoke tests for the SUPPORTED_BACKENDS frozenset."""

    def test_is_frozenset(self) -> None:
        assert isinstance(SUPPORTED_BACKENDS, frozenset)

    def test_contains_all_backend_constants(self) -> None:
        expected = {
            BACKEND_E2E,
            BACKEND_BASIC_LANGGRAPH,
            BACKEND_BASIC_ATOMIC,
            BACKEND_BASIC_AGENT,
            BACKEND_CODEXCLI,
            BACKEND_CLAUDECODECLI,
            BACKEND_DOCKER_SANDBOX_CLAUDE,
            BACKEND_GOOSE,
            BACKEND_GEMINICLI,
            BACKEND_OPENCODECLI,
            BACKEND_DEVINCLI,
        }
        assert expected == SUPPORTED_BACKENDS

    def test_count(self) -> None:
        assert len(SUPPORTED_BACKENDS) == 11


# ---------------------------------------------------------------------------
# get_enabled_backends
# ---------------------------------------------------------------------------


class TestGetEnabledBackends:
    """Tests for get_enabled_backends()."""

    def test_no_env_vars_returns_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no *_ENABLED env vars are set, all backends are enabled."""
        for backend_const in SUPPORTED_BACKENDS:
            env_key = f"HELPING_HANDS_{backend_const.upper().replace('-', '_')}_ENABLED"
            monkeypatch.delenv(env_key, raising=False)
        # Also clear the actual env var names used in the code
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        result = get_enabled_backends()
        assert set(result) == SUPPORTED_BACKENDS

    def test_returns_sorted_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        result = get_enabled_backends()
        assert result == sorted(result)

    def test_single_backend_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_GOOSE_ENABLED", "1")
        result = get_enabled_backends()
        assert result == ["goose"]

    def test_truthy_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_E2E_ENABLED", "true")
        assert "e2e" in get_enabled_backends()

    def test_yes_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "yes")
        assert "codexcli" in get_enabled_backends()

    def test_on_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_GEMINICLI_ENABLED", "on")
        assert "geminicli" in get_enabled_backends()

    def test_falsy_value_excludes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_E2E_ENABLED", "0")
        result = get_enabled_backends()
        assert "e2e" not in result

    def test_multiple_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HELPING_HANDS_E2E_ENABLED",
            "HELPING_HANDS_LANGGRAPH_ENABLED",
            "HELPING_HANDS_ATOMIC_ENABLED",
            "HELPING_HANDS_CODEXCLI_ENABLED",
            "HELPING_HANDS_CLAUDECODECLI_ENABLED",
            "HELPING_HANDS_DOCKER_SANDBOX_CLAUDE_ENABLED",
            "HELPING_HANDS_GOOSE_ENABLED",
            "HELPING_HANDS_GEMINICLI_ENABLED",
            "HELPING_HANDS_OPENCODECLI_ENABLED",
            "HELPING_HANDS_DEVINCLI_ENABLED",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_GOOSE_ENABLED", "1")
        monkeypatch.setenv("HELPING_HANDS_E2E_ENABLED", "1")
        result = get_enabled_backends()
        assert set(result) == {"goose", "e2e"}


# ---------------------------------------------------------------------------
# create_hand — dispatch table
# ---------------------------------------------------------------------------


class TestCreateHand:
    """Tests for create_hand() backend dispatch."""

    def test_unknown_backend_raises(
        self, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with pytest.raises(ValueError, match=r"Unknown backend.*nonsense"):
            create_hand("nonsense", fake_config, repo_index)

    def test_error_lists_supported_backends(
        self, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with pytest.raises(ValueError, match="Supported backends"):
            create_hand("invalid", fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.ClaudeCodeHand",
        create=True,
    )
    def test_claudecodecli(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.claude.ClaudeCodeHand",
            mock_cls,
        ):
            create_hand(BACKEND_CLAUDECODECLI, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.CodexCLIHand",
        create=True,
    )
    def test_codexcli(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.codex.CodexCLIHand",
            mock_cls,
        ):
            create_hand(BACKEND_CODEXCLI, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.GooseCLIHand",
        create=True,
    )
    def test_goose(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.goose.GooseCLIHand",
            mock_cls,
        ):
            create_hand(BACKEND_GOOSE, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.GeminiCLIHand",
        create=True,
    )
    def test_geminicli(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.gemini.GeminiCLIHand",
            mock_cls,
        ):
            create_hand(BACKEND_GEMINICLI, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.OpenCodeCLIHand",
        create=True,
    )
    def test_opencodecli(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.opencode.OpenCodeCLIHand",
            mock_cls,
        ):
            create_hand(BACKEND_OPENCODECLI, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.DevinCLIHand",
        create=True,
    )
    def test_devincli(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.devin.DevinCLIHand",
            mock_cls,
        ):
            create_hand(BACKEND_DEVINCLI, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.DockerSandboxClaudeCodeHand",
        create=True,
    )
    def test_docker_sandbox_claude(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude.DockerSandboxClaudeCodeHand",
            mock_cls,
        ):
            create_hand(BACKEND_DOCKER_SANDBOX_CLAUDE, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.BasicLangGraphHand",
        create=True,
    )
    def test_basic_langgraph(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.iterative.BasicLangGraphHand",
            mock_cls,
        ):
            create_hand(BACKEND_BASIC_LANGGRAPH, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.BasicLangGraphHand",
        create=True,
    )
    def test_basic_langgraph_with_max_iterations(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.iterative.BasicLangGraphHand",
            mock_cls,
        ):
            create_hand(
                BACKEND_BASIC_LANGGRAPH,
                fake_config,
                repo_index,
                max_iterations=10,
            )
        mock_cls.assert_called_once_with(fake_config, repo_index, max_iterations=10)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.BasicAtomicHand",
        create=True,
    )
    def test_basic_atomic(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.iterative.BasicAtomicHand",
            mock_cls,
        ):
            create_hand(BACKEND_BASIC_ATOMIC, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.BasicAtomicHand",
        create=True,
    )
    def test_basic_agent_alias(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.iterative.BasicAtomicHand",
            mock_cls,
        ):
            create_hand(BACKEND_BASIC_AGENT, fake_config, repo_index)
        mock_cls.assert_called_once_with(fake_config, repo_index)

    @patch(
        "helping_hands.lib.hands.v1.hand.factory.BasicAtomicHand",
        create=True,
    )
    def test_basic_atomic_with_max_iterations(
        self, mock_cls: MagicMock, fake_config: Config, repo_index: RepoIndex
    ) -> None:
        with patch(
            "helping_hands.lib.hands.v1.hand.iterative.BasicAtomicHand",
            mock_cls,
        ):
            create_hand(
                BACKEND_BASIC_ATOMIC,
                fake_config,
                repo_index,
                max_iterations=5,
            )
        mock_cls.assert_called_once_with(fake_config, repo_index, max_iterations=5)


# ---------------------------------------------------------------------------
# Backend/env-var consistency (v368)
# ---------------------------------------------------------------------------


class TestBackendEnvVarConsistency:
    """Verify module-level consistency check between SUPPORTED_BACKENDS and env vars."""

    def test_import_succeeds(self) -> None:
        """Module imports without RuntimeError, meaning sets are in sync."""
        from helping_hands.lib.hands.v1.hand import factory  # noqa: F401

    def test_every_backend_has_env_var(self) -> None:
        """Every SUPPORTED_BACKENDS entry must have a _BACKEND_ENABLED_ENV_VARS key."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _BACKEND_ENABLED_ENV_VARS,
            SUPPORTED_BACKENDS,
        )

        assert _BACKEND_ENABLED_ENV_VARS.keys() == SUPPORTED_BACKENDS

    def test_env_var_values_are_nonempty_strings(self) -> None:
        """Every env-var value should be a non-empty string."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _BACKEND_ENABLED_ENV_VARS,
        )

        for backend, env_var in _BACKEND_ENABLED_ENV_VARS.items():
            assert isinstance(env_var, str), f"{backend} env var is not a string"
            assert env_var, f"{backend} has empty env var name"


# ---------------------------------------------------------------------------
# Mismatch error branch coverage (v373)
# ---------------------------------------------------------------------------


class TestValidateBackendEnvConsistency:
    """Cover _validate_backend_env_consistency error branches.

    The function is called at module level to catch mismatches between
    SUPPORTED_BACKENDS and _BACKEND_ENABLED_ENV_VARS.  Extracted to a
    function in v373 so error branches are directly testable.
    """

    def test_no_error_when_in_sync(self) -> None:
        """No exception when backends and env-var keys match."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _validate_backend_env_consistency,
        )

        backends = frozenset({"a", "b"})
        env_vars = {"a": "A_ENABLED", "b": "B_ENABLED"}
        _validate_backend_env_consistency(backends, env_vars)  # should not raise

    def test_missing_env_var_for_backend(self) -> None:
        """RuntimeError when a backend has no env-var entry."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _validate_backend_env_consistency,
        )

        backends = frozenset({"a", "b", "c"})
        env_vars = {"a": "A_ENABLED", "b": "B_ENABLED"}
        with pytest.raises(RuntimeError, match="backends without env vars"):
            _validate_backend_env_consistency(backends, env_vars)

    def test_extra_env_var_without_backend(self) -> None:
        """RuntimeError when an env-var has no matching backend."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _validate_backend_env_consistency,
        )

        backends = frozenset({"a"})
        env_vars = {"a": "A_ENABLED", "fake": "FAKE_ENABLED"}
        with pytest.raises(RuntimeError, match="env vars without backends"):
            _validate_backend_env_consistency(backends, env_vars)

    def test_both_missing_and_extra(self) -> None:
        """RuntimeError mentions both issues when both divergences exist."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _validate_backend_env_consistency,
        )

        backends = frozenset({"a", "missing"})
        env_vars = {"a": "A_ENABLED", "extra": "EXTRA_ENABLED"}
        with pytest.raises(RuntimeError, match="mismatch") as exc_info:
            _validate_backend_env_consistency(backends, env_vars)

        msg = str(exc_info.value)
        assert "backends without env vars" in msg
        assert "env vars without backends" in msg

    def test_empty_both_passes(self) -> None:
        """Empty sets match — no error."""
        from helping_hands.lib.hands.v1.hand.factory import (
            _validate_backend_env_consistency,
        )

        _validate_backend_env_consistency(frozenset(), {})
