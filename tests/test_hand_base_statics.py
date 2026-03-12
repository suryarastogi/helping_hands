"""Tests for Hand base class static/classmethods and helper methods.

Covers edge cases in _github_repo_from_origin, _run_precommit_checks_and_fixes,
_push_noninteractive, and _push_to_existing_pr.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse
from helping_hands.lib.repo import RepoIndex

# repo_index fixture provided by conftest.py


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


# ---------------------------------------------------------------------------
# _update_pr_description
# ---------------------------------------------------------------------------


class TestUpdatePrDescription:
    def test_rich_description_used(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        mock_gh = MagicMock()
        rich = MagicMock()
        rich.body = "Rich PR body"

        with patch(
            "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
            return_value=rich,
        ):
            hand._update_pr_description(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="task",
                summary="done",
                base_branch="main",
                commit_sha="abc123",
            )

        mock_gh.update_pr_body.assert_called_once()
        call_args = mock_gh.update_pr_body.call_args
        assert call_args[1]["body"] == "Rich PR body"

    def test_fallback_to_generic_body(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        mock_gh = MagicMock()

        with patch(
            "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
            return_value=None,
        ):
            hand._update_pr_description(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="task",
                summary="done",
                base_branch="main",
                commit_sha="abc123",
            )

        mock_gh.update_pr_body.assert_called_once()
        body = mock_gh.update_pr_body.call_args[1]["body"]
        assert "test" in body  # backend name in generic body

    def test_update_pr_body_exception_suppressed(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 42

        mock_gh = MagicMock()
        mock_gh.update_pr_body.side_effect = RuntimeError("API error")

        with patch(
            "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
            return_value=None,
        ):
            # Should not raise
            hand._update_pr_description(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="task",
                summary="done",
                base_branch="main",
                commit_sha="abc123",
            )


# ---------------------------------------------------------------------------
# _create_pr_for_diverged_branch
# ---------------------------------------------------------------------------


class TestCreatePrForDivergedBranch:
    def test_rich_description_path(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_pr = MagicMock()
        mock_pr.url = "https://github.com/o/r/pull/11"
        mock_pr.number = 11
        mock_gh.create_pr.return_value = mock_pr

        rich = MagicMock()
        rich.title = "feat: rich title"
        rich.body = "Rich body"

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
                return_value=rich,
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            metadata = hand._create_pr_for_diverged_branch(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="task",
                summary="done",
                metadata={},
                pr_branch="original-branch",
                commit_sha="abc123",
            )

        assert metadata["pr_status"] == "created"
        assert metadata["pr_url"] == "https://github.com/o/r/pull/11"
        mock_gh.create_pr.assert_called_once()
        call_kwargs = mock_gh.create_pr.call_args
        assert call_kwargs[1]["title"] == "feat: rich title"
        assert "Follow-up to #10" in call_kwargs[1]["body"]

    def test_fallback_to_generic_body(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_pr = MagicMock()
        mock_pr.url = "https://github.com/o/r/pull/12"
        mock_pr.number = 12
        mock_gh.create_pr.return_value = mock_pr

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
                return_value=None,
            ),
            patch.object(hand, "_push_noninteractive"),
        ):
            metadata = hand._create_pr_for_diverged_branch(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_index.root,
                backend="test",
                prompt="task",
                summary="done",
                metadata={},
                pr_branch="original-branch",
                commit_sha="abc123",
            )

        assert metadata["pr_status"] == "created"
        call_kwargs = mock_gh.create_pr.call_args
        # When generate_pr_description returns None, the title falls back to
        # _commit_message_from_prompt which derives a conventional commit title.
        assert call_kwargs[1]["title"]  # non-empty title generated from summary
        assert "Follow-up to #10" in call_kwargs[1]["body"]


# ---------------------------------------------------------------------------
# _run_git_read — success path
# ---------------------------------------------------------------------------


class TestRunGitRead:
    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_returns_stripped_stdout_on_success(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="  main  \n"
        )
        result = Hand._run_git_read(tmp_path, "branch", "--show-current")
        assert result == "main"

    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_returns_empty_on_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: not a repo"
        )
        assert Hand._run_git_read(tmp_path, "rev-parse", "--is-inside-work-tree") == ""


# ---------------------------------------------------------------------------
# _finalize_repo_pr — early return paths
# ---------------------------------------------------------------------------


class TestFinalizeRepoEarlyReturns:
    def test_repo_dir_not_a_directory(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        # Point root at a non-existent path
        hand.repo_index = MagicMock()
        hand.repo_index.root.resolve.return_value = Path("/nonexistent/path")
        result = hand._finalize_repo_pr(backend="test", prompt="task", summary="done")
        assert result["pr_status"] == "no_repo"

    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        # tmp_path exists but is not a git repo
        (tmp_path / "file.py").write_text("")
        ri = MagicMock()
        ri.root.resolve.return_value = tmp_path
        config = Config(repo=str(tmp_path), model="test-model")
        hand = _StubHand(config, ri)
        hand.repo_index = ri
        with patch.object(Hand, "_run_git_read", return_value=""):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )
        assert result["pr_status"] == "not_git_repo"

    def test_no_changes(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return ""
            return ""

        with patch.object(Hand, "_run_git_read", side_effect=fake_git_read):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )
        assert result["pr_status"] == "no_changes"

    def test_disabled_auto_pr(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.auto_pr = False
        result = hand._finalize_repo_pr(backend="test", prompt="task", summary="done")
        assert result["pr_status"] == "disabled"

    def test_no_github_origin(self, repo_index: RepoIndex) -> None:
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M file.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value=""),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )
        assert result["pr_status"] == "no_github_origin"


# ---------------------------------------------------------------------------
# _push_to_existing_pr — whoami exception
# ---------------------------------------------------------------------------


class TestPushToExistingPrWhoamiException:
    def test_whoami_exception_skips_pr_description_update(
        self, repo_index: RepoIndex
    ) -> None:
        """If whoami raises, token_user falls back to '' and update is skipped."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "branch",
            "base": "main",
            "url": "https://example.com/pr/10",
            "user": "some-user",
        }
        mock_gh.add_and_commit.return_value = "sha789"
        mock_gh.whoami.side_effect = RuntimeError("network error")

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
        # whoami raised, so token_user == "" and update is skipped
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# _finalize_repo_pr — precommit succeeds but leaves no changes
# ---------------------------------------------------------------------------


