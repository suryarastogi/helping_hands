"""Tests for Multiplayer Grill Me (server/multiplayer_grill.py).

After the option-(2) migration, the worker no longer writes messages to
Redis lists — it pushes envelopes to the shared outbox ``mgrill:ai_outbox``
which the in-process ``mgrill_bridge`` drains into the matching Yjs room's
``messages`` Y.Array.

These tests protect:

* The outbox envelope shape (fields the bridge expects).
* Redis key names that the REST endpoints and worker both reference as
  string literals — drift breaks the contract silently.
* Session state read/write/update round-trips.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from helping_hands.server.mgrill_bridge import AI_OUTBOX_KEY, mgrill_room_name
from helping_hands.server.multiplayer_grill import (
    _REGISTRY_KEY,
    _emit_message,
    _get_state,
    _pop_user_msg,
    _set_state,
    _state_key,
    _touch_activity,
    _update_state,
    _user_msgs_key,
)


class TestRedisClient:
    """Factory uses the REDIS_URL env var, falling back to local default."""

    def test_uses_redis_url_env(self) -> None:
        import sys

        from helping_hands.server.multiplayer_grill import _redis_client

        mock_redis_mod = MagicMock()
        with (
            patch.dict("os.environ", {"REDIS_URL": "redis://myhost:1234/2"}),
            patch.dict(sys.modules, {"redis": mock_redis_mod}),
        ):
            _redis_client()
            mock_redis_mod.from_url.assert_called_once_with(
                "redis://myhost:1234/2", decode_responses=True
            )

    def test_default_url(self) -> None:
        import sys

        from helping_hands.server.multiplayer_grill import _redis_client

        mock_redis_mod = MagicMock()
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.dict(sys.modules, {"redis": mock_redis_mod}),
        ):
            _redis_client()
            mock_redis_mod.from_url.assert_called_once_with(
                "redis://localhost:6379/0", decode_responses=True
            )


class TestKeyNames:
    """The Redis key names must stay stable — REST endpoints in app.py
    reference them as string literals, so any drift silently breaks the
    lobby + room."""

    def test_state_key(self) -> None:
        assert _state_key("abc") == "mgrill:abc:state"

    def test_user_msgs_key(self) -> None:
        assert _user_msgs_key("abc") == "mgrill:abc:user_msgs"

    def test_registry_key(self) -> None:
        assert _REGISTRY_KEY == "mgrill:sessions"

    def test_ai_outbox_key(self) -> None:
        """The bridge consumes this shared queue name."""
        assert AI_OUTBOX_KEY == "mgrill:ai_outbox"

    def test_room_name_format(self) -> None:
        """The frontend connects to the Yjs room using this name format.

        Full mount-prefixed path — see ``mgrill_room_name`` docstring.
        """
        assert mgrill_room_name("abc") == "/ws/yjs/mgrill-abc"


class TestRedisHelpers:
    """Redis helpers that power the worker loop."""

    def _make_redis(self) -> MagicMock:
        """Mock Redis client with dict-backed get/set + RPUSH tracking."""
        store: dict[str, str] = {}
        zset_calls: list[tuple[str, dict[str, float]]] = []
        rpush_store: dict[str, list[str]] = {}
        r = MagicMock()
        r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
        r.get.side_effect = lambda k: store.get(k)

        def rpush(k: str, v: str) -> int:
            rpush_store.setdefault(k, []).append(v)
            return len(rpush_store[k])

        def lpop(k: str) -> str | None:
            lst = rpush_store.get(k)
            if not lst:
                return None
            return lst.pop(0)

        r.rpush.side_effect = rpush
        r.lpop.side_effect = lpop
        r.zadd.side_effect = lambda k, mapping: zset_calls.append((k, mapping)) or 1
        r.expire.return_value = True
        r._store = store  # type: ignore[attr-defined]
        r._rpush_store = rpush_store  # type: ignore[attr-defined]
        r._zset_calls = zset_calls  # type: ignore[attr-defined]
        return r

    def test_set_state_writes_json_with_ttl(self) -> None:
        r = self._make_redis()
        _set_state(r, "s1", {"status": "active", "turn_count": 2})
        stored = r._store["mgrill:s1:state"]  # type: ignore[attr-defined]
        decoded = json.loads(stored)
        assert decoded == {"status": "active", "turn_count": 2}
        r.set.assert_called()

    def test_set_state_bumps_registry_zadd(self) -> None:
        r = self._make_redis()
        _set_state(r, "s1", {"status": "active"})
        calls = r._zset_calls  # type: ignore[attr-defined]
        assert calls
        key, mapping = calls[-1]
        assert key == _REGISTRY_KEY
        assert "s1" in mapping
        assert mapping["s1"] > 0

    def test_get_state_round_trip(self) -> None:
        r = self._make_redis()
        _set_state(r, "s1", {"status": "thinking", "turn_count": 5})
        state = _get_state(r, "s1")
        assert state is not None
        assert state["status"] == "thinking"
        assert state["turn_count"] == 5

    def test_get_state_missing(self) -> None:
        r = self._make_redis()
        assert _get_state(r, "none") is None

    def test_update_state_merges(self) -> None:
        r = self._make_redis()
        _set_state(r, "s1", {"status": "active", "turn_count": 1})
        updated = _update_state(r, "s1", status="thinking")
        assert updated is not None
        assert updated["status"] == "thinking"
        assert updated["turn_count"] == 1

    def test_update_state_missing_returns_none(self) -> None:
        r = self._make_redis()
        assert _update_state(r, "never", status="x") is None

    def test_touch_activity_uses_zadd(self) -> None:
        r = self._make_redis()
        _touch_activity(r, "s1")
        calls = r._zset_calls  # type: ignore[attr-defined]
        assert any(k == _REGISTRY_KEY and "s1" in m for k, m in calls)

    def test_pop_user_msg_present(self) -> None:
        r = self._make_redis()
        r._rpush_store["mgrill:s1:user_msgs"] = [  # type: ignore[attr-defined]
            json.dumps({"content": "yes", "type": "message"})
        ]
        popped = _pop_user_msg(r, "s1")
        assert popped == {"content": "yes", "type": "message"}

    def test_pop_user_msg_empty(self) -> None:
        r = self._make_redis()
        assert _pop_user_msg(r, "s1") is None


class TestEmitMessage:
    """``_emit_message`` must LPUSH to the shared outbox queue with a well
    formed envelope, because the bridge task reads those fields as string
    keys and any drift drops the message silently."""

    def _make_redis(self) -> MagicMock:
        store: dict[str, list[str]] = {}
        r = MagicMock()

        def rpush(k: str, v: str) -> int:
            store.setdefault(k, []).append(v)
            return len(store[k])

        r.rpush.side_effect = rpush
        r.expire.return_value = True
        r.zadd.return_value = 1
        r._store = store  # type: ignore[attr-defined]
        return r

    def test_envelope_shape(self) -> None:
        r = self._make_redis()
        returned = _emit_message(
            r,
            "s1",
            role="assistant",
            content="Hello!",
            author_name="Interviewer",
            msg_type="message",
        )
        # Returned shape mirrors what participants see in the Y.Array.
        assert returned["role"] == "assistant"
        assert returned["content"] == "Hello!"
        assert returned["author_name"] == "Interviewer"
        assert returned["type"] == "message"
        assert "id" in returned
        assert "timestamp" in returned
        assert "session_id" not in returned

    def test_writes_to_outbox(self) -> None:
        r = self._make_redis()
        _emit_message(r, "s1", role="system", content="hi")
        envelopes = r._store[AI_OUTBOX_KEY]  # type: ignore[attr-defined]
        assert envelopes
        decoded = json.loads(envelopes[-1])
        # Bridge identifies the target room via session_id.
        assert decoded["session_id"] == "s1"
        assert decoded["role"] == "system"
        assert decoded["content"] == "hi"

    def test_includes_author_fields(self) -> None:
        """Author fields are preserved so the frontend can render
        ``[Name]:`` attribution for bundled user turns."""
        r = self._make_redis()
        _emit_message(
            r,
            "s1",
            role="user",
            content="answer",
            author_player_id="p-123",
            author_name="Alice",
        )
        decoded = json.loads(r._store[AI_OUTBOX_KEY][-1])  # type: ignore[attr-defined]
        assert decoded["author_player_id"] == "p-123"
        assert decoded["author_name"] == "Alice"

    def test_default_msg_type_is_message(self) -> None:
        r = self._make_redis()
        returned = _emit_message(r, "s1", role="system", content="hi")
        assert returned["type"] == "message"

    def test_plan_msg_type_preserved(self) -> None:
        """Emitting a plan sets ``type: "plan"`` on the envelope — the
        bridge writes this through verbatim so the frontend's final-plan
        detection works."""
        r = self._make_redis()
        _emit_message(
            r,
            "s1",
            role="assistant",
            content="## FINAL PLAN\n...",
            author_name="Interviewer",
            msg_type="plan",
        )
        decoded = json.loads(r._store[AI_OUTBOX_KEY][-1])  # type: ignore[attr-defined]
        assert decoded["type"] == "plan"
