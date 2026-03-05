"""Tests for Hand base class static/classmethods and helper methods.

Covers edge cases in _github_repo_from_origin, _run_precommit_checks_and_fixes,
_push_noninteractive, and _push_to_existing_pr.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_index(tmp_path: Path) -> RepoIndex:
    (tmp_path / "main.py").write_text("")
    return RepoIndex.from_path(tmp_path)


class _StubHand(Hand):
    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str):  # type: ignore[override]
        yield prompt


# ---------------------------------------------------------------------------
# _github_repo_from_origin — edge cases
# ---------------------------------------------------------------------------


class TestGithubRepoFromOriginEdgeCases:
    @patch.object(Hand, "_run_git_read", return_value="")
    def test_empty_remote_returns_empty(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == ""

    @patch.object(
        Hand, "_run_git_read", return_value="https://gitlab.com/owner/repo.git"
    )
    def test_non_github_https_returns_empty(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == ""

    @patch.object(Hand, "_run_git_read", return_value="git@gitlab.com:owner/repo.git")
    def test_non_github_scp_returns_empty(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == ""

    @patch.object(Hand, "_run_git_read", return_value="https://github.com/owner/repo")
    def test_https_without_git_suffix(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == "owner/repo"

    @patch.object(Hand, "_run_git_read", return_value="git@github.com:owner/repo")
    def test_scp_without_git_suffix(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == "owner/repo"

    @patch.object(
        Hand, "_run_git_read", return_value="ssh://git@github.com/owner/repo.git"
    )
    def test_ssh_scheme_with_github(self, _mock: MagicMock, tmp_path: Path) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == "owner/repo"

    @patch.object(Hand, "_run_git_read", return_value="https://github.com/invalid-path")
    def test_single_segment_path_returns_empty(
        self, _mock: MagicMock, tmp_path: Path
    ) -> None:
        assert Hand._github_repo_from_origin(tmp_path) == ""


# ---------------------------------------------------------------------------
# _run_precommit_checks_and_fixes — FileNotFoundError path
# ---------------------------------------------------------------------------


class TestRunPrecommitFileNotFound:
    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_first_pass_file_not_found_raises(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = FileNotFoundError("uv not found")
        with pytest.raises(RuntimeError, match="uv is not available"):
            Hand._run_precommit_checks_and_fixes(tmp_path)

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_second_pass_file_not_found_raises(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="reformatted", stderr=""
            ),
            FileNotFoundError("uv gone"),
        ]
        with pytest.raises(RuntimeError, match="uv is not available"):
            Hand._run_precommit_checks_and_fixes(tmp_path)

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_first_pass_success_returns_immediately(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        Hand._run_precommit_checks_and_fixes(tmp_path)
        assert mock_run.call_count == 1

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_truncates_long_output(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="first fail", stderr=""
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="x" * 5000,
                stderr="e" * 5000,
            ),
        ]
        with pytest.raises(RuntimeError, match="truncated"):
            Hand._run_precommit_checks_and_fixes(tmp_path)


# ---------------------------------------------------------------------------
# _push_noninteractive
# ---------------------------------------------------------------------------


class TestPushNoninteractive:
    def test_sets_and_restores_env_vars(self) -> None:
        mock_gh = MagicMock()
        tmp = Path("/tmp/fake")

        original_prompt = os.environ.get("GIT_TERMINAL_PROMPT")
        original_gcm = os.environ.get("GCM_INTERACTIVE")

        Hand._push_noninteractive(mock_gh, tmp, "test-branch")

        mock_gh.push.assert_called_once_with(
            tmp, branch="test-branch", set_upstream=True
        )
        # Env vars restored to original values
        assert os.environ.get("GIT_TERMINAL_PROMPT") == original_prompt
        assert os.environ.get("GCM_INTERACTIVE") == original_gcm

    def test_restores_env_on_push_failure(self) -> None:
        mock_gh = MagicMock()
        mock_gh.push.side_effect = RuntimeError("push rejected")
        tmp = Path("/tmp/fake")

        original_prompt = os.environ.get("GIT_TERMINAL_PROMPT")

        with pytest.raises(RuntimeError, match="push rejected"):
            Hand._push_noninteractive(mock_gh, tmp, "test-branch")

        assert os.environ.get("GIT_TERMINAL_PROMPT") == original_prompt

    def test_preserves_existing_env_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GIT_TERMINAL_PROMPT", "1")
        monkeypatch.setenv("GCM_INTERACTIVE", "always")

        mock_gh = MagicMock()
        Hand._push_noninteractive(mock_gh, Path("/tmp"), "branch")

        assert os.environ["GIT_TERMINAL_PROMPT"] == "1"
        assert os.environ["GCM_INTERACTIVE"] == "always"


# ---------------------------------------------------------------------------
# _push_to_existing_pr
# ---------------------------------------------------------------------------


class TestPushToExistingPr:
    def test_updates_existing_pr_on_successful_push(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "feature-branch",
            "base": "main",
            "url": "https://github.com/owner/repo/pull/42",
            "user": "bot-user",
        }
        mock_gh.add_and_commit.return_value = "sha123"
        mock_gh.whoami.return_value = {"login": "bot-user"}

        with (
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_update_pr_description") as mock_update,
        ):
            result = hand._push_to_existing_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="fix bug",
                summary="fixed it",
                metadata={},
            )

        assert result["pr_status"] == "updated"
        assert result["pr_url"] == "https://github.com/owner/repo/pull/42"
        assert result["pr_number"] == "42"
        assert result["pr_branch"] == "feature-branch"
        mock_update.assert_called_once()

    def test_creates_diverged_pr_on_push_failure(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "feature-branch",
            "base": "main",
            "url": "https://github.com/owner/repo/pull/42",
        }
        mock_gh.add_and_commit.return_value = "sha123"

        with (
            patch.object(
                Hand,
                "_push_noninteractive",
                side_effect=RuntimeError("push rejected"),
            ),
            patch.object(
                Hand,
                "_create_pr_for_diverged_branch",
                return_value={"pr_status": "created", "pr_url": "new-url"},
            ) as mock_diverged,
        ):
            result = hand._push_to_existing_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="fix bug",
                summary="fixed it",
                metadata={},
            )

        assert result["pr_status"] == "created"
        mock_diverged.assert_called_once()

    def test_skips_pr_description_update_for_different_user(
        self, repo_index: RepoIndex
    ) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "branch",
            "base": "main",
            "url": "https://example.com/pr/10",
            "user": "other-user",
        }
        mock_gh.add_and_commit.return_value = "sha456"
        mock_gh.whoami.return_value = {"login": "bot-user"}

        with (
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_update_pr_description") as mock_update,
        ):
            result = hand._push_to_existing_pr(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="fix",
                summary="done",
                metadata={},
            )

        assert result["pr_status"] == "updated"
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# _should_run_precommit_before_pr
# ---------------------------------------------------------------------------


class TestShouldRunPrecommitBeforePr:
    def test_returns_true_when_execution_enabled(self, repo_index: RepoIndex) -> None:
        config = Config(
            repo=str(repo_index.root),
            model="test-model",
            enable_execution=True,
        )
        hand = _StubHand(config, repo_index)
        assert hand._should_run_precommit_before_pr() is True

    def test_returns_false_when_execution_disabled(self, repo_index: RepoIndex) -> None:
        config = Config(
            repo=str(repo_index.root),
            model="test-model",
            enable_execution=False,
        )
        hand = _StubHand(config, repo_index)
        assert hand._should_run_precommit_before_pr() is False

    def test_returns_false_by_default(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        assert hand._should_run_precommit_before_pr() is False


# ---------------------------------------------------------------------------
# _finalize_repo_pr error paths
# ---------------------------------------------------------------------------


class TestFinalizeRepoErrorPaths:
    def test_missing_token_error(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=ValueError("GITHUB_TOKEN not set"),
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "missing_token"
        assert "GITHUB_TOKEN" in result["pr_error"]

    def test_git_error(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=RuntimeError("git push failed"),
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "git_error"

    def test_generic_error(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=OSError("unexpected"),
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "error"
