"""Tests for helping_hands.lib.hands.v1.hand.cli package-level re-exports."""

from __future__ import annotations

import helping_hands.lib.hands.v1.hand.cli as pkg
from helping_hands.lib.hands.v1.hand.cli import (
    ClaudeCodeHand,
    CodexCLIHand,
    DockerSandboxClaudeCodeHand,
    GeminiCLIHand,
    GooseCLIHand,
    OpenCodeCLIHand,
    __all__,
)


class TestCLIPackageAll:
    """Verify __all__ lists every public re-export."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {
            "ClaudeCodeHand",
            "CodexCLIHand",
            "DockerSandboxClaudeCodeHand",
            "GeminiCLIHand",
            "GooseCLIHand",
            "OpenCodeCLIHand",
        }
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestCLIPackageIdentity:
    """Verify re-exported symbols match their source modules."""

    def test_claude_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            ClaudeCodeHand as Src,
        )

        assert ClaudeCodeHand is Src

    def test_codex_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import (
            CodexCLIHand as Src,
        )

        assert CodexCLIHand is Src

    def test_docker_sandbox_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand as Src,
        )

        assert DockerSandboxClaudeCodeHand is Src

    def test_gemini_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.gemini import (
            GeminiCLIHand as Src,
        )

        assert GeminiCLIHand is Src

    def test_goose_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            GooseCLIHand as Src,
        )

        assert GooseCLIHand is Src

    def test_opencode_identity(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import (
            OpenCodeCLIHand as Src,
        )

        assert OpenCodeCLIHand is Src
