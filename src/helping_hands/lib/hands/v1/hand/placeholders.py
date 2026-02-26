"""Backward-compatible shim for CLI hand modules.

CLI-backed hand implementations have moved to ``hand.cli`` modules. This file
re-exports the same classes and keeps module-level symbols used by legacy
patch targets in tests/external integrations.
"""

from __future__ import annotations

import asyncio as _asyncio
import os as _os
import shutil as _shutil
from pathlib import Path as _Path

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand
from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand
from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand
from helping_hands.lib.hands.v1.hand.cli.gemini import GeminiCLIHand
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

# Legacy patch targets in tests/external code refer to module-level names
# on `hand.placeholders` (for example placeholders.os.geteuid).
asyncio = _asyncio
os = _os
shutil = _shutil
Path = _Path

__all__ = [
    "ClaudeCodeHand",
    "CodexCLIHand",
    "GeminiCLIHand",
    "GooseCLIHand",
    "Path",
    "_TwoPhaseCLIHand",
    "asyncio",
    "os",
    "shutil",
]
