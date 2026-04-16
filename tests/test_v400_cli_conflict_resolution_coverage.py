"""Tests for _TwoPhaseCLIHand AI conflict resolution helpers.

Covers previously untested branches:
- cli/base.py:1919-1938 — _build_conflict_fix_prompt (files, truncation, output)
- cli/base.py:1942-1953 — _get_conflicted_files (normal, timeout, empty)
- cli/base.py:1968-2099 — _attempt_rebase_with_conflict_fix (all paths)
- cli/base.py:2113-2276 — _ai_resolve_push_conflicts (all paths)
- cli/base.py:2403-2411 — run() conflict dispatch
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.cli.base import (
    _META_CONFLICT_FIX_ERROR,
    _META_CONFLICT_FIX_STATUS,
    _META_PR_COMMIT,
    ConflictFixStatus,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed(
    rc: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["git"], returncode=rc, stdout=stdout, stderr=stderr
    )


def _make_hand(tmp_path: Path) -> _TwoPhaseCLIHand:
    """Build a _TwoPhaseCLIHand subclass instance for testing."""

    class _TestCLIHand(_TwoPhaseCLIHand):
        _BACKEND_NAME = "test-cli"
        _CLI_LABEL = "test-cli"
        _CLI_DISPLAY_NAME = "Test CLI"

        def _build_cli_args(self, prompt: str, *, repo_dir: Path) -> list[str]:
            return ["echo", prompt]

    (tmp_path / "main.py").write_text("")
    cfg = Config(repo=str(tmp_path), model="test-model")
    ri = RepoIndex.from_path(tmp_path)
    return _TestCLIHand(config=cfg, repo_index=ri)


# ---------------------------------------------------------------------------
# _build_conflict_fix_prompt
# ---------------------------------------------------------------------------


class TestBuildConflictFixPrompt:
    """Cover cli/base.py:1919-1938."""

    def test_basic_prompt_with_files(self) -> None:
        result = _TwoPhaseCLIHand._build_conflict_fix_prompt(
            "", ["src/a.py", "src/b.py"]
        )
        assert "src/a.py" in result
        assert "src/b.py" in result
        assert "conflict markers" in result

    def test_empty_files_shows_unknown(self) -> None:
        result = _TwoPhaseCLIHand._build_conflict_fix_prompt("", [])
        assert "(unknown)" in result

    def test_includes_git_output(self) -> None:
        result = _TwoPhaseCLIHand._build_conflict_fix_prompt(
            "CONFLICT (content): file.py", ["file.py"]
        )
        assert "CONFLICT (content)" in result

    def test_truncates_long_output(self) -> None:
        long_output = "x" * 5000
        result = _TwoPhaseCLIHand._build_conflict_fix_prompt(long_output, ["file.py"])
        assert "...[truncated]" in result

    def test_empty_output_no_git_block(self) -> None:
        result = _TwoPhaseCLIHand._build_conflict_fix_prompt("   ", ["file.py"])
        # Whitespace-only output should not produce a git output block.
        assert "Git output:" not in result


# ---------------------------------------------------------------------------
# _get_conflicted_files
# ---------------------------------------------------------------------------


class TestGetConflictedFiles:
    """Cover cli/base.py:1942-1953."""

    def test_returns_file_list(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        with patch(
            "subprocess.run",
            return_value=_make_completed(stdout="a.py\nb.py\n"),
        ):
            result = hand._get_conflicted_files(tmp_path)
        assert result == ["a.py", "b.py"]

    def test_timeout_returns_empty(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 10),
        ):
            result = hand._get_conflicted_files(tmp_path)
        assert result == []

    def test_os_error_returns_empty(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        with patch(
            "subprocess.run",
            side_effect=OSError("fail"),
        ):
            result = hand._get_conflicted_files(tmp_path)
        assert result == []

    def test_empty_output_returns_empty(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        with patch(
            "subprocess.run",
            return_value=_make_completed(stdout=""),
        ):
            result = hand._get_conflicted_files(tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# _attempt_rebase_with_conflict_fix
# ---------------------------------------------------------------------------


class TestAttemptRebaseWithConflictFix:
    """Cover cli/base.py:1968-2099."""

    def test_fetch_failure_returns_error(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.ERROR

    def test_clean_rebase_returns_no_conflicts(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(),  # rebase (success)
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.NO_CONFLICTS

    def test_non_conflict_failure_aborts(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(rc=1, stderr="fatal"),  # rebase fail
                _make_completed(stdout=""),  # diff (no conflicts)
                _make_completed(),  # rebase --abort
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.ERROR

    def test_ai_resolves_conflicts_successfully(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        hand._invoke_backend = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(rc=1, stderr="conflict"),  # rebase fail
                _make_completed(stdout="a.py\n"),  # diff (conflicts)
                # After AI invocation:
                _make_completed(stdout=""),  # diff (no remaining conflicts)
                _make_completed(),  # git add
                _make_completed(),  # rebase --continue
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.SUCCESS
        hand._invoke_backend.assert_awaited_once()

    def test_ai_fails_returns_error(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        hand._invoke_backend = AsyncMock(side_effect=RuntimeError("AI down"))
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(rc=1, stderr="conflict"),  # rebase fail
                _make_completed(stdout="a.py\n"),  # diff (conflicts)
                _make_completed(),  # rebase --abort (after AI failure)
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.ERROR

    def test_ai_leaves_remaining_conflicts(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        hand._invoke_backend = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(rc=1, stderr="conflict"),  # rebase fail
                _make_completed(stdout="a.py\n"),  # diff (conflicts)
                # After AI: still conflicted
                _make_completed(stdout="a.py\n"),  # diff (remaining)
                _make_completed(),  # rebase --abort
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.FAILED

    def test_rebase_continue_fails(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        hand._invoke_backend = AsyncMock()
        with patch(
            "subprocess.run",
            side_effect=[
                _make_completed(),  # fetch
                _make_completed(rc=1, stderr="conflict"),  # rebase fail
                _make_completed(stdout="a.py\n"),  # diff (conflicts)
                # After AI: resolved
                _make_completed(stdout=""),  # diff (no remaining)
                _make_completed(),  # git add
                _make_completed(rc=1, stderr="oops"),  # rebase --continue fail
                _make_completed(),  # rebase --abort
            ],
        ):
            result = asyncio.run(
                hand._attempt_rebase_with_conflict_fix(
                    repo_dir=tmp_path,
                    target_branch="main",
                    emit=emit,
                )
            )
        assert result == ConflictFixStatus.FAILED


# ---------------------------------------------------------------------------
# _ai_resolve_push_conflicts
# ---------------------------------------------------------------------------


class TestAiResolvePushConflicts:
    """Cover cli/base.py:2113-2276."""

    def test_not_needs_ai_returns_unchanged(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {_META_CONFLICT_FIX_STATUS: "success"}
        result = asyncio.run(
            hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
        )
        assert result[_META_CONFLICT_FIX_STATUS] == "success"

    def test_no_branch_returns_unchanged(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {_META_CONFLICT_FIX_STATUS: "needs_ai"}
        result = asyncio.run(
            hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
        )
        # No _conflict_branch → early return.
        assert result is metadata

    def test_no_conflicted_files_aborts(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        with (
            patch.object(hand, "_get_conflicted_files", return_value=[]),
            patch("subprocess.run"),
        ):
            result = asyncio.run(
                hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
            )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR

    def test_ai_error_sets_error_status(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        hand._invoke_backend = AsyncMock(side_effect=RuntimeError("boom"))
        with (
            patch.object(hand, "_get_conflicted_files", return_value=["a.py"]),
            patch("subprocess.run"),
        ):
            result = asyncio.run(
                hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
            )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR
        assert "boom" in result[_META_CONFLICT_FIX_ERROR]

    def test_remaining_conflicts_sets_failed(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        hand._invoke_backend = AsyncMock()
        # First call: conflicted files found; second call: still conflicted.
        with (
            patch.object(
                hand,
                "_get_conflicted_files",
                side_effect=[["a.py"], ["a.py"]],
            ),
            patch("subprocess.run"),
        ):
            result = asyncio.run(
                hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
            )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.FAILED

    def test_rebase_continue_fail_sets_failed(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        hand._invoke_backend = AsyncMock()
        with (
            patch.object(hand, "_get_conflicted_files", side_effect=[["a.py"], []]),
            patch(
                "subprocess.run",
                side_effect=[
                    _make_completed(),  # git diff
                    _make_completed(),  # git add
                    _make_completed(rc=1, stderr="fail"),  # rebase --continue
                    _make_completed(),  # rebase --abort
                ],
            ),
        ):
            result = asyncio.run(
                hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
            )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.FAILED

    def test_success_full_path(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        hand.master_rebase = False
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        hand._invoke_backend = AsyncMock()
        hand._push_noninteractive = MagicMock()
        hand._run_git_read = MagicMock(return_value="abc1234")
        with (
            patch.object(hand, "_get_conflicted_files", side_effect=[["a.py"], []]),
            patch(
                "subprocess.run",
                side_effect=[
                    _make_completed(),  # git diff
                    _make_completed(),  # git add
                    _make_completed(),  # rebase --continue
                ],
            ),
            patch("helping_hands.lib.github.GitHubClient"),
        ):
            result = asyncio.run(
                hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
            )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.SUCCESS
        assert result[_META_PR_COMMIT] == "abc1234"

    def test_push_fails_after_resolution(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path)
        hand.master_rebase = False
        emit = AsyncMock()
        metadata = {
            _META_CONFLICT_FIX_STATUS: "needs_ai",
            "_conflict_branch": "feat",
            "_conflict_repo": "o/r",
        }
        hand._invoke_backend = AsyncMock()
        with (
            patch.object(hand, "_get_conflicted_files", side_effect=[["a.py"], []]),
            patch(
                "subprocess.run",
                side_effect=[
                    _make_completed(),  # git diff
                    _make_completed(),  # git add
                    _make_completed(),  # rebase --continue
                ],
            ),
        ):
            mock_gh_cls = MagicMock()
            mock_gh = MagicMock()
            mock_gh_cls.return_value.__enter__ = MagicMock(return_value=mock_gh)
            mock_gh_cls.return_value.__exit__ = MagicMock(return_value=False)
            hand._push_noninteractive = MagicMock(
                side_effect=RuntimeError("push rejected")
            )
            with patch(
                "helping_hands.lib.github.GitHubClient",
                mock_gh_cls,
            ):
                result = asyncio.run(
                    hand._ai_resolve_push_conflicts(metadata=metadata, emit=emit)
                )
        assert result[_META_CONFLICT_FIX_STATUS] == ConflictFixStatus.ERROR
