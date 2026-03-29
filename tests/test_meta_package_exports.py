"""Tests for helping_hands.lib.meta package-level re-exports.

Protects the public surface of the meta package: __all__ must list exactly the
submodules that external callers import (skills and tools), and the re-exported
attributes must be the same objects as the source modules (not copies).  If a
submodule is added to __all__ but not actually importable, or if a re-export
becomes a stale alias after a refactor, callers that rely on the flat import path
will silently get the wrong object or an ImportError at runtime.
"""

from __future__ import annotations

import helping_hands.lib.meta as pkg
from helping_hands.lib.meta import __all__


class TestMetaPackageAll:
    """Verify __all__ lists every public re-export."""

    def test_all_contains_expected_symbols(self) -> None:
        expected = {"skills", "tools"}
        assert set(__all__) == expected

    def test_all_entries_are_importable(self) -> None:
        for name in __all__:
            assert hasattr(pkg, name), f"{name} listed in __all__ but not importable"


class TestMetaPackageIdentity:
    """Verify re-exported submodules match their source packages."""

    def test_tools_identity(self) -> None:
        import helping_hands.lib.meta.tools as src

        assert pkg.tools is src

    def test_skills_identity(self) -> None:
        import helping_hands.lib.meta.skills as src

        assert pkg.skills is src
