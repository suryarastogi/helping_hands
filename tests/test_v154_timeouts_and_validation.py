"""Ensures git subprocess calls honour timeout constants and degrade gracefully.

_get_diff and _get_uncommitted_diff must catch TimeoutExpired and return an
empty string so a slow git-diff does not abort the entire task -- a missing
diff is recoverable (the PR still opens), but an unhandled exception is not.
The "passes timeout param" tests verify the constant is actually forwarded to
subprocess.run; without them the constant could exist as dead code while git
hangs indefinitely on large repos.

_GIT_CLONE_TIMEOUT_S is tested for both cli/main.py and celery_app.py to
ensure the owner/repo auto-clone path cannot block a worker forever.
read_text_file max_chars validation prevents callers from passing non-positive
limits that would silently return empty content.
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import (
    _GIT_CLONE_TIMEOUT_S as CLI_GIT_CLONE_TIMEOUT_S,
    _resolve_repo_path as cli_resolve_repo_path,
)
from helping_hands.lib.hands.v1.hand.pr_description import (
    _GIT_DIFF_TIMEOUT_S,
    _get_diff,
    _get_uncommitted_diff,
)
from helping_hands.lib.meta.tools.filesystem import read_text_file

# ---------------------------------------------------------------------------
# pr_description.py — _GIT_DIFF_TIMEOUT_S constant tests
# ---------------------------------------------------------------------------


class TestGitDiffTimeoutConstant:
    """Verify _GIT_DIFF_TIMEOUT_S constant properties."""

    def test_value(self) -> None:
        assert _GIT_DIFF_TIMEOUT_S == 30

    def test_type(self) -> None:  # TODO: CLEANUP CANDIDATE
        assert isinstance(_GIT_DIFF_TIMEOUT_S, int)

    def test_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        assert _GIT_DIFF_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# pr_description.py — _get_diff timeout handling
# ---------------------------------------------------------------------------


class TestGetDiffTimeout:
    """Verify _get_diff handles TimeoutExpired gracefully."""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_on_base_branch_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First diff (base_branch...HEAD) times out → returns empty string."""
        mock_run.side_effect = TimeoutExpired(cmd=["git", "diff"], timeout=30)
        assert _get_diff(tmp_path, base_branch="main") == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_on_fallback_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """First diff fails (rc!=0), fallback (HEAD~1) times out → empty."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
            TimeoutExpired(cmd=["git", "diff"], timeout=30),
        ]
        assert _get_diff(tmp_path, base_branch="main") == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_passes_timeout_param(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Subprocess call includes timeout=_GIT_DIFF_TIMEOUT_S."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="diff content\n"
        )
        _get_diff(tmp_path, base_branch="main")
        assert mock_run.call_args.kwargs.get("timeout") == _GIT_DIFF_TIMEOUT_S


# ---------------------------------------------------------------------------
# pr_description.py — _get_uncommitted_diff timeout handling
# ---------------------------------------------------------------------------


class TestGetUncommittedDiffTimeout:
    """Verify _get_uncommitted_diff handles TimeoutExpired gracefully."""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_on_git_add_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git add . times out → returns empty string."""
        mock_run.side_effect = TimeoutExpired(cmd=["git", "add"], timeout=30)
        assert _get_uncommitted_diff(tmp_path) == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_returns_empty_on_git_diff_cached_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git add succeeds, git diff --cached times out → empty."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            TimeoutExpired(cmd=["git", "diff"], timeout=30),
        ]
        assert _get_uncommitted_diff(tmp_path) == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_passes_timeout_to_git_add(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git add . subprocess call includes timeout parameter."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="diff content\n"),
        ]
        _get_uncommitted_diff(tmp_path)
        assert mock_run.call_args_list[0].kwargs.get("timeout") == _GIT_DIFF_TIMEOUT_S

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_passes_timeout_to_git_diff_cached(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """git diff --cached subprocess call includes timeout parameter."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="diff content\n"),
        ]
        _get_uncommitted_diff(tmp_path)
        assert mock_run.call_args_list[1].kwargs.get("timeout") == _GIT_DIFF_TIMEOUT_S


# ---------------------------------------------------------------------------
# cli/main.py — _GIT_CLONE_TIMEOUT_S constant tests
# ---------------------------------------------------------------------------


class TestCliGitCloneTimeoutConstant:
    """Verify cli/main.py _GIT_CLONE_TIMEOUT_S constant properties."""

    def test_value(self) -> None:
        assert CLI_GIT_CLONE_TIMEOUT_S == 120

    def test_type(self) -> None:  # TODO: CLEANUP CANDIDATE
        assert isinstance(CLI_GIT_CLONE_TIMEOUT_S, int)

    def test_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        assert CLI_GIT_CLONE_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# cli/main.py — _resolve_repo_path clone timeout handling
# ---------------------------------------------------------------------------


class TestCliResolveRepoPathCloneTimeout:
    """Verify cli/main.py _resolve_repo_path handles clone timeout."""

    @patch("helping_hands.cli.main.subprocess.run")
    @patch(
        "helping_hands.cli.main._github_clone_url",
        return_value="https://example.com/owner/repo.git",
    )
    @patch("helping_hands.cli.main._git_noninteractive_env", return_value={})
    def test_raises_value_error_on_clone_timeout(
        self,
        _mock_env: MagicMock,
        _mock_url: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """Clone timeout raises ValueError with descriptive message."""
        mock_run.side_effect = TimeoutExpired(cmd=["git", "clone"], timeout=120)
        with pytest.raises(ValueError, match="timed out"):
            cli_resolve_repo_path("owner/repo")

    @patch("helping_hands.cli.main.subprocess.run")
    @patch(
        "helping_hands.cli.main._github_clone_url",
        return_value="https://example.com/owner/repo.git",
    )
    @patch("helping_hands.cli.main._git_noninteractive_env", return_value={})
    def test_clone_passes_timeout_param(
        self,
        _mock_env: MagicMock,
        _mock_url: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Subprocess clone call includes timeout=_GIT_CLONE_TIMEOUT_S."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with patch("helping_hands.cli.main.mkdtemp", return_value=str(tmp_path)):
            (tmp_path / "repo").mkdir(exist_ok=True)
            with contextlib.suppress(Exception):
                cli_resolve_repo_path("owner/repo")
        assert mock_run.call_args.kwargs.get("timeout") == CLI_GIT_CLONE_TIMEOUT_S


# ---------------------------------------------------------------------------
# celery_app.py — _GIT_CLONE_TIMEOUT_S constant tests
# ---------------------------------------------------------------------------


class TestCeleryGitCloneTimeoutConstant:
    """Verify celery_app.py _GIT_CLONE_TIMEOUT_S constant properties."""

    def test_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _GIT_CLONE_TIMEOUT_S

        assert _GIT_CLONE_TIMEOUT_S == 120

    def test_type(self) -> None:  # TODO: CLEANUP CANDIDATE
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _GIT_CLONE_TIMEOUT_S

        assert isinstance(_GIT_CLONE_TIMEOUT_S, int)

    def test_positive(self) -> None:  # TODO: CLEANUP CANDIDATE
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _GIT_CLONE_TIMEOUT_S

        assert _GIT_CLONE_TIMEOUT_S > 0

    def test_matches_cli_value(self) -> None:
        """Clone timeout is consistent across cli/main.py and celery_app.py."""
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _GIT_CLONE_TIMEOUT_S

        assert _GIT_CLONE_TIMEOUT_S == CLI_GIT_CLONE_TIMEOUT_S


class TestCeleryResolveRepoPathCloneTimeout:
    """Verify celery_app.py _resolve_repo_path handles clone timeout."""

    def test_raises_value_error_on_clone_timeout(self) -> None:
        """Clone timeout raises ValueError with descriptive message."""
        pytest.importorskip("celery")
        from helping_hands.server import celery_app

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                side_effect=TimeoutExpired(cmd=["git", "clone"], timeout=120),
            ),
            patch(
                "helping_hands.server.celery_app._github_clone_url",
                return_value="https://example.com/owner/repo.git",
            ),
            patch(
                "helping_hands.server.celery_app._git_noninteractive_env",
                return_value={},
            ),
            pytest.raises(ValueError, match="timed out"),
        ):
            celery_app._resolve_repo_path("owner/repo")

    def test_clone_passes_timeout_param(self, tmp_path: Path) -> None:
        """Subprocess clone call includes timeout=_GIT_CLONE_TIMEOUT_S."""
        pytest.importorskip("celery")
        from helping_hands.server import celery_app

        mock_run = MagicMock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
        )
        with (
            patch("helping_hands.server.celery_app.subprocess.run", mock_run),
            patch(
                "helping_hands.server.celery_app._github_clone_url",
                return_value="https://example.com/owner/repo.git",
            ),
            patch(
                "helping_hands.server.celery_app._git_noninteractive_env",
                return_value={},
            ),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value=str(tmp_path),
            ),
        ):
            (tmp_path / "repo").mkdir(exist_ok=True)
            with contextlib.suppress(Exception):
                celery_app._resolve_repo_path("owner/repo")
            assert (
                mock_run.call_args.kwargs.get("timeout")
                == celery_app._GIT_CLONE_TIMEOUT_S
            )


# ---------------------------------------------------------------------------
# filesystem.py — read_text_file max_chars validation
# ---------------------------------------------------------------------------


class TestReadTextFileMaxCharsValidation:
    """Verify read_text_file rejects non-positive max_chars values."""

    def test_rejects_zero_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_chars must be positive"):
            read_text_file(tmp_path, "file.txt", max_chars=0)

    def test_rejects_negative_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_chars must be positive"):
            read_text_file(tmp_path, "file.txt", max_chars=-1)

    def test_rejects_large_negative_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="max_chars must be positive"):
            read_text_file(tmp_path, "file.txt", max_chars=-100)

    def test_accepts_positive_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello world")
        text, truncated, _ = read_text_file(tmp_path, "file.txt", max_chars=5)
        assert text == "hello"
        assert truncated is True

    def test_accepts_none_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        text, truncated, _ = read_text_file(tmp_path, "file.txt", max_chars=None)
        assert text == "hello"
        assert truncated is False

    def test_error_message_includes_value(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(ValueError, match="-5"):
            read_text_file(tmp_path, "file.txt", max_chars=-5)
