"""Shared meta-layer utilities used across ``helping_hands.lib``.

The ``meta`` namespace is intended for reusable infrastructure helpers that
are not tied to a single backend. It currently exports:
- ``tools`` for path-safe runtime tool operations.
- ``skills`` for runtime-selectable skill bundles injected into hands.
"""

from helping_hands.lib.meta import skills, tools

__all__ = ["skills", "tools"]
