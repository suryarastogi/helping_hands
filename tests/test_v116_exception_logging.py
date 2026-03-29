"""Tests for v116: silent exception handlers now emit structured debug logs.

Health-check helpers (_check_redis_health, _check_db_health, _check_workers_health,
_resolve_worker_capacity, _get_claude_oauth_token) must log at DEBUG level when
they catch exceptions and return an error sentinel.  Without these log lines,
operators see only a degraded /health response with no clue about the root cause,
making it impossible to distinguish a mis-configured DATABASE_URL from a genuinely
down service.

If these tests regress, on-call engineers lose observability into why the health
endpoint reports "error" for a dependency.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _check_db_health,
    _check_redis_health,
    _check_workers_health,
    _get_claude_oauth_token,
    _resolve_worker_capacity,
)

# ---------------------------------------------------------------------------
# _check_redis_health logging
# ---------------------------------------------------------------------------


class TestCheckRedisHealthLogging:
    """Verify _check_redis_health logs debug on exception."""

    def test_logs_debug_on_redis_failure(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_redis_mod = MagicMock()
        mock_redis_mod.RedisError = type("RedisError", (Exception,), {})
        mock_redis_mod.Redis.from_url.side_effect = mock_redis_mod.RedisError("refused")
        monkeypatch.setitem(__import__("sys").modules, "redis", mock_redis_mod)

        with caplog.at_level(logging.DEBUG):
            result = _check_redis_health()

        assert result == "error"
        assert any("Redis health check failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _check_db_health logging
# ---------------------------------------------------------------------------


class TestCheckDbHealthLogging:
    """Verify _check_db_health logs debug on exception."""

    def test_logs_debug_on_db_failure(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = type("Error", (Exception,), {})
        mock_psycopg2.connect.side_effect = mock_psycopg2.Error("connection refused")
        monkeypatch.setitem(__import__("sys").modules, "psycopg2", mock_psycopg2)

        with caplog.at_level(logging.DEBUG):
            result = _check_db_health()

        assert result == "error"
        assert any("Database health check failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _check_workers_health logging
# ---------------------------------------------------------------------------


class TestCheckWorkersHealthLogging:
    """Verify _check_workers_health logs debug on exception."""

    def test_logs_debug_on_workers_failure(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_control = MagicMock()
        mock_control.inspect.side_effect = ConnectionError("no broker")
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        with caplog.at_level(logging.DEBUG):
            result = _check_workers_health()

        assert result == "error"
        assert any("Workers health check failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _resolve_worker_capacity logging
# ---------------------------------------------------------------------------


class TestResolveWorkerCapacityLogging:
    """Verify _resolve_worker_capacity logs debug on exception."""

    def test_logs_debug_on_capacity_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Use patch() instead of monkeypatch.setattr to avoid Python 3.14
        # incompatibility with kombu's cached_property descriptor on
        # celery_app.control.
        with patch("helping_hands.server.app.celery_app") as mock_celery:
            mock_celery.control.inspect.side_effect = ConnectionError("broker down")
            with caplog.at_level(logging.DEBUG):
                resp = _resolve_worker_capacity()

        # Falls back to env or default
        assert resp.source in ("env", "default")
        assert any(
            "Failed to resolve worker capacity" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _get_claude_oauth_token logging
# ---------------------------------------------------------------------------


class TestGetClaudeOauthTokenLogging:
    """Verify _get_claude_oauth_token logs debug on exception."""

    def test_logs_debug_on_keychain_timeout(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(
                "helping_hands.server.app._read_claude_credentials_file",
                return_value=None,
            ),
            patch(
                "helping_hands.server.app.subprocess.run",
                side_effect=TimeoutError("keychain timed out"),
            ),
            caplog.at_level(logging.DEBUG),
        ):
            result = _get_claude_oauth_token()

        assert result is None
        assert any(
            "Failed to read Claude OAuth token from Keychain" in r.message
            for r in caplog.records
        )

    def test_logs_debug_on_generic_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(
                "helping_hands.server.app._read_claude_credentials_file",
                return_value=None,
            ),
            patch(
                "helping_hands.server.app.subprocess.run",
                side_effect=OSError("no such binary"),
            ),
            caplog.at_level(logging.DEBUG),
        ):
            result = _get_claude_oauth_token()

        assert result is None
        assert any(
            "Failed to read Claude OAuth token from Keychain" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# ensure_usage_schedule logging (celery_app.py)
# ---------------------------------------------------------------------------


class TestEnsureUsageScheduleLogging:
    """Verify ensure_usage_schedule logs debug on exceptions."""

    def test_logs_debug_on_entry_not_found(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_entry_cls = MagicMock()
        mock_entry_cls.from_key.side_effect = KeyError("not found")
        mock_entry_instance = MagicMock()
        mock_entry_cls.return_value = mock_entry_instance

        mock_schedule = MagicMock()

        with (
            patch(
                "helping_hands.server.celery_app.RedBeatSchedulerEntry",
                mock_entry_cls,
                create=True,
            ),
            patch.dict(
                "sys.modules",
                {
                    "redbeat": MagicMock(RedBeatSchedulerEntry=mock_entry_cls),
                    "celery.schedules": MagicMock(schedule=mock_schedule),
                },
            ),
            caplog.at_level(logging.DEBUG),
        ):
            from helping_hands.server.celery_app import ensure_usage_schedule

            ensure_usage_schedule()

        assert any(
            "Usage schedule entry not found" in r.message for r in caplog.records
        )
        # Should have saved the new entry
        mock_entry_instance.save.assert_called_once()

    def test_logs_debug_on_outer_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch.dict(
                "sys.modules",
                {"redbeat": None, "celery.schedules": None},
            ),
            caplog.at_level(logging.DEBUG),
        ):
            from helping_hands.server.celery_app import ensure_usage_schedule

            ensure_usage_schedule()

        assert any(
            "Failed to register usage schedule" in r.message for r in caplog.records
        )
