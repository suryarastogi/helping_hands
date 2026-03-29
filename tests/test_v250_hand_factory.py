"""Tests for the hand factory module introduced in v250.

create_hand() is the single entry point that maps a backend name string to a
Hand subclass instance. If a backend constant value drifts (e.g. "langgraph"
becomes "basic-langgraph"), the factory raises ValueError for every caller that
uses the old string, breaking the CLI, server, and Celery worker simultaneously.

SUPPORTED_BACKENDS is the authoritative list used for input validation; if a
new hand is added to the factory switch without adding its constant to this
frozenset, the validation layer rejects it before the factory is ever called.

The unknown-backend test ensures the factory raises ValueError with a message
that names the bad input, rather than returning None or raising AttributeError.
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
    create_hand,
    get_enabled_backends,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _config(tmp_path: object) -> Config:
    return Config.from_env(overrides={"repo": str(tmp_path)})


@pytest.fixture()
def _repo_index(tmp_path: object) -> RepoIndex:
    from pathlib import Path

    return RepoIndex(root=Path(str(tmp_path)), files=[])


# ---------------------------------------------------------------------------
# Backend name constants — value correctness
# ---------------------------------------------------------------------------


class TestBackendNameConstants:
    def test_e2e_value(self) -> None:
        assert BACKEND_E2E == "e2e"

    def test_basic_langgraph_value(self) -> None:
        assert BACKEND_BASIC_LANGGRAPH == "basic-langgraph"

    def test_basic_atomic_value(self) -> None:
        assert BACKEND_BASIC_ATOMIC == "basic-atomic"

    def test_basic_agent_value(self) -> None:
        assert BACKEND_BASIC_AGENT == "basic-agent"

    def test_codexcli_value(self) -> None:
        assert BACKEND_CODEXCLI == "codexcli"

    def test_claudecodecli_value(self) -> None:
        assert BACKEND_CLAUDECODECLI == "claudecodecli"

    def test_docker_sandbox_claude_value(self) -> None:
        assert BACKEND_DOCKER_SANDBOX_CLAUDE == "docker-sandbox-claude"

    def test_goose_value(self) -> None:
        assert BACKEND_GOOSE == "goose"

    def test_geminicli_value(self) -> None:
        assert BACKEND_GEMINICLI == "geminicli"

    def test_opencodecli_value(self) -> None:
        assert BACKEND_OPENCODECLI == "opencodecli"

    def test_devincli_value(self) -> None:
        assert BACKEND_DEVINCLI == "devincli"


# ---------------------------------------------------------------------------
# SUPPORTED_BACKENDS frozenset
# ---------------------------------------------------------------------------


class TestSupportedBackends:
    def test_is_frozenset(self) -> None:
        assert isinstance(SUPPORTED_BACKENDS, frozenset)

    def test_contains_all_constants(self) -> None:
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

    def test_all_strings(self) -> None:
        for name in SUPPORTED_BACKENDS:
            assert isinstance(name, str)

    def test_no_empty_strings(self) -> None:
        for name in SUPPORTED_BACKENDS:
            assert name.strip() != ""

    def test_names_are_unique(self) -> None:
        names = list(SUPPORTED_BACKENDS)
        assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# create_hand — returns correct Hand subclass for each backend
# ---------------------------------------------------------------------------


class TestCreateHandCLIBackends:
    """CLI-backed hands that don't require optional extras."""

    def test_codexcli(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        hand = create_hand(BACKEND_CODEXCLI, _config, _repo_index)
        assert isinstance(hand, CodexCLIHand)

    def test_claudecodecli(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        hand = create_hand(BACKEND_CLAUDECODECLI, _config, _repo_index)
        assert isinstance(hand, ClaudeCodeHand)

    def test_docker_sandbox_claude(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        hand = create_hand(BACKEND_DOCKER_SANDBOX_CLAUDE, _config, _repo_index)
        assert isinstance(hand, DockerSandboxClaudeCodeHand)

    def test_goose(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

        hand = create_hand(BACKEND_GOOSE, _config, _repo_index)
        assert isinstance(hand, GooseCLIHand)

    def test_geminicli(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand

        hand = create_hand(BACKEND_GEMINICLI, _config, _repo_index)
        assert isinstance(hand, GeminiCLIHand)

    def test_opencodecli(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        hand = create_hand(BACKEND_OPENCODECLI, _config, _repo_index)
        assert isinstance(hand, OpenCodeCLIHand)

    def test_devincli(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

        hand = create_hand(BACKEND_DEVINCLI, _config, _repo_index)
        assert isinstance(hand, DevinCLIHand)


class TestCreateHandIterativeBackends:
    """Iterative hands that require langchain/atomic extras."""

    @pytest.fixture(autouse=True)
    def _skip_without_langchain(self) -> None:
        pytest.importorskip("langchain_openai", reason="langchain extra not installed")

    def test_basic_langgraph(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicLangGraphHand

        hand = create_hand(BACKEND_BASIC_LANGGRAPH, _config, _repo_index)
        assert isinstance(hand, BasicLangGraphHand)

    def test_basic_langgraph_max_iterations(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        hand = create_hand(
            BACKEND_BASIC_LANGGRAPH, _config, _repo_index, max_iterations=10
        )
        assert hand.max_iterations == 10


class TestCreateHandAtomicBackends:
    @pytest.fixture(autouse=True)
    def _skip_without_atomic(self) -> None:
        pytest.importorskip("atomic_agents", reason="atomic extra not installed")

    @pytest.fixture()
    def _openai_config(self, tmp_path: object) -> Config:
        """Config with an OpenAI-compatible model (atomic requires it)."""
        return Config.from_env(overrides={"repo": str(tmp_path), "model": "gpt-4o"})

    def test_basic_atomic(self, _openai_config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        hand = create_hand(BACKEND_BASIC_ATOMIC, _openai_config, _repo_index)
        assert isinstance(hand, BasicAtomicHand)

    def test_basic_agent_alias(
        self, _openai_config: Config, _repo_index: RepoIndex
    ) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        hand = create_hand(BACKEND_BASIC_AGENT, _openai_config, _repo_index)
        assert isinstance(hand, BasicAtomicHand)

    def test_basic_atomic_max_iterations(
        self, _openai_config: Config, _repo_index: RepoIndex
    ) -> None:
        hand = create_hand(
            BACKEND_BASIC_ATOMIC, _openai_config, _repo_index, max_iterations=5
        )
        assert hand.max_iterations == 5


# ---------------------------------------------------------------------------
# create_hand — mock-based tests (cover paths even without optional extras)
# ---------------------------------------------------------------------------


class TestCreateHandLangGraphMocked:
    """Mock-based tests that always run, covering factory.py lines 106-111."""

    @pytest.fixture(autouse=True)
    def _remove_iterative_cache(self) -> None:
        """Ensure the iterative module isn't cached so the mock takes effect."""
        import sys

        key = "helping_hands.lib.hands.v1.hand.iterative"
        saved = sys.modules.pop(key, None)
        yield  # type: ignore[misc]
        if saved is not None:
            sys.modules[key] = saved
        else:
            sys.modules.pop(key, None)

    def test_langgraph_path_calls_constructor(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()
        mock_hand = MagicMock()
        mock_cls.return_value = mock_hand

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicLangGraphHand=mock_cls
                )
            },
        ):
            result = create_hand(BACKEND_BASIC_LANGGRAPH, _config, _repo_index)

        assert result is mock_hand
        mock_cls.assert_called_once_with(_config, _repo_index)

    def test_langgraph_path_forwards_max_iterations(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()
        mock_hand = MagicMock()
        mock_cls.return_value = mock_hand

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicLangGraphHand=mock_cls
                )
            },
        ):
            result = create_hand(
                BACKEND_BASIC_LANGGRAPH,
                _config,
                _repo_index,
                max_iterations=15,
            )

        assert result is mock_hand
        mock_cls.assert_called_once_with(_config, _repo_index, max_iterations=15)

    def test_langgraph_path_no_max_iterations_omits_kwarg(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicLangGraphHand=mock_cls
                )
            },
        ):
            create_hand(BACKEND_BASIC_LANGGRAPH, _config, _repo_index)

        # max_iterations should NOT be in kwargs when None
        _, kwargs = mock_cls.call_args
        assert "max_iterations" not in kwargs


class TestCreateHandAtomicMocked:
    """Mock-based tests that always run, covering factory.py lines 146-151."""

    @pytest.fixture(autouse=True)
    def _remove_iterative_cache(self) -> None:
        """Ensure the iterative module isn't cached so the mock takes effect."""
        import sys

        key = "helping_hands.lib.hands.v1.hand.iterative"
        saved = sys.modules.pop(key, None)
        yield  # type: ignore[misc]
        if saved is not None:
            sys.modules[key] = saved
        else:
            sys.modules.pop(key, None)

    def test_atomic_path_calls_constructor(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()
        mock_hand = MagicMock()
        mock_cls.return_value = mock_hand

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicAtomicHand=mock_cls
                )
            },
        ):
            result = create_hand(BACKEND_BASIC_ATOMIC, _config, _repo_index)

        assert result is mock_hand
        mock_cls.assert_called_once_with(_config, _repo_index)

    def test_agent_alias_path_calls_atomic_constructor(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()
        mock_hand = MagicMock()
        mock_cls.return_value = mock_hand

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicAtomicHand=mock_cls
                )
            },
        ):
            result = create_hand(BACKEND_BASIC_AGENT, _config, _repo_index)

        assert result is mock_hand
        mock_cls.assert_called_once_with(_config, _repo_index)

    def test_atomic_path_forwards_max_iterations(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()
        mock_hand = MagicMock()
        mock_cls.return_value = mock_hand

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicAtomicHand=mock_cls
                )
            },
        ):
            result = create_hand(
                BACKEND_BASIC_ATOMIC,
                _config,
                _repo_index,
                max_iterations=7,
            )

        assert result is mock_hand
        mock_cls.assert_called_once_with(_config, _repo_index, max_iterations=7)

    def test_atomic_path_no_max_iterations_omits_kwarg(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        mock_cls = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "helping_hands.lib.hands.v1.hand.iterative": MagicMock(
                    BasicAtomicHand=mock_cls
                )
            },
        ):
            create_hand(BACKEND_BASIC_ATOMIC, _config, _repo_index)

        _, kwargs = mock_cls.call_args
        assert "max_iterations" not in kwargs


