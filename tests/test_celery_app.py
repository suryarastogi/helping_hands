"""Tests for Celery configuration helpers."""

from __future__ import annotations

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
