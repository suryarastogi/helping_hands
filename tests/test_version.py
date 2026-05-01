"""Tests for ``helping_hands.lib.version`` and the ``/version`` endpoint.

Covers the version-display feature: nominal version is sourced from
``pyproject.toml``, the SHA + dirty flag come from live git, the deploy
sentinel turns ``is_deployed`` on, worker versions are read from Redis,
and the FastAPI handler degrades gracefully when Redis is unreachable.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from helping_hands.lib import version as version_module
from helping_hands.lib.version import (
    WORKER_VERSION_KEY_PREFIX,
    VersionInfo,
    read_worker_versions,
    register_worker_version,
)
from helping_hands.server.app import app


class _FakeRedis:
    """Minimal in-memory stand-in for redis.Redis covering setex/scan/get."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    def scan_iter(self, match: str | None = None) -> list[bytes]:
        if match is None:
            return [k.encode() for k in self.store]
        prefix = match.rstrip("*")
        return [k.encode() for k in self.store if k.startswith(prefix)]

    def get(self, key: str | bytes) -> bytes | None:
        k = key.decode() if isinstance(key, bytes) else key
        v = self.store.get(k)
        return v.encode() if v is not None else None


class TestVersionModule:
    def test_display_includes_short_sha(self) -> None:
        info = VersionInfo(
            nominal="0.1.0",
            short_sha="abc1234",
            long_sha="abc1234567890",
            dirty=False,
            commit_date=None,
        )
        assert info.display == "0.1.0+abc1234"

    def test_display_appends_dirty_suffix(self) -> None:
        info = VersionInfo(
            nominal="0.1.0",
            short_sha="abc1234",
            long_sha="abc1234567890",
            dirty=True,
            commit_date=None,
        )
        assert info.display == "0.1.0+abc1234-dirty"

    def test_get_version_info_reads_pyproject_nominal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        version_module.get_version_info.cache_clear()
        info = version_module.get_version_info()
        # Whatever the SHA, the nominal must come from pyproject.toml.
        assert info.nominal == "0.1.0"

    def test_get_version_info_falls_back_when_git_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        version_module.get_version_info.cache_clear()
        monkeypatch.setattr(version_module, "_git", lambda *_a, **_k: None)
        monkeypatch.delenv("HH_VERSION", raising=False)
        info = version_module.get_version_info()
        assert info.short_sha == "unknown"
        assert info.long_sha == "unknown"
        assert info.dirty is False
        version_module.get_version_info.cache_clear()

    def test_get_version_info_uses_env_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        version_module.get_version_info.cache_clear()
        monkeypatch.setattr(version_module, "_git", lambda *_a, **_k: None)
        monkeypatch.setenv("HH_VERSION", "envsha7")
        info = version_module.get_version_info()
        assert info.short_sha == "envsha7"
        assert info.long_sha == "envsha7"
        version_module.get_version_info.cache_clear()


class TestWorkerRegistry:
    def test_register_and_read_round_trip(self) -> None:
        client = _FakeRedis()
        # Pre-populate with a key for a different host so we exercise scan.
        client.store[f"{WORKER_VERSION_KEY_PREFIX}otherhost"] = "0.1.0+oldsha1"
        register_worker_version(client, "0.1.0+abc1234")
        out = read_worker_versions(client)
        assert "otherhost" in out
        assert out["otherhost"] == "0.1.0+oldsha1"
        # The current hostname-keyed entry should also be present.
        assert any(v == "0.1.0+abc1234" for v in out.values())

    def test_read_returns_empty_when_redis_lacks_methods(self) -> None:
        class Broken:
            pass

        assert read_worker_versions(Broken()) == {}


class TestVersionEndpoint:
    def test_returns_backend_and_workers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        version_module.get_version_info.cache_clear()
        info = VersionInfo(
            nominal="0.1.0",
            short_sha="abc1234",
            long_sha="abc1234567890",
            dirty=False,
            commit_date="2026-05-01T12:00:00Z",
        )
        monkeypatch.setattr(version_module, "get_version_info", lambda: info)

        fake = _FakeRedis()
        fake.store[f"{WORKER_VERSION_KEY_PREFIX}lugiawyvern"] = "0.1.0+abc1234"

        class _Mod:
            class RedisError(Exception):
                pass

            class Redis:
                @staticmethod
                def from_url(*_a: Any, **_k: Any) -> _FakeRedis:
                    return fake

        monkeypatch.setitem(__import__("sys").modules, "redis", _Mod)
        monkeypatch.setattr(
            version_module, "read_sentinel_sha", lambda: "abc1234567890"
        )

        client = TestClient(app)
        response = client.get("/version")

        assert response.status_code == 200
        body = response.json()
        assert body["backend"] == "0.1.0+abc1234"
        assert body["workers"] == {"lugiawyvern": "0.1.0+abc1234"}
        assert body["git_sha"] == "abc1234567890"
        assert body["commit_date"] == "2026-05-01T12:00:00Z"
        assert body["is_deployed"] is True
        assert body["sentinel_sha"] == "abc1234567890"

    def test_returns_empty_workers_when_redis_unreachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        version_module.get_version_info.cache_clear()
        info = VersionInfo(
            nominal="0.1.0",
            short_sha="abc1234",
            long_sha="abc1234567890",
            dirty=False,
            commit_date=None,
        )
        monkeypatch.setattr(version_module, "get_version_info", lambda: info)
        monkeypatch.setattr(version_module, "read_sentinel_sha", lambda: None)

        class _RedisError(Exception):
            pass

        class _Mod:
            RedisError = _RedisError

            class Redis:
                @staticmethod
                def from_url(*_a: Any, **_k: Any) -> Any:
                    raise _RedisError("boom")

        monkeypatch.setitem(__import__("sys").modules, "redis", _Mod)

        client = TestClient(app)
        response = client.get("/version")

        assert response.status_code == 200
        body = response.json()
        assert body["backend"] == "0.1.0+abc1234"
        assert body["workers"] == {}
        assert body["is_deployed"] is False
        assert body["sentinel_sha"] is None
