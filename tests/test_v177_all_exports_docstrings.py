"""Verify that optional-extra modules declare complete and clean __all__ exports.

LangGraph, Atomic Agents, and the CLI base are optional extras installed with
separate dependency groups. Their __all__ lists are the public contract consumed
by downstream imports and by `from module import *`. If private symbols leak into
__all__ (except the intentional _LANGCHAIN_STREAM_EVENT carve-out), or if a
declared export does not actually exist in the module, any code relying on
`from helping_hands.lib.hands.v1.hand.langgraph import *` would silently pick up
internals or raise ImportError. These tests also confirm the cli/base constants
(_FAILURE_OUTPUT_TAIL_LENGTH etc.) are exported so subclasses can reference them.
"""

from __future__ import annotations

import pytest

import helping_hands.lib.hands.v1.hand.cli.base as cli_base_module

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
        # Module-level constants (e.g. _LANGCHAIN_STREAM_EVENT) are exported
        # by convention in this codebase, matching the pattern in base.py,
        # cli/base.py, etc.
        allowed_private_exports = {"_LANGCHAIN_STREAM_EVENT"}
        for name in langgraph.__all__:
            if name in allowed_private_exports:
                continue
            assert not name.startswith("_"), f"private name {name!r} in __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in langgraph.__all__:
            assert hasattr(langgraph, name), f"{name!r} not found in module"


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
        ]
        for name in expected:
            assert name in cli_base_module.__all__, f"{name!r} missing from __all__"

    def test_all_symbols_are_importable(self) -> None:
        for name in cli_base_module.__all__:
            assert hasattr(cli_base_module, name), f"{name!r} not found in module"
