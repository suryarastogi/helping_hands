"""Tests for helping_hands.lib.meta.tools.search."""

from __future__ import annotations

from pathlib import Path

import pytest

from helping_hands.lib.meta.tools import search as search_tools


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    """Create a sample repo structure for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def main():\n    print('hello')\n")
    (tmp_path / "src" / "utils.py").write_text("def helper():\n    return 42\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_main():\n    pass\n")
    (tmp_path / "README.md").write_text("# My Project\n")
    return tmp_path


class TestGlobFiles:
    def test_find_python_files(self, sample_repo: Path) -> None:
        result = search_tools.glob_files(sample_repo, pattern="**/*.py")
        assert result.pattern == "**/*.py"
        assert len(result.matches) == 3
        assert "src/main.py" in result.matches

    def test_find_in_subdirectory(self, sample_repo: Path) -> None:
        result = search_tools.glob_files(
            sample_repo, pattern="*.py", base_dir="src"
        )
        assert len(result.matches) == 2

    def test_max_results(self, sample_repo: Path) -> None:
        result = search_tools.glob_files(
            sample_repo, pattern="**/*.py", max_results=1
        )
        assert len(result.matches) == 1
        assert result.truncated

    def test_empty_pattern_raises(self, sample_repo: Path) -> None:
        with pytest.raises(ValueError, match="pattern must be non-empty"):
            search_tools.glob_files(sample_repo, pattern="  ")

    def test_invalid_max_results(self, sample_repo: Path) -> None:
        with pytest.raises(ValueError, match="max_results must be > 0"):
            search_tools.glob_files(sample_repo, pattern="*.py", max_results=0)


class TestGrepContent:
    def test_find_function_def(self, sample_repo: Path) -> None:
        result = search_tools.grep_content(sample_repo, pattern="def main")
        assert len(result.matches) == 1
        assert result.matches[0].file == "src/main.py"
        assert result.matches[0].line_number == 1

    def test_case_insensitive(self, sample_repo: Path) -> None:
        result = search_tools.grep_content(
            sample_repo, pattern="DEF MAIN", ignore_case=True
        )
        assert len(result.matches) == 1

    def test_glob_filter(self, sample_repo: Path) -> None:
        result = search_tools.grep_content(
            sample_repo, pattern="def", glob="*.py"
        )
        assert all(m.file.endswith(".py") for m in result.matches)

    def test_empty_pattern_raises(self, sample_repo: Path) -> None:
        with pytest.raises(ValueError, match="pattern must be non-empty"):
            search_tools.grep_content(sample_repo, pattern="  ")

    def test_invalid_regex_raises(self, sample_repo: Path) -> None:
        with pytest.raises(ValueError, match="invalid regex"):
            search_tools.grep_content(sample_repo, pattern="[invalid")

    def test_max_results(self, sample_repo: Path) -> None:
        result = search_tools.grep_content(
            sample_repo, pattern="def", max_results=1
        )
        assert len(result.matches) == 1
        assert result.truncated


class TestListDirectory:
    def test_list_root(self, sample_repo: Path) -> None:
        entries, truncated = search_tools.list_directory(sample_repo)
        assert not truncated
        assert "README.md" in entries
        assert "src/" in entries
        assert "tests/" in entries

    def test_list_subdirectory(self, sample_repo: Path) -> None:
        entries, truncated = search_tools.list_directory(
            sample_repo, rel_path="src"
        )
        assert not truncated
        assert "main.py" in entries
        assert "utils.py" in entries

    def test_hidden_files_excluded_by_default(self, sample_repo: Path) -> None:
        (sample_repo / ".hidden").write_text("secret\n")
        entries, _ = search_tools.list_directory(sample_repo)
        assert ".hidden" not in entries

    def test_hidden_files_included(self, sample_repo: Path) -> None:
        (sample_repo / ".hidden").write_text("secret\n")
        entries, _ = search_tools.list_directory(
            sample_repo, include_hidden=True
        )
        assert ".hidden" in entries

    def test_max_entries(self, sample_repo: Path) -> None:
        entries, truncated = search_tools.list_directory(
            sample_repo, max_entries=1
        )
        assert len(entries) == 1
        assert truncated

    def test_not_a_directory_raises(self, sample_repo: Path) -> None:
        with pytest.raises(NotADirectoryError):
            search_tools.list_directory(sample_repo, rel_path="README.md")
