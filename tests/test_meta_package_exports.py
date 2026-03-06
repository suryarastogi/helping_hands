"""Tests for helping_hands.lib.meta package-level re-exports."""

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
