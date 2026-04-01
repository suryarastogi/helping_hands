"""Tests for the Grill Me interactive session module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.repo import RepoIndex


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt."""

    def test_includes_user_prompt(self, tmp_path: Path) -> None:
        from helping_hands.server.grill import _build_system_prompt

        (tmp_path / "main.py").write_text("print('hello')")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "Add a widget feature")
        assert "Add a widget feature" in result
        assert "## FINAL PLAN" in result

    def test_includes_readme(self, tmp_path: Path) -> None:
        from helping_hands.server.grill import _build_system_prompt

        (tmp_path / "README.md").write_text("# My Project\nA cool project.")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "test")
        assert "My Project" in result

    def test_includes_file_tree(self, tmp_path: Path) -> None:
        from helping_hands.server.grill import _build_system_prompt

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "test")
        assert "app.py" in result

    def test_no_write_instruction(self, tmp_path: Path) -> None:
        from helping_hands.server.grill import _build_system_prompt

        repo_index = RepoIndex(root=tmp_path, files=[], reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "Do NOT write" in result
        assert "Do NOT implement" in result


class TestCloneRepo:
    """Tests for _clone_repo."""

    def test_local_path(self, tmp_path: Path) -> None:
        from helping_hands.server.grill import _clone_repo

        resolved, cloned_from, tmp_root = _clone_repo(str(tmp_path), None)
        assert resolved == tmp_path
        assert cloned_from is None
        assert tmp_root is None

    def test_invalid_path_raises(self) -> None:
        from helping_hands.server.grill import _clone_repo

        with pytest.raises(ValueError, match="Invalid repo path"):
            _clone_repo("/nonexistent/path/that/does/not/exist", None)


class TestSummarizeToolUse:
    """Tests for _summarize_tool_use."""

    def test_read(self) -> None:
        from helping_hands.server.grill import _summarize_tool_use

        assert (
            _summarize_tool_use("Read", {"file_path": "src/main.py"})
            == "Read src/main.py"
        )

    def test_grep(self) -> None:
        from helping_hands.server.grill import _summarize_tool_use

        assert _summarize_tool_use("Grep", {"pattern": "TODO"}) == "Grep /TODO/"

    def test_glob(self) -> None:
        from helping_hands.server.grill import _summarize_tool_use

        assert _summarize_tool_use("Glob", {"pattern": "**/*.py"}) == "Glob **/*.py"

    def test_unknown(self) -> None:
        from helping_hands.server.grill import _summarize_tool_use

        assert _summarize_tool_use("Unknown", {}) == "tool: Unknown"


class TestGrillEnabled:
    """Tests for the grill feature flag in app.py."""

    def test_disabled_by_default(self) -> None:
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {}, clear=True):
            assert _grill_enabled() is False

    def test_enabled_when_set(self) -> None:
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {"GRILL_ME_ENABLED": "1"}):
            assert _grill_enabled() is True

    def test_disabled_when_zero(self) -> None:
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {"GRILL_ME_ENABLED": "0"}):
            assert _grill_enabled() is False
