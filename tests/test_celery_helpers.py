"""Tests for the low-level helper functions extracted from the Celery task module.

Protects the building blocks shared across the worker: _github_clone_url constructs
authenticated URLs (GITHUB_TOKEN takes priority over GH_TOKEN, whitespace tokens
treated as absent); _git_noninteractive_env prevents git from blocking on credential
prompts during headless clones; _redact_sensitive strips tokens from error messages
before they reach logs or task results; _UpdateCollector buffers streaming output
and flushes on newline or a configurable character threshold; and _append_update
enforces per-line length limits and a maximum stored-updates cap to prevent memory
growth during long-running tasks.

If _redact_sensitive regresses, GitHub tokens leak into Celery task results.  If
_UpdateCollector split or flush logic breaks, the monitor page shows garbled or
incomplete streaming output.
"""

from __future__ import annotations

import pytest

pytest.importorskip("celery")

from helping_hands.lib.github_url import (
    noninteractive_env as _git_noninteractive_env,
    redact_credentials as _redact_sensitive,
)
from helping_hands.server.celery_app import (
    _append_update,
    _format_runtime,
    _github_clone_url,
    _has_codex_auth,
    _has_gemini_auth,
    _repo_tmp_dir,
    _trim_updates,
    _UpdateCollector,
    _validate_repo_spec,
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


class TestHasCodexAuth:
    def test_true_when_openai_api_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-abc123")
        assert _has_codex_auth() is True

    def test_true_when_auth_file_exists(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        auth_file = codex_dir / "auth.json"
        auth_file.write_text("{}")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _has_codex_auth() is True

    def test_false_when_no_key_and_no_file(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _has_codex_auth() is False

    def test_false_when_empty_api_key(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _has_codex_auth() is False


class TestHasGeminiAuth:
    """Tests for _has_gemini_auth helper in test_celery_helpers."""

    def test_true_when_key_set(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "AIza-test")
        assert _has_gemini_auth() is True

    def test_false_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert _has_gemini_auth() is False

    def test_false_when_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "")
        assert _has_gemini_auth() is False

    def test_false_when_whitespace_only(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        assert _has_gemini_auth() is False


class TestFormatRuntime:
    """Tests for _format_runtime helper."""

    def test_sub_minute_shows_decimal(self) -> None:
        assert _format_runtime(45.3) == "45.3s"

    def test_exactly_zero(self) -> None:
        assert _format_runtime(0.0) == "0.0s"

    def test_sub_second(self) -> None:
        assert _format_runtime(0.5) == "0.5s"

    def test_exactly_one_minute(self) -> None:
        assert _format_runtime(60.0) == "1m 0s"

    def test_minutes_and_seconds(self) -> None:
        assert _format_runtime(125.7) == "2m 6s"

    def test_large_value(self) -> None:
        result = _format_runtime(3661.0)
        assert result == "61m 1s"

    def test_just_under_one_minute(self) -> None:
        assert _format_runtime(59.9) == "59.9s"


class TestUpdateCollectorEdgeCases:
    """Extended edge case tests for _UpdateCollector."""

    def test_multiple_newlines_in_single_chunk(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("a\nb\nc\n")
        assert "a" in updates
        assert "b" in updates
        assert "c" in updates

    def test_newline_only_chunk(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("hello")
        collector.feed("\n")
        assert "hello" in updates

    def test_split_line_across_two_feeds(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("hel")
        collector.feed("lo\n")
        assert "hello" in updates

    def test_feed_after_flush(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("first")
        collector.flush()
        collector.feed("second\n")
        assert "first" in updates
        assert "second" in updates

    def test_multiple_flushes_are_idempotent(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("data")
        collector.flush()
        collector.flush()
        assert updates == ["data"]

    def test_buffer_flush_boundary_exact(self, monkeypatch) -> None:
        monkeypatch.setattr("helping_hands.server.celery_app._BUFFER_FLUSH_CHARS", 5)
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("abcde")  # exactly at boundary
        assert len(updates) == 1
        assert updates[0] == "abcde"

    def test_buffer_flush_then_newline(self, monkeypatch) -> None:
        monkeypatch.setattr("helping_hands.server.celery_app._BUFFER_FLUSH_CHARS", 5)
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("abcdefgh\nij")
        # "abcdefgh" should be emitted as a line, "ij" stays in buffer
        assert "abcdefgh" in updates
        collector.flush()
        assert "ij" in updates

    def test_whitespace_only_lines_are_skipped(self) -> None:
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("   \n")
        # _append_update strips and skips empty
        assert updates == []

    def test_long_line_is_truncated(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "helping_hands.server.celery_app._MAX_UPDATE_LINE_CHARS", 10
        )
        updates: list[str] = []
        collector = _UpdateCollector(updates)
        collector.feed("a" * 50 + "\n")
        assert updates[0].endswith("...[truncated]")
        assert len(updates[0]) < 50


# ---------------------------------------------------------------------------
# _validate_repo_spec — v149
# ---------------------------------------------------------------------------


class TestValidateRepoSpecCelery:
    def test_valid_owner_repo(self) -> None:
        _validate_repo_spec("owner/repo")  # should not raise

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_repo_spec("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_repo_spec("   ")

    def test_no_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("just-a-repo")

    def test_trailing_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("owner/")


class TestGithubCloneUrlValidationCelery:
    """v149: _github_clone_url rejects invalid repo specs."""

    def test_empty_repo_raises(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with pytest.raises(ValueError, match="must not be empty"):
            _github_clone_url("")

    def test_no_slash_raises(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with pytest.raises(ValueError, match="owner/repo"):
            _github_clone_url("just-a-name")
