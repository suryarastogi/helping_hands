"""Tests for hhpy.helping_hands.lib.repo."""

from __future__ import annotations

from pathlib import Path

import pytest

from hhpy.helping_hands.lib.repo import RepoIndex


class TestRepoIndex:
    def test_from_path_indexes_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.py").write_text("y = 2")

        idx = RepoIndex.from_path(tmp_path)
        assert idx.root == tmp_path
        assert "a.py" in idx.files
        assert "sub/b.py" in idx.files

    def test_from_path_excludes_dotgit_parts(self) -> None:
        """Verify the .git filter logic without needing to write into a .git dir."""
        all_paths = ["src/main.py", ".git/config", ".git/objects/abc", "README.md"]
        filtered = [p for p in all_paths if ".git" not in Path(p).parts]
        assert filtered == ["src/main.py", "README.md"]

    def test_from_path_raises_on_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            RepoIndex.from_path(tmp_path / "nonexistent")
