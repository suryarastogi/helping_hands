"""Tests for v178: py.typed marker and __all__ on remaining __init__.py files."""

from __future__ import annotations

from pathlib import Path

import helping_hands
import helping_hands.cli
import helping_hands.lib
import helping_hands.lib.hands
import helping_hands.server

# ---------------------------------------------------------------------------
# py.typed marker
# ---------------------------------------------------------------------------


class TestPyTypedMarker:
    """Verify PEP 561 py.typed marker file exists."""

    def test_py_typed_exists(self) -> None:
        pkg_dir = Path(helping_hands.__file__).parent
        marker = pkg_dir / "py.typed"
        assert marker.exists(), "py.typed marker missing for PEP 561 compliance"

    def test_py_typed_is_file(self) -> None:
        pkg_dir = Path(helping_hands.__file__).parent
        marker = pkg_dir / "py.typed"
        assert marker.is_file(), "py.typed should be a regular file"


# ---------------------------------------------------------------------------
# Root package __all__
# ---------------------------------------------------------------------------


class TestRootPackageAll:
    """Verify helping_hands root __init__.py __all__ declaration."""

    def test_all_exists(self) -> None:
        assert hasattr(helping_hands, "__all__")

    def test_all_contains_version(self) -> None:
        assert "__version__" in helping_hands.__all__

    def test_all_entries_importable(self) -> None:
        for name in helping_hands.__all__:
            assert hasattr(helping_hands, name), (
                f"{name} listed in __all__ but not importable"
            )

    def test_no_private_names(self) -> None:
        for name in helping_hands.__all__:
            assert not name.startswith("_") or name == "__version__", (
                f"private name {name} in __all__"
            )


# ---------------------------------------------------------------------------
# CLI package __all__
# ---------------------------------------------------------------------------


class TestCliPackageAll:
    """Verify helping_hands.cli __init__.py __all__ declaration."""

    def test_all_exists(self) -> None:
        assert hasattr(helping_hands.cli, "__all__")

    def test_all_is_empty(self) -> None:
        assert helping_hands.cli.__all__ == []

    def test_all_is_list(self) -> None:
        assert isinstance(helping_hands.cli.__all__, list)


# ---------------------------------------------------------------------------
# Lib package __all__
# ---------------------------------------------------------------------------


class TestLibPackageAll:
    """Verify helping_hands.lib __init__.py __all__ declaration."""

    def test_all_exists(self) -> None:
        assert hasattr(helping_hands.lib, "__all__")

    def test_all_is_empty(self) -> None:
        assert helping_hands.lib.__all__ == []

    def test_all_is_list(self) -> None:
        assert isinstance(helping_hands.lib.__all__, list)


# ---------------------------------------------------------------------------
# Hands package __all__
# ---------------------------------------------------------------------------


class TestHandsPackageAll:
    """Verify helping_hands.lib.hands __init__.py __all__ declaration."""

    def test_all_exists(self) -> None:
        assert hasattr(helping_hands.lib.hands, "__all__")

    def test_all_is_empty(self) -> None:
        assert helping_hands.lib.hands.__all__ == []

    def test_all_is_list(self) -> None:
        assert isinstance(helping_hands.lib.hands.__all__, list)


# ---------------------------------------------------------------------------
# Server package __all__
# ---------------------------------------------------------------------------


class TestServerPackageAll:
    """Verify helping_hands.server __init__.py __all__ declaration."""

    def test_all_exists(self) -> None:
        assert hasattr(helping_hands.server, "__all__")

    def test_all_is_empty(self) -> None:
        assert helping_hands.server.__all__ == []

    def test_all_is_list(self) -> None:
        assert isinstance(helping_hands.server.__all__, list)


# ---------------------------------------------------------------------------
# Completeness: all __init__.py files have __all__
# ---------------------------------------------------------------------------


class TestAllInitFilesHaveAll:
    """Verify every __init__.py under src/helping_hands has __all__."""

    def test_all_init_files_declare_all(self) -> None:
        src_root = Path(helping_hands.__file__).parent
        init_files = sorted(src_root.rglob("__init__.py"))
        assert len(init_files) >= 12, (
            f"Expected at least 12 __init__.py files, found {len(init_files)}"
        )
        for init_file in init_files:
            content = init_file.read_text()
            assert "__all__" in content, (
                f"{init_file.relative_to(src_root)} missing __all__ declaration"
            )