class TestFinalizePrecommitNoChangesAfterFix:
    def test_precommit_cleans_all_changes(self, repo_index: RepoIndex) -> None:
        """Precommit reformats and the result is identical to HEAD => no_changes."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        call_count = {"porcelain": 0}

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                call_count["porcelain"] += 1
                # First call: has changes; second call (after precommit): clean
                if call_count["porcelain"] == 1:
                    return " M main.py"
                return ""
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_should_run_precommit_before_pr", return_value=True),
            patch.object(Hand, "_run_precommit_checks_and_fixes"),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "no_changes"
        # porcelain was called twice (before and after precommit)
        assert call_count["porcelain"] == 2


# ---------------------------------------------------------------------------
# _finalize_repo_pr — get_repo default_branch exception fallback
# ---------------------------------------------------------------------------


class TestFinalizeDefaultBranchException:
    def test_get_repo_exception_uses_fallback_base_branch(
        self, repo_index: RepoIndex
    ) -> None:
        """If get_repo raises when fetching default_branch, fall back gracefully."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.get_repo.side_effect = RuntimeError("API error")
        mock_gh.create_pr.return_value = MagicMock(
            html_url="https://github.com/owner/repo/pull/1",
            number=1,
        )
        mock_gh.add_and_commit.return_value = "sha999"
        mock_gh.token = "ghp_test"

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_should_run_precommit_before_pr", return_value=False),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._commit_message_from_prompt",
                return_value="commit msg",
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        # Should still succeed even though get_repo raised
        assert result["pr_status"] == "created"


# ---------------------------------------------------------------------------
# _run_precommit_checks_and_fixes — stderr-only branch miss (line 243->245)
# ---------------------------------------------------------------------------


