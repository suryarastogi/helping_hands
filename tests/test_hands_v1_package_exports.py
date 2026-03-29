"""Tests for helping_hands.lib.hands.v1 package-level re-exports.

Guards the stable public import path at the hands/v1 layer. All Hand subclasses
must be importable from helping_hands.lib.hands.v1 and must be the same objects
as those exported from the inner hand package. If the v1 __init__ is not kept
in sync when classes move between submodules, external callers using the v1
path would receive import errors or stale references without any runtime warning.
"""

from __future__ import annotations

import helping_hands.lib.hands.v1 as pkg
from helping_hands.lib.hands.v1 import (
    AtomicHand,
    BasicAtomicHand,
    BasicLangGraphHand,
    ClaudeCodeHand,
    CodexCLIHand,
    E2EHand,
    GeminiCLIHand,
    Hand,
    HandResponse,
    LangGraphHand,
    __all__,
)


class TestHandsV1PackageAll:
    """Verify __all__ lists every public re-export."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {
            "AtomicHand",
            "BasicAtomicHand",
            "BasicLangGraphHand",
            "ClaudeCodeHand",
            "CodexCLIHand",
            "E2EHand",
            "GeminiCLIHand",
            "Hand",
            "HandResponse",
            "LangGraphHand",
        }
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestHandsV1PackageIdentity:
    """Verify re-exported symbols match their source in the hand package."""

    def test_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import Hand as Src

        assert Hand is Src

    def test_hand_response_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import HandResponse as Src

        assert HandResponse is Src

    def test_e2e_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import E2EHand as Src

        assert E2EHand is Src

    def test_langgraph_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import LangGraphHand as Src

        assert LangGraphHand is Src

    def test_atomic_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import AtomicHand as Src

        assert AtomicHand is Src

    def test_basic_langgraph_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import BasicLangGraphHand as Src

        assert BasicLangGraphHand is Src

    def test_basic_atomic_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import BasicAtomicHand as Src

        assert BasicAtomicHand is Src

    def test_claude_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import ClaudeCodeHand as Src

        assert ClaudeCodeHand is Src

    def test_codex_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import CodexCLIHand as Src

        assert CodexCLIHand is Src

    def test_gemini_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand import GeminiCLIHand as Src

        assert GeminiCLIHand is Src
