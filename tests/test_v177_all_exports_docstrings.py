"""Tests for v177 — __all__ exports and docstrings for langgraph/atomic/cli-base."""

from __future__ import annotations

import pytest

import helping_hands.lib.hands.v1.hand.cli.base as cli_base_module

# ---------------------------------------------------------------------------
# langgraph.py __all__
# ---------------------------------------------------------------------------

langgraph = pytest.importorskip(
    "helping_hands.lib.hands.v1.hand.langgraph",
    reason="langchain extra not installed",
)


class TestLangGraphModuleAll:
    def test_all_exists(self) -> None:
        assert hasattr(langgraph, "__all__")

    def test_all_contains_langgraph_hand(self) -> None:
        assert "LangGraphHand" in langgraph.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in langgraph.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in langgraph.__all__:
            assert hasattr(langgraph, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# atomic.py __all__
# ---------------------------------------------------------------------------

atomic = pytest.importorskip(
    "helping_hands.lib.hands.v1.hand.atomic",
    reason="atomic extra not installed",
)


class TestAtomicModuleAll:
    def test_all_exists(self) -> None:
        assert hasattr(atomic, "__all__")

    def test_all_contains_atomic_hand(self) -> None:
        assert "AtomicHand" in atomic.__all__

    def test_all_does_not_contain_private_names(self) -> None:
        for name in atomic.__all__:
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in atomic.__all__:
            assert hasattr(atomic, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# cli/base.py __all__
# ---------------------------------------------------------------------------


class TestCLIBaseModuleAll:
    def test_all_exists(self) -> None:
        assert hasattr(cli_base_module, "__all__")

    def test_all_contains_two_phase_cli_hand(self) -> None:
        assert "_TwoPhaseCLIHand" in cli_base_module.__all__

    def test_all_contains_constants(self) -> None:
        expected = [
            "_AUTH_ERROR_TOKENS",
            "_PROCESS_TERMINATE_TIMEOUT_S",
            "_CI_POLL_INTERVAL_S",
            "_PR_DESCRIPTION_TIMEOUT_S",
            "_APPLY_CHANGES_TRUNCATION_LIMIT",
            "_STREAM_READ_BUFFER_SIZE",
            "_HOOK_ERROR_TRUNCATION_LIMIT",
            "_GIT_REF_DISPLAY_LENGTH",
            "_FAILURE_OUTPUT_TAIL_LENGTH",
            "_CLI_TRUTHY_VALUES",
        ]
        for name in expected:
            assert name in cli_base_module.__all__, f"{name!r} missing from __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in cli_base_module.__all__:
            assert hasattr(cli_base_module, name), f"{name!r} not found in module"


# ---------------------------------------------------------------------------
# LangGraphHand.stream docstring
# ---------------------------------------------------------------------------


class TestLangGraphStreamDocstring:
    def test_stream_has_docstring(self) -> None:
        assert langgraph.LangGraphHand.stream.__doc__ is not None

    def test_stream_docstring_mentions_args(self) -> None:
        assert "Args:" in langgraph.LangGraphHand.stream.__doc__

    def test_stream_docstring_mentions_yields(self) -> None:
        assert "Yields:" in langgraph.LangGraphHand.stream.__doc__

    def test_stream_docstring_not_trivial(self) -> None:
        assert len(langgraph.LangGraphHand.stream.__doc__) > 50


# ---------------------------------------------------------------------------
# AtomicHand.__init__ docstring
# ---------------------------------------------------------------------------


class TestAtomicInitDocstring:
    def test_init_has_docstring(self) -> None:
        assert atomic.AtomicHand.__init__.__doc__ is not None

    def test_init_docstring_mentions_args(self) -> None:
        assert "Args:" in atomic.AtomicHand.__init__.__doc__

    def test_init_docstring_mentions_config(self) -> None:
        assert "config" in atomic.AtomicHand.__init__.__doc__

    def test_init_docstring_not_trivial(self) -> None:
        assert len(atomic.AtomicHand.__init__.__doc__) > 50


# ---------------------------------------------------------------------------
# AtomicHand.run docstring
# ---------------------------------------------------------------------------


class TestAtomicRunDocstring:
    def test_run_has_docstring(self) -> None:
        assert atomic.AtomicHand.run.__doc__ is not None

    def test_run_docstring_mentions_args(self) -> None:
        assert "Args:" in atomic.AtomicHand.run.__doc__

    def test_run_docstring_mentions_returns(self) -> None:
        assert "Returns:" in atomic.AtomicHand.run.__doc__

    def test_run_docstring_not_trivial(self) -> None:
        assert len(atomic.AtomicHand.run.__doc__) > 50


# ---------------------------------------------------------------------------
# AtomicHand.stream docstring
# ---------------------------------------------------------------------------


class TestAtomicStreamDocstring:
    def test_stream_has_docstring(self) -> None:
        assert atomic.AtomicHand.stream.__doc__ is not None

    def test_stream_docstring_mentions_args(self) -> None:
        assert "Args:" in atomic.AtomicHand.stream.__doc__

    def test_stream_docstring_mentions_yields(self) -> None:
        assert "Yields:" in atomic.AtomicHand.stream.__doc__

    def test_stream_docstring_not_trivial(self) -> None:
        assert len(atomic.AtomicHand.stream.__doc__) > 50
