"""Tests for v263: the _run_git_diff() shared helper in pr_description.py.

Before this helper, _get_diff() and _get_uncommitted_diff() each contained their
own subprocess.run call, timeout constant, FileNotFoundError handler, and
TimeoutExpired handler. Any change to the error handling (e.g. adding a new
timeout label or changing the not-found message) had to be applied twice.

_run_git_diff() centralises this logic. The delegation tests confirm that both
functions forward their arguments correctly; the AST test ensures neither
function re-introduces its own duplicate subprocess block after the refactor.

A regression here would cause git diff timeouts or "git not found" errors to
be handled differently between the staged-diff and uncommitted-diff paths.
"""

from __future__ import annotations

import ast
import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    _GIT_DIFF_TIMEOUT_S,
    _GIT_NOT_FOUND_UNCOMMITTED_MSG,
    _get_diff,
    _get_uncommitted_diff,
    _run_git_diff,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "helping_hands"
_PR_DESCRIPTION_PATH = _SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "pr_description.py"


# ===================================================================
# _run_git_diff — unit tests
# ===================================================================


class TestRunGitDiff:
    """Direct tests for the ``_run_git_diff`` helper."""

    def test_returns_stripped_stdout_on_success(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=0, stdout="  diff output\n")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _run_git_diff(
                tmp_path,
                ["git", "diff", "--cached"],
                not_found_msg="git not found",
                timeout_label="git diff --cached",
            )
        assert result == "diff output"
        mock_run.assert_called_once_with(
            ["git", "diff", "--cached"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_DIFF_TIMEOUT_S,
        )

    def test_returns_empty_on_non_zero_returncode(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=1, stdout="error stuff")
        with patch("subprocess.run", return_value=mock_result):
            result = _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="msg",
                timeout_label="label",
            )
        assert result == ""

    def test_returns_empty_on_blank_stdout(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=0, stdout="   \n  ")
        with patch("subprocess.run", return_value=mock_result):
            result = _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="msg",
                timeout_label="label",
            )
        assert result == ""

    def test_returns_empty_on_empty_stdout(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=0, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            result = _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="msg",
                timeout_label="label",
            )
        assert result == ""

    def test_file_not_found_logs_debug_and_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            caplog.at_level(logging.DEBUG),
        ):
            result = _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="custom not found msg",
                timeout_label="label",
            )
        assert result == ""
        assert "custom not found msg" in caplog.text

    def test_timeout_logs_warning_and_returns_empty(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
            ),
            caplog.at_level(logging.WARNING),
        ):
            result = _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="msg",
                timeout_label="git diff custom",
            )
        assert result == ""
        assert "git diff custom" in caplog.text
        assert "timed out" in caplog.text

    def test_timeout_label_appears_in_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
            ),
            caplog.at_level(logging.WARNING),
        ):
            _run_git_diff(
                tmp_path,
                ["git", "diff", "HEAD~1"],
                not_found_msg="msg",
                timeout_label="git diff HEAD~1",
            )
        assert "git diff HEAD~1" in caplog.text

    def test_passes_correct_timeout(self, tmp_path: Path) -> None:
        mock_result = MagicMock(returncode=0, stdout="ok\n")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _run_git_diff(
                tmp_path,
                ["git", "diff"],
                not_found_msg="msg",
                timeout_label="label",
            )
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == _GIT_DIFF_TIMEOUT_S


# ===================================================================
# _get_diff — delegation tests
# ===================================================================


