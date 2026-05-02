"""Tests for _collect_queue_depth and the /tasks/queue-depth endpoint.

The popover surface in the UI relies on these counts to show whether the
queue is backed up vs. workers being idle. If the helper regresses (e.g.
crashes when celery inspect returns None, or fails to sum entries across
workers) the popover silently shows 0s and operators lose visibility.

Key invariants: each inspect method (active/reserved/scheduled) is
independently tolerant of missing data; broker_depth is read via Redis
LLEN of the default "celery" queue; ``source`` reflects which sides
(celery, redis, both, neither) succeeded.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import _collect_queue_depth


def _mock_inspect(monkeypatch: pytest.MonkeyPatch, payloads: dict[str, object]) -> None:
    """Patch celery inspect with the given per-method return values."""
    mock_control = MagicMock()
    mock_inspector = MagicMock()
    for method, value in payloads.items():
        getattr(mock_inspector, method).return_value = value
    mock_control.inspect.return_value = mock_inspector
    monkeypatch.setattr("helping_hands.server.app.celery_app.control", mock_control)


def _mock_redis_llen(monkeypatch: pytest.MonkeyPatch, value: int | Exception) -> None:
    """Patch the redis client used by _collect_queue_depth.

    Pass an int to return that LLEN, or an Exception class instance to raise it.
    """
    import redis as redis_lib

    mock_client = MagicMock()
    if isinstance(value, Exception):
        mock_client.llen.side_effect = value
    else:
        mock_client.llen.return_value = value

    def fake_from_url(*_args: object, **_kwargs: object) -> object:
        return mock_client

    monkeypatch.setattr(redis_lib.Redis, "from_url", staticmethod(fake_from_url))


class TestCollectQueueDepth:
    def test_all_sources_succeed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_inspect(
            monkeypatch,
            {
                "active": {
                    "worker-1": [{"id": "a"}, {"id": "b"}],
                    "worker-2": [{"id": "c"}],
                },
                "reserved": {"worker-1": [{"id": "d"}]},
                "scheduled": {"worker-1": [{"id": "e"}, {"id": "f"}]},
            },
        )
        _mock_redis_llen(monkeypatch, 7)

        resp = _collect_queue_depth()

        assert resp.active == 3
        assert resp.reserved == 1
        assert resp.scheduled == 2
        assert resp.broker_depth == 7
        assert resp.source == "celery+redis"

    def test_celery_only_when_redis_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _mock_inspect(
            monkeypatch,
            {
                "active": {"worker-1": [{"id": "a"}]},
                "reserved": {},
                "scheduled": {},
            },
        )
        import redis as redis_lib

        _mock_redis_llen(monkeypatch, redis_lib.RedisError("nope"))

        resp = _collect_queue_depth()

        assert resp.active == 1
        assert resp.broker_depth == 0
        assert resp.source == "celery"

    def test_redis_only_when_celery_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _mock_inspect(
            monkeypatch,
            {"active": None, "reserved": None, "scheduled": None},
        )
        _mock_redis_llen(monkeypatch, 4)

        resp = _collect_queue_depth()

        assert resp.active == 0
        assert resp.reserved == 0
        assert resp.scheduled == 0
        assert resp.broker_depth == 4
        assert resp.source == "redis"

    def test_unavailable_when_both_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_inspect(
            monkeypatch,
            {"active": None, "reserved": None, "scheduled": None},
        )
        import redis as redis_lib

        _mock_redis_llen(monkeypatch, redis_lib.RedisError("down"))

        resp = _collect_queue_depth()

        assert resp.active == 0
        assert resp.broker_depth == 0
        assert resp.source == "unavailable"

    def test_non_dict_inspect_payload_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Some inspect implementations occasionally return a list or string
        # under network failure. The helper should treat that as "no data"
        # rather than crashing.
        _mock_inspect(
            monkeypatch,
            {
                "active": "not-a-dict",
                "reserved": ["bare-list"],
                "scheduled": {"worker-1": [{"id": "x"}]},
            },
        )
        _mock_redis_llen(monkeypatch, 0)

        resp = _collect_queue_depth()

        assert resp.active == 0
        assert resp.reserved == 0
        assert resp.scheduled == 1
        assert resp.source == "celery+redis"

    def test_non_list_worker_entries_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _mock_inspect(
            monkeypatch,
            {
                "active": {"worker-1": "not-a-list", "worker-2": [{"id": "a"}]},
                "reserved": {},
                "scheduled": {},
            },
        )
        _mock_redis_llen(monkeypatch, 0)

        resp = _collect_queue_depth()

        assert resp.active == 1


class TestQueueDepthEndpoint:
    def test_endpoint_returns_collected_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi.testclient import TestClient

        from helping_hands.server.app import app

        _mock_inspect(
            monkeypatch,
            {
                "active": {"worker-1": [{"id": "a"}]},
                "reserved": {},
                "scheduled": {},
            },
        )
        _mock_redis_llen(monkeypatch, 2)

        client = TestClient(app)
        response = client.get("/tasks/queue-depth")

        assert response.status_code == 200
        data = response.json()
        assert data["active"] == 1
        assert data["broker_depth"] == 2
        assert data["source"] == "celery+redis"
