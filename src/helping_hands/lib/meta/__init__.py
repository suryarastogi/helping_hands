"""Shared meta-layer utilities used across ``helping_hands.lib``.

The ``meta`` namespace is intended for reusable infrastructure helpers that
are not tied to a single backend. Currently it exports ``tools``, a set of
system filesystem helpers used by iterative hands.
"""

from helping_hands.lib.meta import tools

__all__ = ["tools"]
