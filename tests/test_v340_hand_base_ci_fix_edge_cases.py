"""Tests for Hand._working_tree_is_clean and CI fix edge cases.

Covers previously untested branches:
- ``_working_tree_is_clean`` (base.py:403-404, 407): TimeoutExpired, OSError,
  clean/dirty stdout, and non-zero returncode paths.  This static method had
  zero direct unit tests — it was always mocked by other test suites.
- ``_poll_ci_checks`` wait ≤ 0 break (cli/base.py:1535): the deadline-reached
  path that breaks out of the poll loop before sleeping.
- ``_ci_fix_loop`` loop timeout (cli/base.py:1718-1727): the monotonic
  deadline guard that emits a timeout message and returns EXHAUSTED.

A regression in _working_tree_is_clean returning True on errors would cause
the finalization flow to skip the commit-and-push step, silently losing work.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from helping_hands.lib.hands.v1.hand.base import Hand

_CLI_BASE_MOD = "helping_hands.lib.hands.v1.hand.cli.base"


# ---------------------------------------------------------------------------
# _working_tree_is_clean — direct unit tests
# ---------------------------------------------------------------------------


class TestWorkingTreeIsClean:
    """Tests for the static Hand._working_tree_is_clean method."""

    def test_timeout_expired_returns_false(self, tmp_path: Path) -> None:
        """TimeoutExpired during git status should return False."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_os_error_returns_false(self, tmp_path: Path) -> None:
        """OSError (e.g. git not found) should return False."""
        with patch("subprocess.run", side_effect=OSError("No such file")):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_nonzero_returncode_returns_false(self, tmp_path: Path) -> None:
        """Non-zero exit code (e.g. not a git repo) should return False."""
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_dirty_tree_returns_false(self, tmp_path: Path) -> None:
        """Non-empty stdout (porcelain output) means dirty tree."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = " M src/main.py\n"
        with patch("subprocess.run", return_value=mock_result):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_clean_tree_returns_true(self, tmp_path: Path) -> None:
        """Empty stdout with returncode 0 means clean tree."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            assert Hand._working_tree_is_clean(tmp_path) is True


# ---------------------------------------------------------------------------
# _poll_ci_checks — wait ≤ 0 break path
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


class TestPollCiChecksDeadlineBreak:
    """Test _poll_ci_checks breaks when remaining wait is ≤ 0."""

    def test_break_when_wait_le_zero(self) -> None:
        """When monotonic deadline is reached mid-loop, poll should break
        and do a final get_check_runs instead of sleeping."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        stub = MagicMock(spec=_TwoPhaseCLIHand)
        stub._label_msg = lambda msg: f"[stub] {msg}"

        mock_gh = MagicMock()
        # First call: pending (enters loop body)
        # Second call: final result after break
        mock_gh.get_check_runs.side_effect = [
            {"conclusion": "pending", "total_count": 1},
            {"conclusion": "success", "total_count": 1},
        ]

        emit_chunks: list[str] = []

        async def emit(chunk: str) -> None:
            emit_chunks.append(chunk)

        # Simulate time advancing past deadline between the while-condition
        # check and the remaining-time calculation.
        call_count = 0
        base_time = 1000.0

        def fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # deadline setup (line 1526) + while condition (line 1527)
                return base_time
            # remaining-time calc (line 1532): past deadline
            return base_time + 99999

        with (
            patch(f"{_CLI_BASE_MOD}.time") as mock_time,
            patch(f"{_CLI_BASE_MOD}.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_time.monotonic = fake_monotonic

            result = _run(
                _TwoPhaseCLIHand._poll_ci_checks(
                    stub,
                    gh=mock_gh,
                    repo="owner/repo",
                    ref="abc123",
                    emit=emit,
                    initial_wait=0.001,
                    max_poll_seconds=0.001,
                )
            )

        # Should have called get_check_runs twice: once in loop, once final
        assert mock_gh.get_check_runs.call_count == 2
        assert result["conclusion"] == "success"


# ---------------------------------------------------------------------------
# _ci_fix_loop — monotonic loop timeout
# ---------------------------------------------------------------------------


class TestCiFixLoopTimeout:
    """Test _ci_fix_loop exits with EXHAUSTED when loop deadline is exceeded."""

    def test_loop_deadline_exceeded(self) -> None:
        """When time.monotonic() > loop_deadline on first iteration, the loop
        should emit a timeout message and return with EXHAUSTED status."""
        from helping_hands.lib.hands.v1.hand.cli.base import (
            CIFixStatus,
            _TwoPhaseCLIHand,
        )

        stub = MagicMock()
        stub._label_msg = lambda msg: f"[stub] {msg}"
        stub._is_interrupted = MagicMock(return_value=False)
        stub.fix_ci = True
        stub.auto_pr = True
        stub.ci_check_wait_minutes = 0.001
        stub.ci_max_retries = 3
        stub.config = MagicMock()
        stub.config.github_token = "fake-token"
        stub.repo_index = MagicMock()
        stub.repo_index.root.resolve.return_value = Path("/fake/repo")

        meta = {"pr_status": "created", "pr_commit": "abc", "pr_branch": "b"}

        emit_chunks: list[str] = []

        async def emit(chunk: str) -> None:
            emit_chunks.append(chunk)

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        # First monotonic() call sets loop_deadline = 0.0 + 1800.
        # Second call (in the for-loop check) returns far past deadline.
        call_count = 0

        def fake_monotonic() -> float:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 0.0
            return 99999.0

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch(f"{_CLI_BASE_MOD}.time") as mock_time,
            patch(f"{_CLI_BASE_MOD}.os.environ", {"HELPING_HANDS_CI_MAX_RETRIES": ""}),
        ):
            mock_time.monotonic = fake_monotonic

            result = _run(
                _TwoPhaseCLIHand._ci_fix_loop(
                    stub,
                    prompt="fix",
                    metadata=meta,
                    emit=emit,
                )
            )

        assert result["ci_fix_status"] == CIFixStatus.EXHAUSTED
        timeout_msgs = [c for c in emit_chunks if "timed out" in c]
        assert len(timeout_msgs) == 1
