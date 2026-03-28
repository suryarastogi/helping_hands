"""Unit tests for E2EHand.run() and stream() with mocked GitHubClient.

Protects the full run() state machine: dry-run mode must skip push/PR and write
a marker file; fresh-PR mode must call clone, branch, push, create_pr,
update_pr_body, and upsert_pr_comment in sequence; resumed-PR mode must fetch
the existing branch without creating a new PR.  Also covers the base-branch
resolution chain (env override → GitHub API → current_branch fallback → "main"
constant), draft-PR toggling via HELPING_HANDS_E2E_DRAFT_PR, and the
auto-generated hand_uuid.  Regressions here break automated PR lifecycle
management and the metadata contract consumed by server-side task tracking.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.e2e import E2EHand


@dataclass
class _FakePRResult:
    number: int
    url: str
    title: str
    head: str
    base: str


def _make_hand(repo: str = "owner/repo", model: str = "test-model") -> E2EHand:
    config = Config(repo=repo, model=model)
    return E2EHand(config=config, repo_index=None)


def _mock_gh() -> MagicMock:
    """Build a MagicMock that satisfies the GitHubClient interface used by run()."""
    gh = MagicMock()
    gh.default_branch.return_value = "main"
    gh.current_branch.return_value = "main"
    gh.clone.return_value = Path("/tmp/cloned")
    gh.add_and_commit.return_value = "abc123deadbeef"
    gh.create_pr.return_value = _FakePRResult(
        number=42,
        url="https://github.com/owner/repo/pull/42",
        title="test PR",
        head="helping-hands/e2e-test",
        base="main",
    )
    gh.get_pr.return_value = {
        "base": "main",
        "head": "existing-branch",
        "url": "https://github.com/owner/repo/pull/99",
    }
    # Context manager support
    gh.__enter__ = MagicMock(return_value=gh)
    gh.__exit__ = MagicMock(return_value=False)
    return gh


class TestE2EHandRunDryRun:
    """dry_run=True skips push/PR."""

    def test_dry_run_no_push(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_WORK_ROOT", raising=False)
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        hand = _make_hand()
        gh = _mock_gh()

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("test prompt", hand_uuid="uuid-1234", dry_run=True)

        assert "dry run" in result.message.lower()
        assert result.metadata["dry_run"] == "true"
        assert result.metadata["backend"] == "e2e"
        gh.push.assert_not_called()
        gh.create_pr.assert_not_called()

    def test_dry_run_writes_marker_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        # Make clone create the repo_dir so write_text works
        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("test prompt", hand_uuid="uuid-5678", dry_run=True)

        marker = Path(result.metadata["workspace"]) / "HELPING_HANDS_E2E.md"
        assert marker.exists()
        content = marker.read_text()
        assert "uuid-5678" in content
        assert "test prompt" in content


class TestE2EHandRunFreshPR:
    """Fresh PR path: clone, branch, commit, push, create PR."""

    def test_creates_pr_and_returns_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("add feature", hand_uuid="uuid-fresh")

        assert result.metadata["pr_url"] == "https://github.com/owner/repo/pull/42"
        assert result.metadata["pr_number"] == "42"
        assert result.metadata["resumed_pr"] == "false"
        assert result.metadata["commit"] == "abc123deadbeef"
        gh.create_branch.assert_called_once()
        gh.push.assert_called_once()
        gh.create_pr.assert_called_once()
        gh.update_pr_body.assert_called_once()
        gh.upsert_pr_comment.assert_called_once()

    def test_metadata_contains_expected_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("task", hand_uuid="uuid-meta")

        expected_keys = {
            "backend",
            "model",
            "hand_uuid",
            "hand_root",
            "repo",
            "workspace",
            "branch",
            "base_branch",
            "commit",
            "pr_number",
            "pr_url",
            "resumed_pr",
            "dry_run",
        }
        assert set(result.metadata.keys()) == expected_keys
        assert result.metadata["model"] == "test-model"
        assert result.metadata["repo"] == "owner/repo"


class TestE2EHandRunResumedPR:
    """Resumed PR path: pr_number provided, fetch+switch existing branch."""

    def test_resumes_existing_pr(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("fix bug", hand_uuid="uuid-resume", pr_number=99)

        assert result.metadata["resumed_pr"] == "true"
        assert result.metadata["pr_number"] == "99"
        gh.get_pr.assert_called_once_with("owner/repo", 99)
        gh.fetch_branch.assert_called_once()
        gh.switch_branch.assert_called_once()
        gh.create_branch.assert_not_called()
        gh.create_pr.assert_not_called()
        # Should still update PR body and comment
        gh.update_pr_body.assert_called_once()
        gh.upsert_pr_comment.assert_called_once()


class TestE2EHandRunEmptyRepo:
    """Empty repo raises ValueError."""

    def test_empty_repo_raises(self) -> None:
        hand = _make_hand(repo="")
        with pytest.raises(ValueError, match=r"requires config\.repo"):
            hand.run("prompt")

    def test_whitespace_repo_raises(self) -> None:
        hand = _make_hand(repo="   ")
        with pytest.raises(ValueError, match=r"requires config\.repo"):
            hand.run("prompt")


class TestE2EHandRunConfiguredBaseBranch:
    """Configured base branch override via env var."""

    def test_uses_env_base_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.setenv("HELPING_HANDS_BASE_BRANCH", "develop")
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("task", hand_uuid="uuid-branch", dry_run=True)

        assert result.metadata["base_branch"] == "develop"
        # Should not call default_branch when env is set
        gh.default_branch.assert_not_called()


class TestE2EHandRunDefaultBranchFallback:
    """When default_branch() fails, clone_branch=None and detected branch is used."""

    def test_fallback_on_default_branch_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()
        gh.default_branch.side_effect = GithubException(500, "API error", None)
        gh.current_branch.return_value = "master"

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("task", hand_uuid="uuid-fallback", dry_run=True)

        assert result.metadata["base_branch"] == "master"
        # clone should be called with branch=None
        clone_call = gh.clone.call_args
        assert (
            clone_call.kwargs.get("branch") is None
            or clone_call[1].get("branch") is None
        )


class TestE2EHandRunDefaultBranchFallbackNoDetected:
    """When default_branch() fails AND current_branch returns falsy, base_branch stays 'main'."""

    def test_fallback_with_no_detected_branch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()
        gh.default_branch.side_effect = GithubException(500, "API error", None)
        gh.current_branch.return_value = ""

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("task", hand_uuid="uuid-nodetect", dry_run=True)

        # base_branch stays at the initial "main" fallback since detected was falsy
        assert result.metadata["base_branch"] == "main"
        gh.current_branch.assert_called_once()


class TestE2EHandRunAutoUuid:
    """run() auto-generates hand_uuid when not provided."""

    def test_auto_uuid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            result = hand.run("task", dry_run=True)

        assert result.metadata["hand_uuid"]
        assert len(result.metadata["hand_uuid"]) > 8


class TestE2EHandDraftPR:
    """E2E hand draft PR configuration."""

    def test_draft_pr_enabled_by_default(self) -> None:
        assert E2EHand._draft_pr_enabled() is True

    def test_draft_pr_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "false")
        assert E2EHand._draft_pr_enabled() is False

    def test_draft_pr_enabled_via_env_yes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "yes")
        assert E2EHand._draft_pr_enabled() is True

    def test_draft_pr_disabled_via_env_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "0")
        assert E2EHand._draft_pr_enabled() is False

    def test_draft_pr_disabled_via_env_no(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "no")
        assert E2EHand._draft_pr_enabled() is False

    def test_create_pr_called_with_draft_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        monkeypatch.delenv("HELPING_HANDS_E2E_DRAFT_PR", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            hand.run("add feature", hand_uuid="uuid-draft")

        gh.create_pr.assert_called_once()
        _, kwargs = gh.create_pr.call_args
        assert kwargs.get("draft") is True

    def test_create_pr_called_with_draft_false_when_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "false")
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            hand.run("add feature", hand_uuid="uuid-nodraft")

        gh.create_pr.assert_called_once()
        _, kwargs = gh.create_pr.call_args
        assert kwargs.get("draft") is False


class TestE2EHandStream:
    """stream() yields run() message."""

    def test_stream_yields_run_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        hand = _make_hand()
        gh = _mock_gh()

        def _fake_clone(repo: str, dest: Path, **kwargs: Any) -> Path:
            dest.mkdir(parents=True, exist_ok=True)
            return dest

        gh.clone.side_effect = _fake_clone

        async def _collect() -> list[str]:
            chunks: list[str] = []
            async for chunk in hand.stream("task"):
                chunks.append(chunk)
            return chunks

        with patch("helping_hands.lib.github.GitHubClient", return_value=gh):
            chunks = asyncio.run(_collect())

        assert len(chunks) == 1
        assert "E2EHand" in chunks[0]
