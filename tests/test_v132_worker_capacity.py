"""Tests for _resolve_worker_capacity: correct worker slot calculation and env override.

The server uses _resolve_worker_capacity() to decide how many concurrent build
tasks it will accept before returning a 503.  If the resolution logic regresses,
the server either rejects all tasks (capacity reads 0) or accepts unlimited tasks
(capacity falls through to an unbounded default), both causing production outages.

Key invariants: a valid env var overrides Celery-detected capacity; invalid env
values (non-numeric, zero, negative) are silently skipped so misconfiguration
degrades gracefully; the hard default is 8 workers; Celery stats with unexpected
types in the worker dict are skipped rather than crashing.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    _DEFAULT_WORKER_CAPACITY,
    _WORKER_CAPACITY_ENV_VARS,
    _resolve_worker_capacity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENV_VARS_TO_CLEAR = list(_WORKER_CAPACITY_ENV_VARS)


def _clear_worker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all worker capacity env vars so tests start clean."""
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)


def _mock_no_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock celery inspect to return no stats (simulates no workers)."""
    mock_control = MagicMock()
    mock_inspector = MagicMock()
    mock_inspector.stats.return_value = None
    mock_control.inspect.return_value = mock_inspector
    monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)


# ---------------------------------------------------------------------------
# Default fallback
# ---------------------------------------------------------------------------


class TestDefaultFallback:
    def test_no_celery_no_env_returns_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)

        resp = _resolve_worker_capacity()
        assert resp.source == "default"
        assert resp.max_workers == _DEFAULT_WORKER_CAPACITY
        assert resp.workers == {}

    def test_default_capacity_is_eight(self) -> None:
        assert _DEFAULT_WORKER_CAPACITY == 8


# ---------------------------------------------------------------------------
# Env var fallback
# ---------------------------------------------------------------------------


class TestEnvVarFallback:
    def test_valid_env_var_returns_env_source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "4")

        resp = _resolve_worker_capacity()
        assert resp.source == "env:HELPING_HANDS_MAX_WORKERS"
        assert resp.max_workers == 4
        assert resp.workers == {}

    def test_non_numeric_env_var_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "not-a-number")

        resp = _resolve_worker_capacity()
        assert resp.source == "default"

    def test_zero_env_var_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "0")

        resp = _resolve_worker_capacity()
        assert resp.source == "default"

    def test_negative_env_var_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "-3")

        resp = _resolve_worker_capacity()
        assert resp.source == "default"

    def test_whitespace_env_var_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "  ")

        resp = _resolve_worker_capacity()
        assert resp.source == "default"

    def test_second_env_var_used_when_first_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("CELERY_WORKER_CONCURRENCY", "6")

        resp = _resolve_worker_capacity()
        assert resp.source == "env:CELERY_WORKER_CONCURRENCY"
        assert resp.max_workers == 6

    def test_first_env_var_takes_priority(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)
        _mock_no_celery(monkeypatch)
        monkeypatch.setenv("HELPING_HANDS_MAX_WORKERS", "2")
        monkeypatch.setenv("CELERY_WORKER_CONCURRENCY", "10")

        resp = _resolve_worker_capacity()
        assert resp.source == "env:HELPING_HANDS_MAX_WORKERS"
        assert resp.max_workers == 2


# ---------------------------------------------------------------------------
# Celery stats path
# ---------------------------------------------------------------------------


class TestCeleryStatsPath:
    def test_celery_stats_returns_celery_source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)

        mock_control = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker-1": {"pool": {"max-concurrency": 4}},
            "worker-2": {"pool": {"max-concurrency": 2}},
        }
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        resp = _resolve_worker_capacity()
        assert resp.source == "celery"
        assert resp.max_workers == 6
        assert resp.workers == {"worker-1": 4, "worker-2": 2}

    def test_celery_stats_non_dict_worker_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)

        mock_control = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker-1": "not-a-dict",
            "worker-2": {"pool": {"max-concurrency": 3}},
        }
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        resp = _resolve_worker_capacity()
        assert resp.source == "celery"
        assert resp.max_workers == 3
        assert "worker-1" not in resp.workers

    def test_celery_stats_non_int_concurrency_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)

        mock_control = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker-1": {"pool": {"max-concurrency": "bad"}},
        }
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        resp = _resolve_worker_capacity()
        # Falls through to env/default since no valid concurrency was found
        assert resp.source in ("default", "env")

    def test_celery_stats_zero_concurrency_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)

        mock_control = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker-1": {"pool": {"max-concurrency": 0}},
        }
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        resp = _resolve_worker_capacity()
        assert resp.source == "default"

    def test_celery_stats_non_dict_pool_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_worker_env(monkeypatch)

        mock_control = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.stats.return_value = {
            "worker-1": {"pool": "not-a-dict"},
        }
        mock_control.inspect.return_value = mock_inspector
        monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)

        resp = _resolve_worker_capacity()
        assert resp.source == "default"
