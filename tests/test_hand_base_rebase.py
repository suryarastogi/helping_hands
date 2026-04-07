"""Tests for Hand base rebase and push-to-existing-PR conflict paths.

Covers ``_try_rebase_for_push`` (fetch, rebase success, conflicts-left-for-AI,
non-conflict abort), ``_default_base_branch`` (git symbolic-ref success path),
and ``_push_to_existing_pr`` (master_rebase success/fail, fix_conflicts
rebase-ok/push-fail, rebase-fail → needs_ai).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import (
    _DEFAULT_BASE_BRANCH,
    _META_CONFLICT_FIX_STATUS,
    Hand,
    HandResponse,
)
from helping_hands.lib.repo import RepoIndex

# repo_index fixture provided by conftest.py


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _default_base_branch — success path (git symbolic-ref returns a ref)
# ---------------------------------------------------------------------------


class TestDefaultBaseBranchSuccess:
    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_returns_branch_from_symbolic_ref(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="refs/remotes/origin/master\n", stderr="",
        )
        result = Hand._default_base_branch(tmp_path)
        assert result == "master"

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_returns_main_from_symbolic_ref(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="refs/remotes/origin/main\n", stderr="",
        )
        result = Hand._default_base_branch(tmp_path)
        assert result == "main"

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_empty_ref_falls_back_to_default(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        result = Hand._default_base_branch(tmp_path)
        assert result == _DEFAULT_BASE_BRANCH


# ---------------------------------------------------------------------------
# _try_rebase_for_push — subprocess-mocked paths
# ---------------------------------------------------------------------------

_BASE_SUB = "helping_hands.lib.hands.v1.hand.base.subprocess.run"


class TestTryRebaseForPush:
    def _make_hand(self, tmp_path: Path) -> _StubHand:
        config = Config.from_env()
        hand = _StubHand.__new__(_StubHand)
        hand.config = config
        hand.repo_index = RepoIndex(root=tmp_path, files=[])
        return hand

    @patch(_BASE_SUB)
    def test_fetch_failure_returns_false(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git fetch")
        gh = MagicMock()
        hand = self._make_hand(tmp_path)
        assert hand._try_rebase_for_push(gh, tmp_path, "main") is False

    @patch(_BASE_SUB)
    def test_fetch_timeout_returns_false(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=60)
        gh = MagicMock()
        hand = self._make_hand(tmp_path)
        assert hand._try_rebase_for_push(gh, tmp_path, "main") is False

    @patch(_BASE_SUB)
    def test_rebase_success_returns_true(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # fetch ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        gh = MagicMock()
        hand = self._make_hand(tmp_path)
        assert hand._try_rebase_for_push(gh, tmp_path, "main") is True

    @patch(_BASE_SUB)
    def test_rebase_conflicts_left_for_ai(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # fetch ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase fails
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="CONFLICT", stderr=""
            ),
            # git diff shows conflicted files
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="foo.py\n", stderr=""
            ),
        ]
        gh = MagicMock()
        hand = self._make_hand(tmp_path)
        # Returns False but leaves rebase in progress
        assert hand._try_rebase_for_push(gh, tmp_path, "main") is False

    @patch(_BASE_SUB)
    def test_rebase_non_conflict_aborts(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        mock_run.side_effect = [
            # fetch ok
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase fails
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="fatal: bad revision"
            ),
            # git diff shows NO conflicted files
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # rebase --abort
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        gh = MagicMock()
        hand = self._make_hand(tmp_path)
        assert hand._try_rebase_for_push(gh, tmp_path, "main") is False
        # Verify rebase --abort was called (4th subprocess call)
        assert mock_run.call_count == 4


# ---------------------------------------------------------------------------
# _push_to_existing_pr — master_rebase path
# ---------------------------------------------------------------------------


class TestPushToExistingPrMasterRebase:
    def _make_hand(self, tmp_path: Path) -> _StubHand:
        config = Config.from_env()
        hand = _StubHand.__new__(_StubHand)
        hand.config = config
        hand.repo_index = RepoIndex(root=tmp_path, files=[])
        hand.pr_number = 42
        hand.master_rebase = True
        hand.fix_conflicts = False
        hand.auto_pr = True
        hand.no_pr = False
        hand.issue_number = None
        hand.last_pr_metadata = {}
        return hand

    @patch(_BASE_SUB)
    def test_master_rebase_success_updates_sha(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        gh.get_pr.return_value = {
            "head": "feat-branch",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }

        with (
            patch.object(hand, "_working_tree_is_clean", return_value=True),
            patch.object(hand, "_run_git_read", return_value="abc1234"),
            patch.object(hand, "_default_base_branch", return_value="main"),
            patch.object(hand, "_try_rebase_for_push", return_value=True),
            patch.object(hand, "_push_noninteractive"),
            patch.object(hand, "_update_pr_description"),
            patch.object(hand, "_post_issue_link_comment"),
        ):
            result = hand._push_to_existing_pr(
                gh=gh, repo="owner/repo", repo_dir=tmp_path,
                backend="stub", prompt="fix bug", summary="done",
                metadata={},
            )
        assert result.get("pr_commit") == "abc1234"

    @patch(_BASE_SUB)
    def test_master_rebase_fails_aborts_and_continues(
        self, mock_run: MagicMock, tmp_path: Path,
    ) -> None:
        # rebase --abort subprocess call
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        gh.get_pr.return_value = {
            "head": "feat-branch",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }

        with (
            patch.object(hand, "_working_tree_is_clean", return_value=True),
            patch.object(hand, "_run_git_read", return_value="abc1234"),
            patch.object(hand, "_default_base_branch", return_value="main"),
            patch.object(hand, "_try_rebase_for_push", return_value=False),
            patch.object(hand, "_push_noninteractive"),
            patch.object(hand, "_update_pr_description"),
            patch.object(hand, "_post_issue_link_comment"),
        ):
            result = hand._push_to_existing_pr(
                gh=gh, repo="owner/repo", repo_dir=tmp_path,
                backend="stub", prompt="fix bug", summary="done",
                metadata={},
            )
        # Should still succeed (push continues despite rebase failure)
        assert "pr_status" in result
        # rebase --abort was called
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# _push_to_existing_pr — fix_conflicts path
# ---------------------------------------------------------------------------


class TestPushToExistingPrFixConflicts:
    def _make_hand(self, tmp_path: Path) -> _StubHand:
        config = Config.from_env()
        hand = _StubHand.__new__(_StubHand)
        hand.config = config
        hand.repo_index = RepoIndex(root=tmp_path, files=[])
        hand.pr_number = 42
        hand.master_rebase = False
        hand.fix_conflicts = True
        hand.auto_pr = True
        hand.no_pr = False
        hand.issue_number = None
        hand.last_pr_metadata = {}
        return hand

    def test_fix_conflicts_rebase_ok_push_ok(self, tmp_path: Path) -> None:
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        gh.get_pr.return_value = {
            "head": "feat-branch",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }

        push_call_count = 0

        def _push_side_effect(*args: object, **kwargs: object) -> None:
            nonlocal push_call_count
            push_call_count += 1
            if push_call_count == 1:
                raise RuntimeError("push rejected")
            # Second call succeeds

        with (
            patch.object(hand, "_working_tree_is_clean", return_value=True),
            patch.object(hand, "_run_git_read", return_value="abc1234"),
            patch.object(hand, "_try_rebase_for_push", return_value=True),
            patch.object(hand, "_push_noninteractive", side_effect=_push_side_effect),
            patch.object(hand, "_update_pr_description"),
            patch.object(hand, "_post_issue_link_comment"),
        ):
            result = hand._push_to_existing_pr(
                gh=gh, repo="owner/repo", repo_dir=tmp_path,
                backend="stub", prompt="fix bug", summary="done",
                metadata={},
            )
        assert result.get("pr_status") == "updated"

    def test_fix_conflicts_rebase_ok_push_still_fails_diverged(
        self, tmp_path: Path,
    ) -> None:
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        gh.get_pr.return_value = {
            "head": "feat-branch",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }

        with (
            patch.object(hand, "_working_tree_is_clean", return_value=True),
            patch.object(hand, "_run_git_read", return_value="abc1234"),
            patch.object(hand, "_try_rebase_for_push", return_value=True),
            patch.object(
                hand, "_push_noninteractive", side_effect=RuntimeError("rejected")
            ),
            patch.object(
                hand, "_create_pr_for_diverged_branch", return_value={"pr_status": "created"}
            ),
        ):
            result = hand._push_to_existing_pr(
                gh=gh, repo="owner/repo", repo_dir=tmp_path,
                backend="stub", prompt="fix bug", summary="done",
                metadata={},
            )
        assert result.get("pr_status") == "created"

    def test_fix_conflicts_rebase_fails_needs_ai(self, tmp_path: Path) -> None:
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        gh.get_pr.return_value = {
            "head": "feat-branch",
            "base": "main",
            "url": "https://github.com/o/r/pull/42",
            "user": "bot",
        }

        with (
            patch.object(hand, "_working_tree_is_clean", return_value=True),
            patch.object(hand, "_run_git_read", return_value="abc1234"),
            patch.object(hand, "_try_rebase_for_push", return_value=False),
            patch.object(
                hand, "_push_noninteractive", side_effect=RuntimeError("rejected")
            ),
        ):
            result = hand._push_to_existing_pr(
                gh=gh, repo="owner/repo", repo_dir=tmp_path,
                backend="stub", prompt="fix bug", summary="done",
                metadata={},
            )
        assert result.get(_META_CONFLICT_FIX_STATUS) == "needs_ai"
        assert result.get("_conflict_branch") == "feat-branch"
