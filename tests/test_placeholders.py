"""Tests for helping_hands.lib.hands.v1.hand.placeholders backward-compat shim."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path


class TestPlaceholdersReexports:
    """All expected symbols are re-exported from the shim module."""

    def test_class_reexports(self) -> None:
        from helping_hands.lib.hands.v1.hand.placeholders import (
            ClaudeCodeHand,
            CodexCLIHand,
            GeminiCLIHand,
            GooseCLIHand,
            _TwoPhaseCLIHand,
        )

        assert ClaudeCodeHand is not None
        assert CodexCLIHand is not None
        assert GeminiCLIHand is not None
        assert GooseCLIHand is not None
        assert _TwoPhaseCLIHand is not None

    def test_module_aliases(self) -> None:
        from helping_hands.lib.hands.v1.hand import placeholders

        assert placeholders.asyncio is asyncio
        assert placeholders.os is os
        assert placeholders.shutil is shutil
        assert placeholders.Path is Path

    def test_all_contains_expected_names(self) -> None:
        from helping_hands.lib.hands.v1.hand.placeholders import __all__

        expected = {
            "ClaudeCodeHand",
            "CodexCLIHand",
            "GeminiCLIHand",
            "GooseCLIHand",
            "Path",
            "_TwoPhaseCLIHand",
            "asyncio",
            "os",
            "shutil",
        }
        assert set(__all__) == expected

    def test_classes_resolve_to_correct_origins(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import (
            ClaudeCodeHand as OrigClaude,
        )
        from helping_hands.lib.hands.v1.hand.cli.codex import (
            CodexCLIHand as OrigCodex,
        )
        from helping_hands.lib.hands.v1.hand.cli.gemini import (
            GeminiCLIHand as OrigGemini,
        )
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            GooseCLIHand as OrigGoose,
        )
        from helping_hands.lib.hands.v1.hand.placeholders import (
            ClaudeCodeHand,
            CodexCLIHand,
            GeminiCLIHand,
            GooseCLIHand,
        )

        assert ClaudeCodeHand is OrigClaude
        assert CodexCLIHand is OrigCodex
        assert GeminiCLIHand is OrigGemini
        assert GooseCLIHand is OrigGoose
