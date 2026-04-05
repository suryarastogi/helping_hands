"""Unit tests for E2EHand static/class methods.

Protects the pure helper logic that underpins the clone-branch-commit-PR
workflow: safe directory name generation from arbitrary repo strings (prevents
bad characters from polluting filesystem paths), work-root and base-branch
resolution from environment variables, and the Markdown formatting of PR bodies
and status comments.  If these regress, E2EHand will silently produce malformed
paths or PR content with missing fields, breaking downstream CI consumers that
parse that content.

Also tests ``_draft_pr_enabled`` env-var gating and the ``stream()``
async wrapper to ensure they delegate correctly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.e2e import E2EHand


class TestSafeRepoDir:
    def test_simple_owner_repo(self) -> None:
        assert E2EHand._safe_repo_dir("owner/repo") == "owner_repo"

    def test_strips_leading_trailing_slashes(self) -> None:
        assert E2EHand._safe_repo_dir("/owner/repo/") == "owner_repo"

    def test_replaces_special_chars(self) -> None:
        assert E2EHand._safe_repo_dir("my org/my repo!@#") == "my_org_my_repo_"

    def test_preserves_dots_and_hyphens(self) -> None:
        assert E2EHand._safe_repo_dir("my-org/my.repo") == "my-org_my.repo"

    def test_multiple_slashes(self) -> None:
        assert E2EHand._safe_repo_dir("a//b///c") == "a_b_c"

    def test_empty_string(self) -> None:
        assert E2EHand._safe_repo_dir("") == ""

    def test_underscores_preserved(self) -> None:
        assert E2EHand._safe_repo_dir("my_org/my_repo") == "my_org_my_repo"


class TestWorkBase:
    def test_default_is_cwd(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_WORK_ROOT", raising=False)
        result = E2EHand._work_base()
        assert result == Path(".")

    def test_uses_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", "/tmp/test-work")
        result = E2EHand._work_base()
        assert result == Path("/tmp/test-work")

    def test_expands_user(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", "~/work")
        result = E2EHand._work_base()
        assert "~" not in str(result)
        assert str(result).endswith("/work")


class TestConfiguredBaseBranch:
    def test_empty_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_BASE_BRANCH", raising=False)
        assert E2EHand._configured_base_branch() == ""

    def test_returns_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_BASE_BRANCH", "develop")
        assert E2EHand._configured_base_branch() == "develop"

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_BASE_BRANCH", "  main  ")
        assert E2EHand._configured_base_branch() == "main"


class TestBuildE2ePrComment:
    def test_contains_all_fields(self) -> None:
        result = E2EHand._build_e2e_pr_comment(
            hand_uuid="abc-123",
            prompt="fix the bug",
            stamp_utc="2026-03-05T00:00:00+00:00",
            commit_sha="deadbeef",
        )
        assert "## helping_hands E2E update" in result
        assert "`abc-123`" in result
        assert "fix the bug" in result
        assert "`2026-03-05T00:00:00+00:00`" in result
        assert "`deadbeef`" in result

    def test_markdown_formatting(self) -> None:
        result = E2EHand._build_e2e_pr_comment(
            hand_uuid="id",
            prompt="p",
            stamp_utc="t",
            commit_sha="c",
        )
        lines = result.strip().split("\n")
        assert lines[0] == "## helping_hands E2E update"
        assert all(line.startswith("- ") for line in lines[2:])


class TestBuildE2ePrBody:
    def test_contains_all_fields(self) -> None:
        result = E2EHand._build_e2e_pr_body(
            hand_uuid="uuid-456",
            prompt="add feature",
            stamp_utc="2026-03-05T12:00:00+00:00",
            commit_sha="cafebabe",
        )
        assert "Automated E2E validation PR" in result
        assert "`uuid-456`" in result
        assert "add feature" in result
        assert "`2026-03-05T12:00:00+00:00`" in result
        assert "`cafebabe`" in result

    def test_includes_commit_sha(self) -> None:
        result = E2EHand._build_e2e_pr_body(
            hand_uuid="u",
            prompt="p",
            stamp_utc="t",
            commit_sha="abc123",
        )
        assert "commit: `abc123`" in result


# ---------------------------------------------------------------------------
# _draft_pr_enabled
# ---------------------------------------------------------------------------


class TestDraftPrEnabled:
    """Tests for E2EHand._draft_pr_enabled env-var gating."""

    def test_default_is_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When HELPING_HANDS_E2E_DRAFT_PR is unset, default is 'true'."""
        monkeypatch.delenv("HELPING_HANDS_E2E_DRAFT_PR", raising=False)
        assert E2EHand._draft_pr_enabled() is True

    def test_explicit_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "true")
        assert E2EHand._draft_pr_enabled() is True

    def test_explicit_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "1")
        assert E2EHand._draft_pr_enabled() is True

    def test_explicit_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "false")
        assert E2EHand._draft_pr_enabled() is False

    def test_explicit_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "0")
        assert E2EHand._draft_pr_enabled() is False

    def test_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "")
        assert E2EHand._draft_pr_enabled() is False

    def test_yes_is_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "yes")
        assert E2EHand._draft_pr_enabled() is True

    def test_whitespace_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_E2E_DRAFT_PR", "  true  ")
        assert E2EHand._draft_pr_enabled() is True


# ---------------------------------------------------------------------------
# stream() — async wrapper
# ---------------------------------------------------------------------------


class TestStream:
    """Tests for E2EHand.stream() async generator."""

    @pytest.mark.asyncio
    async def test_stream_yields_run_message(self) -> None:
        """stream() should delegate to run() and yield its message."""
        mock_config = MagicMock()
        mock_config.repo = "owner/repo"
        mock_index = MagicMock()

        hand = E2EHand.__new__(E2EHand)
        hand.config = mock_config
        hand.repo_index = mock_index

        sentinel_msg = "E2EHand complete. PR: https://example.com/pr/1"
        mock_response = MagicMock()
        mock_response.message = sentinel_msg

        with patch.object(E2EHand, "run", return_value=mock_response) as mock_run:
            messages = [msg async for msg in hand.stream("test prompt")]
            mock_run.assert_called_once_with("test prompt")

        assert messages == [sentinel_msg]

    @pytest.mark.asyncio
    async def test_stream_yields_exactly_one_message(self) -> None:
        """stream() should yield exactly one message."""
        hand = E2EHand.__new__(E2EHand)
        hand.config = MagicMock()
        hand.repo_index = MagicMock()

        mock_response = MagicMock()
        mock_response.message = "done"

        with patch.object(E2EHand, "run", return_value=mock_response):
            count = 0
            async for _ in hand.stream("p"):
                count += 1
        assert count == 1