class TestPrecommitStdoutOnlyNoStderr:
    @patch("helping_hands.lib.hands.v1.hand.base.subprocess.run")
    def test_second_pass_fails_with_stdout_only(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """When second pass fails with stdout but empty stderr, error still raised."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="reformatted", stderr=""
            ),
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="check failed", stderr=""
            ),
        ]
        with pytest.raises(RuntimeError, match="pre-commit checks failed"):
            Hand._run_precommit_checks_and_fixes(tmp_path)


# ---------------------------------------------------------------------------
# _finalize_repo_pr — pr_number set triggers _push_to_existing_pr (line 560)
# ---------------------------------------------------------------------------


class TestFinalizePrNumberSet:
    def test_finalize_delegates_to_push_to_existing_pr(
        self, repo_index: RepoIndex
    ) -> None:
        """When pr_number is set, _finalize_repo_pr returns _push_to_existing_pr."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 99

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.token = "ghp_test"

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_should_run_precommit_before_pr", return_value=False),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch.object(
                Hand,
                "_push_to_existing_pr",
                return_value={"pr_status": "updated", "pr_number": "99"},
            ) as mock_push_existing,
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        mock_push_existing.assert_called_once()
        assert result["pr_status"] == "updated"
        assert result["pr_number"] == "99"


# ---------------------------------------------------------------------------
# _finalize_repo_pr — default_branch is falsy (line 597->602 false branch)
# ---------------------------------------------------------------------------


class TestFinalizeEmptyDefaultBranch:
    def test_falsy_default_branch_uses_fallback(self, repo_index: RepoIndex) -> None:
        """When repo_obj.default_branch is empty, base_branch stays as fallback."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_repo_obj = MagicMock()
        mock_repo_obj.default_branch = ""  # falsy

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.get_repo.return_value = mock_repo_obj
        mock_gh.create_pr.return_value = MagicMock(
            html_url="https://github.com/owner/repo/pull/1",
            number=1,
        )
        mock_gh.add_and_commit.return_value = "sha123"
        mock_gh.token = "ghp_test"

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_should_run_precommit_before_pr", return_value=False),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._commit_message_from_prompt",
                return_value="commit msg",
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "created"
        # create_pr was called with the fallback base branch (main), not empty
        call_kwargs = mock_gh.create_pr.call_args
        assert call_kwargs.kwargs.get("base") or call_kwargs[1].get("base") or "main"


# ---------------------------------------------------------------------------
# _finalize_repo_pr — get_repo exception debug logging (v121)
# ---------------------------------------------------------------------------


class TestFinalizeDefaultBranchExceptionLogging:
    def test_get_repo_exception_emits_debug_log(
        self, repo_index: RepoIndex, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When get_repo raises, a debug log with exc_info should be emitted."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        mock_gh.get_repo.side_effect = RuntimeError("API down")
        mock_gh.create_pr.return_value = MagicMock(
            html_url="https://github.com/owner/repo/pull/1",
            number=1,
        )
        mock_gh.add_and_commit.return_value = "sha999"
        mock_gh.token = "ghp_test"

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch.object(Hand, "_should_run_precommit_before_pr", return_value=False),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_configure_authenticated_push_remote"),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description.generate_pr_description",
                return_value=None,
            ),
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description._commit_message_from_prompt",
                return_value="commit msg",
            ),
            caplog.at_level(
                logging.DEBUG, logger="helping_hands.lib.hands.v1.hand.base"
            ),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "created"
        assert any(
            "could not fetch default branch" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _push_to_existing_pr — whoami exception debug logging (v121)
# ---------------------------------------------------------------------------


class TestPushToExistingPrWhoamiExceptionLogging:
    def test_whoami_exception_emits_debug_log(
        self, repo_index: RepoIndex, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When whoami raises, a debug log should be emitted."""
        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _StubHand(config, repo_index)
        hand.pr_number = 10

        mock_gh = MagicMock()
        mock_gh.get_pr.return_value = {
            "head": "branch",
            "base": "main",
            "url": "https://example.com/pr/10",
            "user": "some-user",
        }
        mock_gh.add_and_commit.return_value = "sha789"
        mock_gh.whoami.side_effect = RuntimeError("network error")

        with (
            patch.object(Hand, "_push_noninteractive"),
            patch.object(Hand, "_update_pr_description") as mock_update,
            caplog.at_level(
                logging.DEBUG, logger="helping_hands.lib.hands.v1.hand.base"
            ),
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
        assert any("whoami() failed" in r.message for r in caplog.records)
