"""Tests for hand factory module (v250).

Covers backend name constants, SUPPORTED_BACKENDS frozenset, and the
create_hand() factory function.
"""

from __future__ import annotations

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_BASIC_AGENT,
    BACKEND_BASIC_ATOMIC,
    BACKEND_BASIC_LANGGRAPH,
    BACKEND_CLAUDECODECLI,
    BACKEND_CODEXCLI,
    BACKEND_DOCKER_SANDBOX_CLAUDE,
    BACKEND_E2E,
    BACKEND_GEMINICLI,
    BACKEND_GOOSE,
    BACKEND_OPENCODECLI,
    SUPPORTED_BACKENDS,
    create_hand,
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
        }
        assert expected == SUPPORTED_BACKENDS

    def test_count(self) -> None:
        assert len(SUPPORTED_BACKENDS) == 10

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

    def test_basic_atomic(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        hand = create_hand(BACKEND_BASIC_ATOMIC, _config, _repo_index)
        assert isinstance(hand, BasicAtomicHand)

    def test_basic_agent_alias(self, _config: Config, _repo_index: RepoIndex) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand

        hand = create_hand(BACKEND_BASIC_AGENT, _config, _repo_index)
        assert isinstance(hand, BasicAtomicHand)

    def test_basic_atomic_max_iterations(
        self, _config: Config, _repo_index: RepoIndex
    ) -> None:
        hand = create_hand(BACKEND_BASIC_ATOMIC, _config, _repo_index, max_iterations=5)
        assert hand.max_iterations == 5


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
