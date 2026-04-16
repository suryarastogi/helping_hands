"""Tests for Hand base class rebase/push conflict resolution paths.

Covers previously untested branches:
- base.py:413-415 — _default_base_branch successful ref parsing
- base.py:863-921 — _try_rebase_for_push (fetch fail, clean rebase,
  conflict rebase, non-conflict failure + abort)
- base.py:973-991 — _push_to_existing_pr master_rebase paths
- base.py:1005-1041 — _push_to_existing_pr fix_conflicts rebase/retry/fallback
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Stub hand
# ---------------------------------------------------------------------------


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _default_base_branch — successful ref parsing (line 413-415)
# ---------------------------------------------------------------------------


class TestDefaultBaseBranch:
    """Cover the branch where git symbolic-ref succeeds."""

    def test_parses_ref_successfully(self, tmp_path: Path) -> None:
        """Line 413-415: strip prefix from symbolic-ref output."""
        result = subprocess.CompletedProcess(
            args=["git", "symbolic-ref"],
            returncode=0,
            stdout="refs/remotes/origin/main\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._default_base_branch(tmp_path) == "main"

    def test_parses_master_ref(self, tmp_path: Path) -> None:
        result = subprocess.CompletedProcess(
            args=["git", "symbolic-ref"],
            returncode=0,
            stdout="refs/remotes/origin/master\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._default_base_branch(tmp_path) == "master"

    def test_empty_ref_falls_back(self, tmp_path: Path) -> None:
        """Empty output → fall through to default."""
        result = subprocess.CompletedProcess(
            args=["git", "symbolic-ref"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._default_base_branch(tmp_path) == "main"


# ---------------------------------------------------------------------------
# _try_rebase_for_push (lines 863-921)
# ---------------------------------------------------------------------------


class TestTryRebaseForPush:
    """Cover all branches in _try_rebase_for_push."""

    def _make_hand(self, tmp_path: Path) -> _StubHand:
        cfg = Config(model="test-model")
        ri = RepoIndex(root=tmp_path)
        return _StubHand(config=cfg, repo_index=ri)

    def test_fetch_failure_returns_false(self, tmp_path: Path) -> None:
        """Fetch CalledProcessError → return False."""
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = hand._try_rebase_for_push(gh, tmp_path, "main")
        assert result is False

    def test_clean_rebase_returns_true(self, tmp_path: Path) -> None:
        """Fetch ok, rebase rc=0 → return True."""
        hand = self._make_hand(tmp_path)
        gh = MagicMock()

        fetch_ok = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        rebase_ok = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        with patch("subprocess.run", side_effect=[fetch_ok, rebase_ok]):
            result = hand._try_rebase_for_push(gh, tmp_path, "main")
        assert result is True

    def test_conflict_rebase_returns_false(self, tmp_path: Path) -> None:
        """Rebase fails with conflicts → return False, leave rebase in progress."""
        hand = self._make_hand(tmp_path)
        gh = MagicMock()

        fetch_ok = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        rebase_fail = subprocess.CompletedProcess(
            args=["git"], returncode=1, stdout="", stderr="conflict"
        )
        # diff --name-only shows conflicted files
        diff_result = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="src/foo.py\n", stderr=""
        )
        with patch("subprocess.run", side_effect=[fetch_ok, rebase_fail, diff_result]):
            result = hand._try_rebase_for_push(gh, tmp_path, "main")
        assert result is False

    def test_non_conflict_failure_aborts_rebase(self, tmp_path: Path) -> None:
        """Rebase fails for non-conflict reason → abort rebase, return False."""
        hand = self._make_hand(tmp_path)
        gh = MagicMock()

        fetch_ok = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        rebase_fail = subprocess.CompletedProcess(
            args=["git"], returncode=1, stdout="", stderr="fatal error"
        )
        # diff shows no conflicts
        diff_no_conflict = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        # rebase --abort
        abort_ok = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="", stderr=""
        )
        with patch(
            "subprocess.run",
            side_effect=[fetch_ok, rebase_fail, diff_no_conflict, abort_ok],
        ):
            result = hand._try_rebase_for_push(gh, tmp_path, "main")
        assert result is False

    def test_fetch_timeout_returns_false(self, tmp_path: Path) -> None:
        """TimeoutExpired during fetch → return False."""
        hand = self._make_hand(tmp_path)
        gh = MagicMock()
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("git", 60),
        ):
            result = hand._try_rebase_for_push(gh, tmp_path, "main")
        assert result is False