# ---------------------------------------------------------------------------
# create_hand — error cases
# ---------------------------------------------------------------------------


class TestCreateHandErrors:
    def test_unknown_backend_raises_value_error(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        with pytest.raises(ValueError, match=r"Unknown backend.*'nonsense'"):
            create_hand("nonsense", _config, _repo_index)

    def test_e2e_backend_raises_value_error(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        """E2E has a separate workflow and is not handled by create_hand."""
        with pytest.raises(ValueError, match=r"Unknown backend.*'e2e'"):
            create_hand(BACKEND_E2E, _config, _repo_index)

    def test_empty_backend_raises_value_error(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        with pytest.raises(ValueError, match="Unknown backend"):
            create_hand("", _config, _repo_index)

    def test_error_message_includes_supported_backends(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        with pytest.raises(ValueError, match="Supported backends:"):
            create_hand("invalid", _config, _repo_index)


# ---------------------------------------------------------------------------
# __all__ exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_all_contains_create_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand import factory

        assert "create_hand" in factory.__all__

    def test_all_contains_supported_backends(self) -> None:
        from helping_hands.lib.hands.v1.hand import factory

        assert "SUPPORTED_BACKENDS" in factory.__all__

    def test_all_contains_all_backend_constants(self) -> None:
        from helping_hands.lib.hands.v1.hand import factory

        for name in dir(factory):
            if name.startswith("BACKEND_"):
                assert name in factory.__all__, f"{name} missing from __all__"

    def test_hand_package_reexports_create_hand(self) -> None:
        from helping_hands.lib.hands.v1 import hand as hand_pkg

        assert hasattr(hand_pkg, "create_hand")
        assert hand_pkg.create_hand is create_hand

    def test_hand_package_reexports_supported_backends(self) -> None:
        from helping_hands.lib.hands.v1 import hand as hand_pkg

        assert hasattr(hand_pkg, "SUPPORTED_BACKENDS")
        assert hand_pkg.SUPPORTED_BACKENDS is SUPPORTED_BACKENDS


# ---------------------------------------------------------------------------
# Integration: constants match server/constants DEFAULT_BACKEND
# ---------------------------------------------------------------------------


class TestConstantsIntegration:
    def test_default_backend_uses_factory_constant(self) -> None:
        from helping_hands.server.constants import DEFAULT_BACKEND

        assert DEFAULT_BACKEND == BACKEND_CLAUDECODECLI

    def test_default_backend_in_supported(self) -> None:
        from helping_hands.server.constants import DEFAULT_BACKEND

        assert DEFAULT_BACKEND in SUPPORTED_BACKENDS

    def test_app_backend_lookup_keys_use_constants(self) -> None:
        pytest.importorskip("fastapi", reason="server extra not installed")
        from helping_hands.server.app import _BACKEND_LOOKUP

        for key in _BACKEND_LOOKUP:
            assert key in SUPPORTED_BACKENDS, (
                f"_BACKEND_LOOKUP key {key!r} not in SUPPORTED_BACKENDS"
            )

    def test_app_backend_lookup_keys_match_supported(self) -> None:
        pytest.importorskip("fastapi", reason="server extra not installed")
        from helping_hands.server.app import _BACKEND_LOOKUP

        assert set(_BACKEND_LOOKUP.keys()) == SUPPORTED_BACKENDS

    def test_mcp_build_feature_default_uses_constant(self) -> None:
        pytest.importorskip("mcp", reason="mcp extra not installed")
        import inspect

        from helping_hands.server.mcp_server import build_feature

        sig = inspect.signature(build_feature)
        default = sig.parameters["backend"].default
        assert default == BACKEND_CODEXCLI
        assert default in SUPPORTED_BACKENDS


# ---------------------------------------------------------------------------
# get_enabled_backends
# ---------------------------------------------------------------------------


class TestGetEnabledBackends:
    def test_no_env_vars_returns_all(self, monkeypatch) -> None:
        """When no *_ENABLED env vars are set, all backends are returned."""
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        result = get_enabled_backends()
        assert set(result) == SUPPORTED_BACKENDS

    def test_returns_sorted(self, monkeypatch) -> None:
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        result = get_enabled_backends()
        assert result == sorted(result)

    def test_single_enabled(self, monkeypatch) -> None:
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "1")
        result = get_enabled_backends()
        assert result == ["codexcli"]

    def test_multiple_enabled(self, monkeypatch) -> None:
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "true")
        monkeypatch.setenv("HELPING_HANDS_GOOSE_ENABLED", "yes")
        result = get_enabled_backends()
        assert result == ["codexcli", "goose"]

    def test_falsy_value_disables(self, monkeypatch) -> None:
        """A non-empty but non-truthy value means 'has_any' is True but backend not enabled."""
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "0")
        result = get_enabled_backends()
        assert result == []

    def test_mixed_truthy_and_falsy(self, monkeypatch) -> None:
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "1")
        monkeypatch.setenv("HELPING_HANDS_GOOSE_ENABLED", "false")
        result = get_enabled_backends()
        assert result == ["codexcli"]

    def test_truthy_values_on_and_yes(self, monkeypatch) -> None:
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CLAUDECODECLI_ENABLED", "on")
        monkeypatch.setenv("HELPING_HANDS_GEMINICLI_ENABLED", "YES")
        result = get_enabled_backends()
        assert set(result) == {"claudecodecli", "geminicli"}

    def test_whitespace_only_ignored(self, monkeypatch) -> None:
        """Whitespace-only env var is treated as unset."""
        from helping_hands.lib.hands.v1.hand.factory import _BACKEND_ENABLED_ENV_VARS

        for env_var in _BACKEND_ENABLED_ENV_VARS.values():
            monkeypatch.delenv(env_var, raising=False)
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "  ")
        result = get_enabled_backends()
        # whitespace-only -> strip -> empty -> not counted as has_any
        assert set(result) == SUPPORTED_BACKENDS
