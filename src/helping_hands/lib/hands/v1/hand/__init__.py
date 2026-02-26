"""Public import surface for hand backends in ``helping_hands.lib.hands.v1``.

This package-level module is the compatibility boundary consumed by:
- ``helping_hands.cli.main`` for CLI backend routing.
- ``helping_hands.server.celery_app`` for E2E task execution.
- ``helping_hands.lib.hands.v1`` and external imports that use
  ``from helping_hands.lib.hands.v1.hand import ...``.

It re-exports the abstract interface (`Hand`, `HandResponse`) plus all
concrete backend classes from sibling modules. The ``subprocess`` alias is
kept for backward-compatible patch targets in tests.
"""

from helping_hands.lib.hands.v1.hand import base as _base_module
from helping_hands.lib.hands.v1.hand.atomic import AtomicHand
from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.hands.v1.hand.e2e import E2EHand
from helping_hands.lib.hands.v1.hand.iterative import (
    BasicAtomicHand,
    BasicLangGraphHand,
)
from helping_hands.lib.hands.v1.hand.langgraph import LangGraphHand
from helping_hands.lib.hands.v1.hand.placeholders import (
    ClaudeCodeHand,
    CodexCLIHand,
    GeminiCLIHand,
    GooseCLIHand,
)

# Backward-compatible patch target for tests and external users.
subprocess = _base_module.subprocess

__all__ = [
    "AtomicHand",
    "BasicAtomicHand",
    "BasicLangGraphHand",
    "ClaudeCodeHand",
    "CodexCLIHand",
    "E2EHand",
    "GeminiCLIHand",
    "GooseCLIHand",
    "Hand",
    "HandResponse",
    "LangGraphHand",
]
