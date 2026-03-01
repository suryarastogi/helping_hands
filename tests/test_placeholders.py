"""Tests for helping_hands.lib.hands.v1.hand.placeholders backward-compat shim."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path


def test_re_exports_cli_hand_classes() -> None:
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


def test_backward_compat_stdlib_symbols() -> None:
    from helping_hands.lib.hands.v1.hand import placeholders

    assert placeholders.asyncio is asyncio
    assert placeholders.os is os
    assert placeholders.shutil is shutil
    assert placeholders.Path is Path


def test_all_contains_expected_names() -> None:
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


def test_classes_match_canonical_imports() -> None:
    from helping_hands.lib.hands.v1.hand.cli.claude import (
        ClaudeCodeHand as CanonicalClaude,
    )
    from helping_hands.lib.hands.v1.hand.cli.codex import (
        CodexCLIHand as CanonicalCodex,
    )
    from helping_hands.lib.hands.v1.hand.cli.gemini import (
        GeminiCLIHand as CanonicalGemini,
    )
    from helping_hands.lib.hands.v1.hand.cli.goose import (
        GooseCLIHand as CanonicalGoose,
    )
    from helping_hands.lib.hands.v1.hand.placeholders import (
        ClaudeCodeHand,
        CodexCLIHand,
        GeminiCLIHand,
        GooseCLIHand,
    )

    assert ClaudeCodeHand is CanonicalClaude
    assert CodexCLIHand is CanonicalCodex
    assert GeminiCLIHand is CanonicalGemini
    assert GooseCLIHand is CanonicalGoose
