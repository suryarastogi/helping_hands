"""Tests for v124 git hardening: _run_git timeout + _validate_full_name."""

from __future__ import annotations

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.github import (
    _DEFAULT_GIT_TIMEOUT,
    GitHubClient,
    _git_timeout,
    _run_git,
    _validate_full_name,
)

# ---------------------------------------------------------------------------
# _git_timeout
# ---------------------------------------------------------------------------


class TestGitTimeout:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_GIT_TIMEOUT", raising=False)
        assert _git_timeout() == _DEFAULT_GIT_TIMEOUT

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "60")
        assert _git_timeout() == 60

    def test_non_numeric_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "abc")
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _DEFAULT_GIT_TIMEOUT
        assert "not an integer" in caplog.text

    def test_zero_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "0")
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _DEFAULT_GIT_TIMEOUT
        assert "must be positive" in caplog.text

    def test_negative_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "-5")
        with caplog.at_level(logging.WARNING):
            result = _git_timeout()
        assert result == _DEFAULT_GIT_TIMEOUT
        assert "must be positive" in caplog.text

    def test_empty_string_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "")
        assert _git_timeout() == _DEFAULT_GIT_TIMEOUT

    def test_whitespace_only_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_GIT_TIMEOUT", "   ")
        assert _git_timeout() == _DEFAULT_GIT_TIMEOUT


# ---------------------------------------------------------------------------
# _run_git timeout
# ---------------------------------------------------------------------------


class TestRunGitTimeout:
    @patch("helping_hands.lib.github._git_timeout", return_value=10)
    @patch("helping_hands.lib.github.subprocess.run")
    def test_timeout_raises_runtime_error(
        self, mock_run: MagicMock, _mock_timeout: MagicMock
    ) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "clone", "url"], timeout=10
        )
        with pytest.raises(RuntimeError, match="git timed out after 10s"):
            _run_git(["git", "clone", "url"])

    @patch("helping_hands.lib.github._git_timeout", return_value=10)
    @patch("helping_hands.lib.github.subprocess.run")
    def test_timeout_redacts_token_in_message(
        self, mock_run: MagicMock, _mock_timeout: MagicMock
    ) -> None:
        cmd = [
            "git",
            "clone",
            "https://x-access-token:secret123@github.com/owner/repo.git",
        ]
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=cmd, timeout=10)
        with pytest.raises(RuntimeError, match=r"\*\*\*") as exc_info:
            _run_git(cmd)
        assert "secret123" not in str(exc_info.value)

    @patch("helping_hands.lib.github._git_timeout", return_value=300)
    @patch("helping_hands.lib.github.subprocess.run")
    def test_passes_timeout_to_subprocess(
        self, mock_run: MagicMock, _mock_timeout: MagicMock
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status"], returncode=0, stdout="ok\n", stderr=""
        )
        _run_git(["git", "status"])
        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 300


# ---------------------------------------------------------------------------
# _validate_full_name
# ---------------------------------------------------------------------------


class TestValidateFullName:
    def test_valid(self) -> None:
        _validate_full_name("owner/repo")  # should not raise

    def test_valid_with_dashes(self) -> None:
        _validate_full_name("my-org/my-repo")  # should not raise

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_full_name("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_full_name("   ")

    def test_no_slash(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("justrepo")

    def test_multiple_slashes(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("a/b/c")

    def test_trailing_slash(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("owner/")

    def test_leading_slash(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_full_name("/repo")

    def test_contains_space(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            _validate_full_name("owner /repo")

    def test_contains_tab(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            _validate_full_name("owner\t/repo")


# ---------------------------------------------------------------------------
# GitHubClient.get_repo validates full_name
# ---------------------------------------------------------------------------


class TestGetRepoValidation:
    @pytest.fixture(autouse=True)
    def _fake_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")

    @pytest.fixture()
    def client(self) -> GitHubClient:
        with patch("helping_hands.lib.github.Github"):
            return GitHubClient()

    def test_rejects_invalid_full_name(self, client: GitHubClient) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            client.get_repo("invalid")

    def test_accepts_valid_full_name(self, client: GitHubClient) -> None:
        client.get_repo("owner/repo")  # should not raise
        client._gh.get_repo.assert_called_once_with("owner/repo")
