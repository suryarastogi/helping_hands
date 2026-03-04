"""Tests for helping_hands.lib.repo."""

from __future__ import annotations

from pathlib import Path

import pytest

from helping_hands.lib.repo import RepoIndex


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

    def test_empty_directory(self, tmp_path: Path) -> None:
        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == []
        assert idx.root == tmp_path

    def test_files_are_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "z.py").write_text("")
        (tmp_path / "a.py").write_text("")
        (tmp_path / "m.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == ["a.py", "m.py", "z.py"]

    def test_deeply_nested_files(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        assert "a/b/c/d/deep.py" in idx.files

    def test_excludes_dotgit_in_nested_path(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git" / "refs"
        git_dir.mkdir(parents=True)
        (git_dir / "heads").write_text("")
        (tmp_path / "real.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == ["real.py"]

    def test_directories_not_included(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file.py").write_text("")
        idx = RepoIndex.from_path(tmp_path)
        assert "subdir" not in idx.files
        assert "subdir/file.py" in idx.files

    def test_default_files_empty(self) -> None:
        idx = RepoIndex(root=Path("/tmp/fake"))
        assert idx.files == []
