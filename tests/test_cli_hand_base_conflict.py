"""Tests for CLI hand conflict resolution helpers.

Covers ``_build_conflict_fix_prompt``, ``_get_conflicted_files``,
``_attempt_rebase_with_conflict_fix``, and ``_ai_resolve_push_conflicts``
— the AI-driven merge conflict resolution pipeline that was previously
at 0% coverage.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from helping_hands.lib.hands.v1.hand.base import (
    _META_CONFLICT_FIX_ERROR,
    _META_CONFLICT_FIX_STATUS,
    _META_PR_COMMIT,
)
from helping_hands.lib.hands.v1.hand.cli.base import (
    ConflictFixStatus,
    _TwoPhaseCLIHand,
)

# ---------------------------------------------------------------------------
# Minimal stub that skips the full __init__ chain
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _COMMAND_ENV_VAR = "STUB_CMD"
    _DEFAULT_CLI_CMD = "stub-cli"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ()
    _BACKEND_NAME = "stub"

    def __init__(self, *, repo_root: Path | None = None) -> None:
        self.config = SimpleNamespace(
            model="stub-model-1",
            verbose=False,
            use_native_cli_auth=False,
            github_token="test-token",
        )
        self.auto_pr = True
        self._baseline_head = ""
        self._ci_fix_mode = False
        self.master_rebase = False
        self.fix_conflicts = False
        self.pr_number = 42
        if repo_root is not None:
            from helping_hands.lib.repo import RepoIndex

            self.repo_index = RepoIndex(root=repo_root, files=[])


# ---------------------------------------------------------------------------
# _build_conflict_fix_prompt — pure static method
# ---------------------------------------------------------------------------


class TestBuildConflictFixPrompt:
    def test_single_file_no_output(self) -> None:
        result = _Stub._build_conflict_fix_prompt("", ["src/main.py"])
        assert "src/main.py" in result
        assert "Git output:" not in result
        assert "resolve ALL merge conflicts" in result

    def test_multiple_files_with_output(self) -> None:
        result = _Stub._build_conflict_fix_prompt(
            "CONFLICT (content): Merge conflict in foo.py",
            ["foo.py", "bar.py"],
        )
        assert "foo.py" in result
        assert "bar.py" in result
        assert "Git output:" in result
        assert "CONFLICT" in result

    def test_empty_file_list_shows_unknown(self) -> None:
        result = _Stub._build_conflict_fix_prompt("some output", [])
        assert "(unknown)" in result

    def test_truncates_long_output(self) -> None:
        long_output = "x" * 5000
        result = _Stub._build_conflict_fix_prompt(long_output, ["a.py"])
        assert "...[truncated]" in result
        # Ensure the output is capped — first 4000 chars + truncation marker
        assert "x" * 4000 in result

    def test_whitespace_only_output_excluded(self) -> None:
        result = _Stub._build_conflict_fix_prompt("   \n  ", ["a.py"])
        assert "Git output:" not in result

    def test_conflict_markers_mentioned(self) -> None:
        result = _Stub._build_conflict_fix_prompt("", ["a.py"])
        assert "<<<<<<< HEAD" in result
        assert "=======" in result
        assert ">>>>>>>" in result


# ---------------------------------------------------------------------------
# _get_conflicted_files — subprocess mock
# ---------------------------------------------------------------------------


class TestGetConflictedFiles:
    @patch("helping_hands.lib.hands.v1.hand.cli.base.subprocess.run")
    def test_returns_files(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="foo.py\nbar.py\n", stderr=""
        )
        stub = _Stub(repo_root=tmp_path)
        result = stub._get_conflicted_files(tmp_path)
        assert result == ["foo.py", "bar.py"]

    @patch("helping_hands.lib.hands.v1.hand.cli.base.subprocess.run")
    def test_empty_output(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        stub = _Stub(repo_root=tmp_path)
        assert stub._get_conflicted_files(tmp_path) == []

    @patch("helping_hands.lib.hands.v1.hand.cli.base.subprocess.run")
    def test_timeout_returns_empty(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
        stub = _Stub(repo_root=tmp_path)
        assert stub._get_conflicted_files(tmp_path) == []

    @patch("helping_hands.lib.hands.v1.hand.cli.base.subprocess.run")
    def test_oserror_returns_empty(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = OSError("git not found")
        stub = _Stub(repo_root=tmp_path)
        assert stub._get_conflicted_files(tmp_path) == []

    @patch("helping_hands.lib.hands.v1.hand.cli.base.subprocess.run")
    def test_filters_blank_lines(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="foo.py\n\n  \nbar.py\n", stderr=""
        )
        stub = _Stub(repo_root=tmp_path)
        assert stub._get_conflicted_files(tmp_path) == ["foo.py", "bar.py"]


# ---------------------------------------------------------------------------
# _attempt_rebase_with_conflict_fix — async
# ---------------------------------------------------------------------------

_CLI_SUB = "helping_hands.lib.hands.v1.hand.cli.base.subprocess.run"


class TestAttemptRebaseWithConflictFix:
    def _run(self, stub: _Stub, repo_dir: Path) -> str:
        emit = AsyncMock()
        return asyncio.run(
            stub._attempt_rebase_with_conflict_fix(
                repo_dir=repo_dir,
                target_branch="main",
                emit=emit,
            )
        )

    @patch(_CLI_SUB)
    def test_fetch_failure_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git fetch")
        stub = _Stub(repo_root=tmp_path)
        assert self._run(stub, tmp_path) == ConflictFixStatus.ERROR

    @patch(_CLI_SUB)
    def test_rebase_succeeds_no_conflicts(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch succeeds, rebase succeeds
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        assert self._run(stub, tmp_path) == ConflictFixStatus.NO_CONFLICTS

    @patch(_CLI_SUB)
    def test_rebase_fails_no_conflicted_files_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch ok, rebase fails, git diff returns no files, rebase --abort
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="fatal: error"
            ),
            # _get_conflicted_files: no files
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        assert self._run(stub, tmp_path) == ConflictFixStatus.ERROR

    @patch(_CLI_SUB)
    def test_ai_resolution_fails_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch ok, rebase fails with conflicts, AI fails
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="CONFLICT", stderr=""
            ),
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # rebase --abort after AI error
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)

        with patch.object(stub, "_invoke_backend", side_effect=RuntimeError("boom")):
            assert self._run(stub, tmp_path) == ConflictFixStatus.ERROR

    @patch(_CLI_SUB)
    def test_ai_resolves_but_conflicts_remain_returns_failed(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch ok, rebase fails, AI runs, but conflicts still there
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="CONFLICT", stderr=""
            ),
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # _get_conflicted_files after AI: still has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)

        with patch.object(stub, "_invoke_backend", new_callable=AsyncMock):
            assert self._run(stub, tmp_path) == ConflictFixStatus.FAILED

    @patch(_CLI_SUB)
    def test_rebase_continue_fails_returns_failed(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch ok, rebase fails, AI resolves, git add, rebase --continue fails
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="CONFLICT", stderr=""
            ),
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue fails
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="continue error"
            ),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)

        with patch.object(stub, "_invoke_backend", new_callable=AsyncMock):
            assert self._run(stub, tmp_path) == ConflictFixStatus.FAILED

    @patch(_CLI_SUB)
    def test_full_success(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # fetch ok, rebase fails, AI resolves, git add, rebase --continue ok
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="CONFLICT", stderr=""
            ),
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)

        with patch.object(stub, "_invoke_backend", new_callable=AsyncMock):
            assert self._run(stub, tmp_path) == ConflictFixStatus.SUCCESS

    @patch(_CLI_SUB)
    def test_fetch_timeout_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=60)
        stub = _Stub(repo_root=tmp_path)
        assert self._run(stub, tmp_path) == ConflictFixStatus.ERROR


# ---------------------------------------------------------------------------
# _ai_resolve_push_conflicts — async
# ---------------------------------------------------------------------------


class TestAiResolvePushConflicts:
    def _run(self, stub: _Stub, metadata: dict[str, str]) -> dict[str, str]:
        emit = AsyncMock()
        return asyncio.run(
            stub._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
        )

    def test_not_needs_ai_returns_unchanged(self, tmp_path: Path) -> None:
        stub = _Stub(repo_root=tmp_path)
        meta = {"conflict_fix_status": "none"}
        result = self._run(stub, meta)
        assert result is meta

    def test_no_branch_returns_unchanged(self, tmp_path: Path) -> None:
        stub = _Stub(repo_root=tmp_path)
        meta = {_META_CONFLICT_FIX_STATUS: "needs_ai"}
        result = self._run(stub, meta)
        assert result is meta

    @patch(_CLI_SUB)
    def test_no_conflicted_files_aborts_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        # _get_conflicted_files returns empty, rebase --abort
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
            "_conflict_repo": "owner/repo",
        }
        result = self._run(stub, meta)
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR

    @patch(_CLI_SUB)
    def test_ai_error_aborts_returns_error(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff for context
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff output", stderr=""
            ),
            # rebase --abort after AI error
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }
        with patch.object(stub, "_invoke_backend", side_effect=RuntimeError("boom")):
            result = self._run(stub, meta)
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR
        assert result[_META_CONFLICT_FIX_ERROR] == "boom"

    @patch(_CLI_SUB)
    def test_remaining_conflicts_returns_failed(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: still has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }
        with patch.object(stub, "_invoke_backend", new_callable=AsyncMock):
            result = self._run(stub, meta)
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.FAILED

    @patch(_CLI_SUB)
    def test_rebase_continue_fails_returns_failed(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue fails
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="error"
            ),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }
        with patch.object(stub, "_invoke_backend", new_callable=AsyncMock):
            result = self._run(stub, meta)
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.FAILED

    @patch(_CLI_SUB)
    @patch("helping_hands.lib.github.GitHubClient")
    def test_full_success_without_master_rebase(
        self,
        mock_gh_cls: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files: has files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        stub.master_rebase = False

        mock_gh = MagicMock()
        mock_gh_cls.return_value.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh_cls.return_value.__exit__ = MagicMock(return_value=False)

        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }

        with (
            patch.object(stub, "_invoke_backend", new_callable=AsyncMock),
            patch.object(stub, "_push_noninteractive"),
            patch.object(stub, "_run_git_read", return_value="abc1234"),
        ):
            result = self._run(stub, meta)

        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.SUCCESS
        assert result[_META_PR_COMMIT] == "abc1234"

    @patch(_CLI_SUB)
    @patch("helping_hands.lib.github.GitHubClient")
    def test_push_after_resolve_fails_returns_error(
        self,
        mock_gh_cls: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        stub.master_rebase = False

        mock_gh = MagicMock()
        mock_gh_cls.return_value.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh_cls.return_value.__exit__ = MagicMock(return_value=False)

        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }

        with (
            patch.object(stub, "_invoke_backend", new_callable=AsyncMock),
            patch.object(
                stub, "_push_noninteractive", side_effect=RuntimeError("push fail")
            ),
        ):
            result = self._run(stub, meta)

        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR
        assert result[_META_CONFLICT_FIX_ERROR] == "push fail"

    @patch(_CLI_SUB)
    @patch("helping_hands.lib.github.GitHubClient")
    def test_master_rebase_success_after_resolve(
        self,
        mock_gh_cls: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        stub.master_rebase = True

        mock_gh = MagicMock()
        mock_gh_cls.return_value.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh_cls.return_value.__exit__ = MagicMock(return_value=False)

        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }

        with (
            patch.object(stub, "_invoke_backend", new_callable=AsyncMock),
            patch.object(stub, "_push_noninteractive"),
            patch.object(stub, "_run_git_read", return_value="abc1234"),
            patch.object(stub, "_default_base_branch", return_value="main"),
            patch.object(stub, "_try_rebase_for_push", return_value=True),
        ):
            result = self._run(stub, meta)

        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.SUCCESS

    @patch(_CLI_SUB)
    @patch("helping_hands.lib.github.GitHubClient")
    def test_master_rebase_fails_after_resolve_still_pushes(
        self,
        mock_gh_cls: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # _get_conflicted_files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
            # git diff
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # _get_conflicted_files after AI: resolved
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git add .
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git rebase --continue ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase --abort (after failed master rebase)
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        stub = _Stub(repo_root=tmp_path)
        stub.master_rebase = True

        mock_gh = MagicMock()
        mock_gh_cls.return_value.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh_cls.return_value.__exit__ = MagicMock(return_value=False)

        meta = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat-branch",
        }

        with (
            patch.object(stub, "_invoke_backend", new_callable=AsyncMock),
            patch.object(stub, "_push_noninteractive"),
            patch.object(stub, "_run_git_read", return_value="abc1234"),
            patch.object(stub, "_default_base_branch", return_value="main"),
            patch.object(stub, "_try_rebase_for_push", return_value=False),
        ):
            result = self._run(stub, meta)

        # Should still succeed even if master rebase fails
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.SUCCESS
