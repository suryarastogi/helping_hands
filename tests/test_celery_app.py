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
            repo_path, cloned_from = celery_app._resolve_repo_path("owner/repo")

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
