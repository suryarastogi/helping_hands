"""Smoke tests: every Hand backend constructs and exposes the public API surface.

Guards against wiring regressions when new hands are added or the base class
evolves: if any concrete hand fails to construct from (Config, RepoIndex), or
loses run()/stream()/interrupt()/auto_pr/fix_ci, the CLI and server will crash
at dispatch time with no prior signal. Also validates that HandResponse uses
per-instance metadata dicts (not a shared default) -- a mutable-default-arg bug
would cause cross-talk between concurrent server responses.
"""

from __future__ import annotations

import importlib.util

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand import (
    BasicAtomicHand,
    BasicLangGraphHand,
    ClaudeCodeHand,
    CodexCLIHand,
    DockerSandboxClaudeCodeHand,
    E2EHand,
    GeminiCLIHand,
    GooseCLIHand,
    Hand,
    HandResponse,
    OpenCodeCLIHand,
)
from helping_hands.lib.repo import RepoIndex

_langgraph_available = importlib.util.find_spec("langgraph") is not None
_atomic_available = importlib.util.find_spec("atomic_agents") is not None


# All concrete Hand subclasses that can be constructed with (Config, RepoIndex).
_CONCRETE_HANDS: list[type[Hand]] = [
    E2EHand,
    ClaudeCodeHand,
    CodexCLIHand,
    DockerSandboxClaudeCodeHand,
    GeminiCLIHand,
    GooseCLIHand,
    OpenCodeCLIHand,
]


class TestHandInstantiation:
    """Every concrete hand can be constructed with minimal Config + RepoIndex."""

    @pytest.fixture()
    def _hand_deps(self, tmp_path):
        (tmp_path / "README.md").write_text("# test")
        config = Config(repo=str(tmp_path), model="test-model")
        ri = RepoIndex.from_path(tmp_path)
        return config, ri

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_constructs_with_config_and_repo_index(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert isinstance(hand, Hand)

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_has_auto_pr_attribute(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert hasattr(hand, "auto_pr")

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_has_interrupt_event(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert hasattr(hand, "_interrupt_event")

    @pytest.mark.skipif(
        not _langgraph_available, reason="langgraph extras not installed"
    )
    def test_basic_langgraph_hand(self, _hand_deps, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")
        config, ri = _hand_deps
        hand = BasicLangGraphHand(config=config, repo_index=ri)
        assert isinstance(hand, Hand)

    @pytest.mark.skipif(
        not _atomic_available, reason="atomic_agents extras not installed"
    )
    def test_basic_atomic_hand(self, _hand_deps, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")
        config, ri = _hand_deps
        hand = BasicAtomicHand(config=config, repo_index=ri)
        assert isinstance(hand, Hand)

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_has_run_method(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert callable(getattr(hand, "run", None))

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_has_stream_method(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert callable(getattr(hand, "stream", None))

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_has_interrupt_method(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert callable(getattr(hand, "interrupt", None))

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_default_auto_pr_is_true(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert hand.auto_pr is True

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_default_fix_ci_is_false(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert hand.fix_ci is False

    @pytest.mark.parametrize(
        "hand_cls",
        _CONCRETE_HANDS,
        ids=[c.__name__ for c in _CONCRETE_HANDS],
    )
    def test_default_last_pr_metadata_is_empty_dict(self, hand_cls, _hand_deps) -> None:
        config, ri = _hand_deps
        hand = hand_cls(config=config, repo_index=ri)
        assert hand.last_pr_metadata == {}


class TestHandResponseConstruction:
    """HandResponse dataclass construction tests."""

    # TODO: CLEANUP CANDIDATE — test_equality, test_inequality, test_repr_contains_message
    # just exercise auto-generated dataclass methods; they protect no custom logic.

    def test_minimal_construction(self) -> None:
        resp = HandResponse(message="done")
        assert resp.message == "done"
        assert resp.metadata == {}

    def test_with_metadata(self) -> None:
        resp = HandResponse(message="ok", metadata={"pr_url": "https://x"})
        assert resp.metadata["pr_url"] == "https://x"

    def test_equality(self) -> None:
        a = HandResponse(message="x", metadata={"k": 1})
        b = HandResponse(message="x", metadata={"k": 1})
        assert a == b

    def test_inequality(self) -> None:
        a = HandResponse(message="x")
        b = HandResponse(message="y")
        assert a != b

    def test_default_metadata_is_independent(self) -> None:
        """Each instance gets its own metadata dict."""
        a = HandResponse(message="x")
        b = HandResponse(message="y")
        a.metadata["key"] = "value"
        assert "key" not in b.metadata

    def test_repr_contains_message(self) -> None:
        resp = HandResponse(message="done")
        assert "done" in repr(resp)

    def test_metadata_default_is_dict(self) -> None:
        resp = HandResponse(message="test")
        assert isinstance(resp.metadata, dict)