class TestGetDiffDelegation:
    """Verify _get_diff delegates to _run_git_diff."""

    _MODULE = "helping_hands.lib.hands.v1.hand.pr_description"

    def test_returns_first_diff_when_base_branch_succeeds(self, tmp_path: Path) -> None:
        with patch(f"{self._MODULE}._run_git_diff", return_value="base diff") as mock:
            result = _get_diff(tmp_path, base_branch="main")
        assert result == "base diff"
        # Should only call once since first call returned data
        assert mock.call_count == 1
        args = mock.call_args_list[0]
        assert "main...HEAD" in str(args)

    def test_falls_back_to_head1_when_base_branch_empty(self, tmp_path: Path) -> None:
        with patch(
            f"{self._MODULE}._run_git_diff", side_effect=["", "fallback diff"]
        ) as mock:
            result = _get_diff(tmp_path, base_branch="main")
        assert result == "fallback diff"
        assert mock.call_count == 2

    def test_returns_empty_when_both_diffs_empty(self, tmp_path: Path) -> None:
        with patch(f"{self._MODULE}._run_git_diff", return_value=""):
            result = _get_diff(tmp_path, base_branch="main")
        assert result == ""


# ===================================================================
# _get_uncommitted_diff — delegation tests
# ===================================================================


class TestGetUncommittedDiffDelegation:
    """Verify _get_uncommitted_diff delegates to _run_git_diff for diff."""

    _MODULE = "helping_hands.lib.hands.v1.hand.pr_description"

    def test_delegates_cached_diff(self, tmp_path: Path) -> None:
        mock_add = MagicMock(returncode=0)
        with (
            patch("subprocess.run", return_value=mock_add),
            patch(
                f"{self._MODULE}._run_git_diff", return_value="cached diff"
            ) as mock_diff,
        ):
            result = _get_uncommitted_diff(tmp_path)
        assert result == "cached diff"
        mock_diff.assert_called_once()
        call_args = mock_diff.call_args
        assert call_args[0][1] == ["git", "diff", "--cached"]

    def test_uses_uncommitted_not_found_msg(self, tmp_path: Path) -> None:
        mock_add = MagicMock(returncode=0)
        with (
            patch("subprocess.run", return_value=mock_add),
            patch(f"{self._MODULE}._run_git_diff", return_value="") as mock_diff,
        ):
            _get_uncommitted_diff(tmp_path)
        call_kwargs = mock_diff.call_args[1]
        assert call_kwargs["not_found_msg"] == _GIT_NOT_FOUND_UNCOMMITTED_MSG


# ===================================================================
# AST source check: no duplicate subprocess.run + exception blocks
# ===================================================================


class TestNoDuplicateSubprocessBlocks:
    """Verify that ``_get_diff`` and ``_get_uncommitted_diff`` no longer
    contain inline ``subprocess.run`` calls with ``text=True`` (the
    diff calls are now delegated to ``_run_git_diff``).
    """

    @pytest.fixture()
    def source_tree(self) -> ast.Module:
        return ast.parse(_PR_DESCRIPTION_PATH.read_text())

    def _function_body_source(self, tree: ast.Module, name: str) -> str:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.dump(node)
        pytest.fail(f"Function {name!r} not found in pr_description.py")

    def test_get_diff_no_inline_subprocess_run(self, source_tree: ast.Module) -> None:
        body = self._function_body_source(source_tree, "_get_diff")
        # _get_diff should not contain subprocess.run calls — it delegates
        assert "subprocess" not in body

    def test_get_uncommitted_diff_has_one_subprocess_run(
        self, source_tree: ast.Module
    ) -> None:
        """_get_uncommitted_diff still has the git-add subprocess call,
        but the git-diff call should be delegated."""
        body = self._function_body_source(source_tree, "_get_uncommitted_diff")
        # Count subprocess.run calls — should be exactly 1 (git add .)
        count = body.count("subprocess")
        assert count == 1, (
            f"Expected 1 subprocess ref (git add) in _get_uncommitted_diff, "
            f"found {count}"
        )

    def test_run_git_diff_exists(self, source_tree: ast.Module) -> None:
        found = any(
            isinstance(node, ast.FunctionDef) and node.name == "_run_git_diff"
            for node in ast.walk(source_tree)
        )
        assert found, "_run_git_diff function not found in pr_description.py"

    def test_run_git_diff_has_docstring(self, source_tree: ast.Module) -> None:
        for node in ast.walk(source_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_git_diff":
                docstring = ast.get_docstring(node)
                assert docstring, "_run_git_diff should have a docstring"
                return
        pytest.fail("_run_git_diff not found")
