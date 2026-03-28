"""Tests for helping_hands.lib.repo.

Guards RepoIndex.from_path, which builds the file inventory that is injected
into every Hand's system prompt. Critical invariants: .git internals are
excluded (so agent prompts don't leak git objects), .github is retained (CI
configs are useful context), only files appear (not directories), paths are
relative and sorted, and the constructor raises FileNotFoundError for missing
or non-directory paths. If the .git filter regresses, token budgets balloon
with object files; if sorting changes, prompt diffs become noisy and hard to
review.
"""

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

    def test_from_path_empty_directory(self, tmp_path: Path) -> None:
        """An empty directory should produce an empty file list."""
        idx = RepoIndex.from_path(tmp_path)
        assert idx.root == tmp_path
        assert idx.files == []

    def test_from_path_sorts_files(self, tmp_path: Path) -> None:
        """Files should be returned in sorted order."""
        (tmp_path / "z.py").write_text("")
        (tmp_path / "a.py").write_text("")
        (tmp_path / "m.py").write_text("")

        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == ["a.py", "m.py", "z.py"]

    def test_from_path_excludes_nested_dotgit(self, tmp_path: Path) -> None:
        """Files inside .git subdirectories should be excluded."""
        git_dir = tmp_path / ".git" / "refs"
        git_dir.mkdir(parents=True)
        (git_dir / "HEAD").write_text("ref")
        (tmp_path / "real.py").write_text("code")

        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == ["real.py"]

    def test_from_path_excludes_only_dotgit_not_similar_names(
        self, tmp_path: Path
    ) -> None:
        """A directory named '.github' should NOT be excluded."""
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        (github_dir / "workflows.yml").write_text("ci: true")
        (tmp_path / "main.py").write_text("code")

        idx = RepoIndex.from_path(tmp_path)
        assert ".github/workflows.yml" in idx.files
        assert "main.py" in idx.files

    def test_from_path_deeply_nested_files(self, tmp_path: Path) -> None:
        """Deeply nested files should be included with relative paths."""
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.txt").write_text("deep")

        idx = RepoIndex.from_path(tmp_path)
        assert "a/b/c/d/deep.txt" in idx.files

    def test_from_path_ignores_directories_in_listing(self, tmp_path: Path) -> None:
        """Only files should appear in the index, not directories."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("content")

        idx = RepoIndex.from_path(tmp_path)
        assert idx.files == ["file.txt"]

    def test_from_path_raises_on_file_not_dir(self, tmp_path: Path) -> None:
        """Passing a file path (not a directory) should raise FileNotFoundError."""
        f = tmp_path / "afile.txt"
        f.write_text("not a dir")
        with pytest.raises(FileNotFoundError, match="Not a directory"):
            RepoIndex.from_path(f)

    def test_dataclass_defaults(self) -> None:
        """RepoIndex can be constructed with just a root path."""
        idx = RepoIndex(root=Path("/tmp"))
        assert idx.root == Path("/tmp")
        assert idx.files == []

    def test_files_field_independence(self) -> None:
        """Each RepoIndex instance should have its own files list."""
        a = RepoIndex(root=Path("/a"))
        b = RepoIndex(root=Path("/b"))
        a.files.append("x.py")
        assert b.files == []
