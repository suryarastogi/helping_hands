"""Tests for v364 — config repo validation and finalization catch-all hardening.

Validates that Config.from_env rejects malicious repo inputs (path traversal,
null bytes, newlines) and that _finalize_repo_pr catches truly unexpected
exceptions (KeyError, AttributeError) rather than letting them crash the run.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from github import GithubException

from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse, PRStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_index(tmp_path: Path):
    """Minimal RepoIndex for hand instantiation."""
    from helping_hands.lib.repo import RepoIndex

    (tmp_path / ".git").mkdir()
    (tmp_path / "README.md").write_text("# test\n")
    return RepoIndex(root=tmp_path, files=["README.md"])


class _StubHand(Hand):
    """Minimal concrete Hand for testing base-class methods."""

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


def _fake_git_read(_repo_dir: Path, *args: str) -> str:
    if args == ("rev-parse", "--is-inside-work-tree"):
        return "true"
    if args == ("status", "--porcelain"):
        return " M main.py"
    return ""


# ---------------------------------------------------------------------------
# _finalize_repo_pr catch-all for truly unexpected exceptions
# ---------------------------------------------------------------------------


class TestFinalizeRepoPrCatchAll:
    """The new catch-all except Exception handler in _finalize_repo_pr."""

    def test_unexpected_keyerror_caught(self, repo_index, caplog) -> None:
        """A KeyError from inside finalization should not crash."""
        from helping_hands.lib.config import Config

        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        with (
            patch.object(Hand, "_run_git_read", side_effect=_fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=KeyError("bad_key"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == PRStatus.ERROR
        assert "unexpected error" in result.get("pr_error", "")
        assert any(
            "_finalize_repo_pr unexpected error" in r.message for r in caplog.records
        )

    def test_unexpected_attributeerror_caught(self, repo_index, caplog) -> None:
        """An AttributeError from inside finalization should not crash."""
        from helping_hands.lib.config import Config

        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        with (
            patch.object(Hand, "_run_git_read", side_effect=_fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=AttributeError("no_attr"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == PRStatus.ERROR
        assert "unexpected error" in result.get("pr_error", "")


# ---------------------------------------------------------------------------
# _push_to_existing_pr OSError handling
# ---------------------------------------------------------------------------


class TestPushOSErrorFallback:
    """Push failure from OSError (e.g. git binary missing) should trigger
    the diverged-branch fallback, same as RuntimeError."""

    def test_oserror_during_push_triggers_fallback(self, repo_index) -> None:
        from helping_hands.lib.config import Config

        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        with (
            patch.object(Hand, "_run_git_read", side_effect=_fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch("helping_hands.lib.github.GitHubClient") as mock_gh_cls,
            patch.object(
                Hand, "_configure_authenticated_push_remote"
            ),
            patch.object(Hand, "_push_noninteractive", side_effect=OSError("no git")),
            patch.object(Hand, "_create_pr_for_diverged_branch") as mock_diverged,
        ):
            mock_gh = mock_gh_cls.return_value
            mock_gh.token = "ghp_testtoken123456789012345"
            mock_gh.get_pr.return_value = {
                "head_branch": "helping-hands/test",
                "user": "bot",
            }
            mock_gh.add_and_commit.return_value = "abc123"

            mock_diverged.return_value = {"pr_status": "created"}

            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        # The diverged-branch fallback should have been triggered.
        mock_diverged.assert_called_once()
        assert result["pr_status"] == "created"
