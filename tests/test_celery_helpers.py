"""Tests for Celery app helper functions."""

from __future__ import annotations

import pytest

pytest.importorskip("celery")

from helping_hands.server.celery_app import (
    _append_update,
    _git_noninteractive_env,
    _github_clone_url,
    _redact_sensitive,
    _repo_tmp_dir,
    _trim_updates,
    _UpdateCollector,
)


class TestGithubCloneUrl:
    def test_token_auth_url(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_abc123")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_abc123@github.com/owner/repo.git"

    def test_gh_token_fallback(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_fallback")
        url = _github_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_fallback@github.com/owner/repo.git"

    def test_plain_https_without_token(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_github_token_takes_precedence(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "primary")
        monkeypatch.setenv("GH_TOKEN", "secondary")
        url = _github_clone_url("owner/repo")
        assert "primary" in url

    def test_whitespace_only_token_treated_as_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "   ")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"


class TestGitNoninteractiveEnv:
    def test_sets_git_terminal_prompt(self) -> None:
        env = _git_noninteractive_env()
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_sets_gcm_interactive(self) -> None:
        env = _git_noninteractive_env()
        assert env["GCM_INTERACTIVE"] == "never"


class TestRedactSensitive:
    def test_redacts_token_in_url(self) -> None:
        text = "https://x-access-token:ghp_secret123@github.com/owner/repo.git"
        result = _redact_sensitive(text)
        assert "ghp_secret123" not in result
        assert "***" in result
        assert "github.com/" in result

    def test_passthrough_plain_url(self) -> None:
        text = "https://github.com/owner/repo.git"
        assert _redact_sensitive(text) == text

    def test_redacts_multiple_occurrences(self) -> None:
        text = (
            "https://x-access-token:aaa@github.com/a/b "
            "https://x-access-token:bbb@github.com/c/d"
        )
        result = _redact_sensitive(text)
        assert "aaa" not in result
        assert "bbb" not in result

    def test_non_url_text_unchanged(self) -> None:
        text = "just some plain text"
        assert _redact_sensitive(text) == text


class TestRepoTmpDir:
    def test_returns_none_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_REPO_TMP", raising=False)
        assert _repo_tmp_dir() is None

    def test_returns_path_when_set(self, monkeypatch, tmp_path) -> None:
        target = tmp_path / "repo-tmp"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        result = _repo_tmp_dir()
        assert result == target
        assert target.is_dir()

    def test_creates_directory(self, monkeypatch, tmp_path) -> None:
        target = tmp_path / "nested" / "dir"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        result = _repo_tmp_dir()
        assert result is not None
        assert result.is_dir()

    def test_whitespace_only_returns_none(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "   ")
        assert _repo_tmp_dir() is None


class TestTrimUpdates:
    def test_no_trim_when_under_limit(self) -> None:
        updates = ["a", "b", "c"]
        _trim_updates(updates)
        assert len(updates) == 3

    def test_trims_oldest_entries(self, monkeypatch) -> None:
        monkeypatch.setattr("helping_hands.server.celery_app._MAX_STORED_UPDATES", 3)
        updates = ["a", "b", "c", "d", "e"]
        _trim_updates(updates)
        assert updates == ["c", "d", "e"]


class TestAppendUpdate:
    def test_appends_cleaned_text(self) -> None:
        updates: list[str] = []
        _append_update(updates, "  hello world  ")
        assert updates == ["hello world"]

    def test_skips_empty_text(self) -> None:
        updates: list[str] = []
        _append_update(updates, "")
        _append_update(updates, "   ")
        assert updates == []

    def test_truncates_long_lines(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.celery_app._MAX_UPDATE_LINE_CHARS", 10
        )
        updates: list[str] = []
        _append_update(updates, "a" * 20)
        assert updates[0].endswith("...[truncated]")
        assert updates[0].startswith("a" * 10)

    def test_calls_trim(self, monkeypatch) -> None:
        monkeypatch.setattr("helping_hands.server.celery_app._MAX_STORED_UPDATES", 2)
        updates: list[str] = []
        _append_update(updates, "one")
        _append_update(updates, "two")
        _append_update(updates, "three")
        assert len(updates) == 2
        assert updates == ["two", "three"]


class TestUpdateCollector:
    def test_feed_splits_on_newlines(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("line1\nline2\n")
        assert "line1" in updates

    def test_feed_ignores_empty_chunk(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("")
        assert updates == []

    def test_flush_emits_remaining_buffer(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("partial")
        collector.flush()
        assert "partial" in updates

    def test_flush_on_empty_buffer_is_noop(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.flush()
        assert updates == []

    def test_buffer_flush_on_char_limit(self, monkeypatch) -> None:
        monkeypatch.setattr("helping_hands.server.celery_app._BUFFER_FLUSH_CHARS", 5)
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("abcdefghij")
        assert len(updates) >= 1
