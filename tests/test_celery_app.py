"""Tests for Celery configuration helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("celery")

from helping_hands.server import celery_app


class TestResolveCeleryUrls:
    def test_uses_explicit_broker_and_backend(self, monkeypatch) -> None:
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker-host:6379/0")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://backend-host:6379/1")
        monkeypatch.setenv("REDIS_URL", "redis://shared-host:6379/0")

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://broker-host:6379/0"
        assert backend == "redis://backend-host:6379/1"

    def test_falls_back_to_redis_url(self, monkeypatch) -> None:
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://shared-host:6379/0")

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://shared-host:6379/0"
        assert backend == "redis://shared-host:6379/0"

    def test_backend_falls_back_to_broker_url(self, monkeypatch) -> None:
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker-host:6379/0")
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://broker-host:6379/0"
        assert backend == "redis://broker-host:6379/0"


class TestResolveRepoPath:
    def test_clone_owner_repo_uses_token_and_noninteractive_env(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
        monkeypatch.setenv("GH_TOKEN", "gh-test-token")
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_test",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            repo_path, cloned_from, temp_root = celery_app._resolve_repo_path(
                "owner/repo"
            )

        clone_cmd = mock_run.call_args.args[0]
        clone_env = mock_run.call_args.kwargs["env"]
        assert clone_cmd[0:4] == ["git", "clone", "--depth", "1"]
        assert (
            clone_cmd[4]
            == "https://x-access-token:gh-test-token@github.com/owner/repo.git"
        )
        assert clone_env["GIT_TERMINAL_PROMPT"] == "0"
        assert clone_env["GCM_INTERACTIVE"] == "never"
        assert repo_path == Path("/tmp/helping_hands_repo_test/repo").resolve()
        assert cloned_from == "owner/repo"
        assert temp_root == Path("/tmp/helping_hands_repo_test")

    def test_clone_owner_repo_falls_back_to_plain_https_without_token(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_test_plain",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            celery_app._resolve_repo_path("owner/repo")

        clone_cmd = mock_run.call_args.args[0]
        assert clone_cmd[4] == "https://github.com/owner/repo.git"


class TestNormalizeBackend:
    def test_defaults_to_codexcli(self) -> None:
        requested, runtime = celery_app._normalize_backend(None)
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_basic_agent_maps_to_atomic_runtime(self) -> None:
        requested, runtime = celery_app._normalize_backend("basic-agent")
        assert requested == "basic-agent"
        assert runtime == "basic-atomic"

    def test_codexcli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("codexcli")
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_claudecodecli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("claudecodecli")
        assert requested == "claudecodecli"
        assert runtime == "claudecodecli"

    def test_goose_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("goose")
        assert requested == "goose"
        assert runtime == "goose"

    def test_geminicli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("geminicli")
        assert requested == "geminicli"
        assert runtime == "geminicli"

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            celery_app._normalize_backend("unknown-backend")


class TestCodexAuth:
    def test_has_codex_auth_with_openai_key(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert celery_app._has_codex_auth() is True

    def test_has_codex_auth_with_auth_file(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "auth.json").write_text("{}", encoding="utf-8")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert celery_app._has_codex_auth() is True

    def test_has_codex_auth_false_when_no_key_or_auth_file(
        self, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert celery_app._has_codex_auth() is False


class TestGeminiAuth:
    def test_has_gemini_auth_with_key(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "gem-test")
        assert celery_app._has_gemini_auth() is True

    def test_has_gemini_auth_false_without_key(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert celery_app._has_gemini_auth() is False


# ---------------------------------------------------------------------------
# Additional helper function tests
# ---------------------------------------------------------------------------


class TestRedactSensitive:
    """Tests for _redact_sensitive()."""

    def test_redacts_token_in_clone_url(self) -> None:
        text = "https://x-access-token:ghp_secret123@github.com/owner/repo.git"
        result = celery_app._redact_sensitive(text)
        assert "ghp_secret123" not in result
        assert "***" in result
        assert "github.com/" in result

    def test_no_match_passes_through(self) -> None:
        text = "plain text with no tokens"
        assert celery_app._redact_sensitive(text) == text

    def test_multiple_tokens_redacted(self) -> None:
        text = (
            "https://x-access-token:tok1@github.com/a/b "
            "https://x-access-token:tok2@github.com/c/d"
        )
        result = celery_app._redact_sensitive(text)
        assert "tok1" not in result
        assert "tok2" not in result


class TestGithubCloneUrl:
    """Tests for _github_clone_url()."""

    def test_with_github_token(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_abc")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = celery_app._github_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_abc@github.com/owner/repo.git"

    def test_with_gh_token_fallback(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "ghp_def")
        url = celery_app._github_clone_url("owner/repo")
        assert url == "https://x-access-token:ghp_def@github.com/owner/repo.git"

    def test_without_token(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = celery_app._github_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"


class TestRepoTmpDir:
    """Tests for _repo_tmp_dir()."""

    def test_returns_path_when_env_set(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(tmp_path / "repos"))
        result = celery_app._repo_tmp_dir()
        assert result == tmp_path / "repos"
        assert result.is_dir()

    def test_returns_none_when_env_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "")
        assert celery_app._repo_tmp_dir() is None

    def test_returns_none_when_env_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_REPO_TMP", raising=False)
        assert celery_app._repo_tmp_dir() is None


class TestTrimUpdates:
    """Tests for _trim_updates()."""

    def test_under_limit_is_noop(self) -> None:
        updates = ["a", "b", "c"]
        celery_app._trim_updates(updates)
        assert updates == ["a", "b", "c"]

    def test_at_limit_is_noop(self) -> None:
        updates = [f"line_{i}" for i in range(celery_app._MAX_STORED_UPDATES)]
        celery_app._trim_updates(updates)
        assert len(updates) == celery_app._MAX_STORED_UPDATES

    def test_over_limit_trims_oldest(self) -> None:
        n = celery_app._MAX_STORED_UPDATES + 50
        updates = [f"line_{i}" for i in range(n)]
        celery_app._trim_updates(updates)
        assert len(updates) == celery_app._MAX_STORED_UPDATES
        assert updates[0] == "line_50"
        assert updates[-1] == f"line_{n - 1}"


class TestAppendUpdate:
    """Tests for _append_update()."""

    def test_appends_normal_text(self) -> None:
        updates: list[str] = []
        celery_app._append_update(updates, "hello world")
        assert updates == ["hello world"]

    def test_strips_whitespace(self) -> None:
        updates: list[str] = []
        celery_app._append_update(updates, "  spaced  ")
        assert updates == ["spaced"]

    def test_empty_text_ignored(self) -> None:
        updates: list[str] = []
        celery_app._append_update(updates, "")
        celery_app._append_update(updates, "   ")
        assert updates == []

    def test_truncates_long_text(self) -> None:
        updates: list[str] = []
        long_text = "x" * (celery_app._MAX_UPDATE_LINE_CHARS + 100)
        celery_app._append_update(updates, long_text)
        assert len(updates) == 1
        assert updates[0].endswith("...[truncated]")
        assert len(updates[0]) < len(long_text)


class TestUpdateCollector:
    """Tests for _UpdateCollector."""

    def test_splits_on_newlines(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        collector.feed("line1\nline2\nline3\n")
        assert updates == ["line1", "line2", "line3"]

    def test_buffers_partial_lines(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        collector.feed("partial")
        assert updates == []
        collector.feed(" text\n")
        assert updates == ["partial text"]

    def test_flush_emits_buffered_content(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        collector.feed("buffered")
        assert updates == []
        collector.flush()
        assert updates == ["buffered"]

    def test_flush_noop_when_empty(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        collector.flush()
        assert updates == []

    def test_large_buffer_auto_flushes(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        chunk = "a" * (celery_app._BUFFER_FLUSH_CHARS + 10)
        collector.feed(chunk)
        assert len(updates) == 1
        assert updates[0] == chunk

    def test_empty_chunk_ignored(self) -> None:
        updates: list[str] = []
        collector = celery_app._UpdateCollector(updates)
        collector.feed("")
        assert updates == []
