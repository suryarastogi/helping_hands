"""Tests for Hand._working_tree_is_clean edge cases and GitHub project resolution.

Covers previously untested branches:
- base.py:403-404 — TimeoutExpired and OSError in _working_tree_is_clean
- base.py:407 — dirty working tree (non-empty stdout) returns False
- base.py:831 — clean working tree finalization skips commit, uses rev-parse
- github.py:949 — project ID resolution failure raises RuntimeError

These paths are important because _working_tree_is_clean silently falls through
on errors (returning False so the normal commit path runs), and project resolution
failures must surface clearly rather than producing a misleading None downstream.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.github import GitHubClient
from helping_hands.lib.hands.v1.hand import Hand, HandResponse
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Stub hand for testing static/base methods
# ---------------------------------------------------------------------------


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _working_tree_is_clean edge cases (base.py:403-404, 407)
# ---------------------------------------------------------------------------


class TestWorkingTreeIsClean:
    """Cover exception and dirty-tree branches in _working_tree_is_clean."""

    def test_timeout_returns_false(self, tmp_path: Path) -> None:
        """TimeoutExpired during git status → False (line 403-404)."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_os_error_returns_false(self, tmp_path: Path) -> None:
        """OSError (e.g. git not found) → False (line 403-404)."""
        with patch("subprocess.run", side_effect=OSError("No such file")):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_dirty_tree_returns_false(self, tmp_path: Path) -> None:
        """Non-empty stdout (dirty working tree) → False (line 407)."""
        result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout=" M src/foo.py\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_clean_tree_returns_true(self, tmp_path: Path) -> None:
        """Empty stdout with rc=0 → True (baseline sanity check)."""
        result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._working_tree_is_clean(tmp_path) is True

    def test_nonzero_returncode_returns_false(self, tmp_path: Path) -> None:
        """Non-zero exit code (e.g. not a git repo) → False."""
        result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=128,
            stdout="",
            stderr="fatal: not a git repo",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._working_tree_is_clean(tmp_path) is False

    def test_whitespace_only_stdout_is_clean(self, tmp_path: Path) -> None:
        """Whitespace-only stdout is treated as clean."""
        result = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"],
            returncode=0,
            stdout="   \n  ",
            stderr="",
        )
        with patch("subprocess.run", return_value=result):
            assert Hand._working_tree_is_clean(tmp_path) is True


# ---------------------------------------------------------------------------
# _create_new_pr with clean working tree (base.py:831)
# ---------------------------------------------------------------------------


class TestPushToExistingPrCleanTree:
    """Cover the clean-tree branch in _push_to_existing_pr (line 831)."""

    def test_clean_tree_uses_rev_parse(
        self, repo_index: RepoIndex, tmp_path: Path
    ) -> None:
        """When working tree is clean, rev-parse HEAD is used (line 831)."""
        hand = _StubHand(Config(repo="owner/repo", model="test-model"), repo_index)
        hand.pr_number = 42
        hand.issue_number = None

        hand._working_tree_is_clean = MagicMock(return_value=True)  # type: ignore[assignment]
        hand._run_git_read = MagicMock(return_value="abc1234")  # type: ignore[assignment]
        hand._push_noninteractive = MagicMock()  # type: ignore[assignment]
        hand._post_issue_link_comment = MagicMock()  # type: ignore[assignment]

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "feature-branch",
            "base": "main",
            "url": "https://github.com/owner/repo/pull/42",
            "user": "bot",
        }
        mock_gh.whoami.return_value = {"login": "other-user"}

        result = hand._push_to_existing_pr(
            gh=mock_gh,
            repo="owner/repo",
            repo_dir=tmp_path,
            backend="basic-langgraph",
            prompt="fix bug",
            summary="Fixed it",
            metadata={},
        )

        # Should have called rev-parse (clean path), not commit
        hand._run_git_read.assert_called_once_with(
            tmp_path, "rev-parse", "--short", "HEAD"
        )
        assert result["pr_commit"] == "abc1234"


# ---------------------------------------------------------------------------
# add_to_project_v2 — project resolution failure (github.py:949)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _ensure_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")


@pytest.fixture()
def client() -> GitHubClient:
    with patch("helping_hands.lib.github.Github"):
        return GitHubClient()


class TestAddToProjectV2ProjectResolutionFailure:
    """Cover RuntimeError when project ID cannot be resolved (line 949)."""

    def test_org_project_not_found_raises(self, client: GitHubClient) -> None:
        """Organization project query returns empty → RuntimeError."""
        responses = [
            # org project query returns no projectV2 key
            {"data": {"organization": {}}},
        ]
        call_count = {"n": 0}

        def mock_urlopen(req: Any) -> MagicMock:
            import json

            resp = MagicMock()
            resp.read.return_value = json.dumps(responses[call_count["n"]]).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            call_count["n"] += 1
            return resp

        with (
            patch("helping_hands.lib.github.urllib.request.urlopen", mock_urlopen),
            pytest.raises(RuntimeError, match="Could not resolve project ID"),
        ):
            client.add_to_project_v2(
                "https://github.com/orgs/myorg/projects/999",
                content_id="I_abc123",
            )

    def test_user_project_not_found_raises(self, client: GitHubClient) -> None:
        """User project query returns empty → RuntimeError."""
        responses = [
            # user project query returns no projectV2 key
            {"data": {"user": {}}},
        ]
        call_count = {"n": 0}

        def mock_urlopen(req: Any) -> MagicMock:
            import json

            resp = MagicMock()
            resp.read.return_value = json.dumps(responses[call_count["n"]]).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            call_count["n"] += 1
            return resp

        with (
            patch("helping_hands.lib.github.urllib.request.urlopen", mock_urlopen),
            pytest.raises(RuntimeError, match="Could not resolve project ID"),
        ):
            client.add_to_project_v2(
                "https://github.com/users/alice/projects/999",
                content_id="I_abc123",
            )

    def test_org_project_missing_key_raises(self, client: GitHubClient) -> None:
        """Organization query returns data but no 'organization' key."""
        responses = [
            {"data": {}},
        ]
        call_count = {"n": 0}

        def mock_urlopen(req: Any) -> MagicMock:
            import json

            resp = MagicMock()
            resp.read.return_value = json.dumps(responses[call_count["n"]]).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            call_count["n"] += 1
            return resp

        with (
            patch("helping_hands.lib.github.urllib.request.urlopen", mock_urlopen),
            pytest.raises(RuntimeError, match="Could not resolve project ID"),
        ):
            client.add_to_project_v2(
                "https://github.com/orgs/myorg/projects/5",
                content_id="I_abc123",
            )
