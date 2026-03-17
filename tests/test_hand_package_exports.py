"""Tests for helping_hands.lib.hands.v1.hand package-level re-exports."""

from __future__ import annotations

import subprocess as stdlib_subprocess

from helping_hands.lib.hands.v1.hand import (
    AtomicHand,
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
    LangGraphHand,
    OpenCodeCLIHand,
    __all__,
    subprocess,
)


class TestHandPackageAll:
    """Verify __all__ lists every public re-export."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {
            "SUPPORTED_BACKENDS",
            "AtomicHand",
            "BasicAtomicHand",
            "BasicLangGraphHand",
            "ClaudeCodeHand",
            "CodexCLIHand",
            "DockerSandboxClaudeCodeHand",
            "E2EHand",
            "GeminiCLIHand",
            "GooseCLIHand",
            "Hand",
            "HandResponse",
            "LangGraphHand",
            "OpenCodeCLIHand",
            "create_hand",
        }
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        import helping_hands.lib.hands.v1.hand as pkg

        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestHandPackageIdentity:
    """Verify re-exported symbols match their source modules."""

    def test_hand_is_base_hand(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import Hand as BaseHand

        assert Hand is BaseHand

    def test_hand_response_is_base_hand_response(self) -> None:
        from helping_hands.lib.hands.v1.hand.base import (
            HandResponse as BaseHandResponse,
        )

        assert HandResponse is BaseHandResponse

    def test_e2e_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand as SrcE2E

        assert E2EHand is SrcE2E

    def test_langgraph_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.langgraph import (
            LangGraphHand as SrcLG,
        )

        assert LangGraphHand is SrcLG

    def test_atomic_hand_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.atomic import (
            AtomicHand as SrcAtomic,
        )

        assert AtomicHand is SrcAtomic

    def test_iterative_basic_langgraph_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            BasicLangGraphHand as SrcBLG,
        )

        assert BasicLangGraphHand is SrcBLG

    def test_iterative_basic_atomic_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            BasicAtomicHand as SrcBA,
        )

        assert BasicAtomicHand is SrcBA

    def test_cli_hand_identities(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import (
            ClaudeCodeHand as SrcClaude,
        )
        from helping_hands.lib.hands.v1.hand.cli import (
            CodexCLIHand as SrcCodex,
        )
        from helping_hands.lib.hands.v1.hand.cli import (
            DockerSandboxClaudeCodeHand as SrcDocker,
        )
        from helping_hands.lib.hands.v1.hand.cli import (
            GeminiCLIHand as SrcGemini,
        )
        from helping_hands.lib.hands.v1.hand.cli import (
            GooseCLIHand as SrcGoose,
        )
        from helping_hands.lib.hands.v1.hand.cli import (
            OpenCodeCLIHand as SrcOpenCode,
        )

        assert ClaudeCodeHand is SrcClaude
        assert CodexCLIHand is SrcCodex
        assert DockerSandboxClaudeCodeHand is SrcDocker
        assert GeminiCLIHand is SrcGemini
        assert GooseCLIHand is SrcGoose
        assert OpenCodeCLIHand is SrcOpenCode


class TestSubprocessAlias:
    """The package re-exports subprocess from base for backward-compat patching."""

    def test_subprocess_is_stdlib_subprocess(self) -> None:
        assert subprocess is stdlib_subprocess

    def test_subprocess_matches_base_module_reference(self) -> None:
        from helping_hands.lib.hands.v1.hand import base as _base_module

        assert subprocess is _base_module.subprocess
