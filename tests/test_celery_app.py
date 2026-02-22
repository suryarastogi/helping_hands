"""Tests for Celery configuration helpers."""

from __future__ import annotations

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


class TestNormalizeBackend:
    def test_defaults_to_e2e(self) -> None:
        requested, runtime = celery_app._normalize_backend(None)
        assert requested == "e2e"
        assert runtime == "e2e"

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
