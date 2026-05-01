"""Tests for the multiplayer-grill bridge (server/mgrill_bridge.py).

The bridge is the option-(2) pub/sub glue: Celery workers push AI-produced
message envelopes onto a shared Redis list (``mgrill:ai_outbox``); a
long-running asyncio task in the FastAPI process drains that list and
appends each envelope to the matching Yjs room's ``messages`` Y.Array.

These tests cover the pure logic — envelope routing, missing-session
handling, and malformed entries — without spinning up a real Redis or Yjs
server.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.server.mgrill_bridge import (
    AI_OUTBOX_KEY,
    LEADER_KEY,
    _append_to_room,
    _release_leader,
    _renew_leader,
    _try_acquire_leader,
    mgrill_room_name,
    start_mgrill_bridge,
    stop_mgrill_bridge,
)


class TestRoomNaming:
    def test_room_name_format(self) -> None:
        # Full-mount-prefixed path — Starlette does NOT strip the mount
        # prefix from scope["path"], so the Yjs server keys rooms by the
        # whole ``/ws/yjs/...`` string.  See helper docstring.
        assert mgrill_room_name("abc-123") == "/ws/yjs/mgrill-abc-123"

    def test_outbox_key(self) -> None:
        assert AI_OUTBOX_KEY == "mgrill:ai_outbox"

    def test_leader_key(self) -> None:
        assert LEADER_KEY == "mgrill:bridge:leader"


class TestAppendToRoom:
    """``_append_to_room`` must correctly route envelopes to the right room
    and strip the ``session_id`` field before storing (the room identity
    already encodes it)."""

    @pytest.mark.asyncio
    async def test_routes_to_matching_room(self) -> None:
        # Mock Y.Doc + Array behaviour (pycrdt is optional).
        fake_array = MagicMock()
        fake_array.append = MagicMock()
        fake_ydoc = MagicMock()
        fake_ydoc.__getitem__.side_effect = lambda k: (
            fake_array if k == "messages" else (_ for _ in ()).throw(KeyError(k))
        )
        fake_ydoc.__setitem__ = MagicMock()

        fake_room = MagicMock()
        fake_room.ydoc = fake_ydoc

        fake_server = MagicMock()
        fake_server.get_room = AsyncMock(return_value=fake_room)

        envelope = {
            "session_id": "s1",
            "id": "m1",
            "role": "assistant",
            "content": "hi",
            "type": "message",
        }
        await _append_to_room(fake_server, envelope)

        fake_server.get_room.assert_awaited_once_with("/ws/yjs/mgrill-s1")
        # session_id stripped before Y.Array.append.
        fake_array.append.assert_called_once()
        appended = fake_array.append.call_args[0][0]
        assert appended["id"] == "m1"
        assert "session_id" not in appended

    @pytest.mark.asyncio
    async def test_creates_array_when_missing(self) -> None:
        """If the Y.Doc has no ``messages`` key yet, one is created."""
        keys: dict[str, object] = {}
        fake_array = MagicMock()
        fake_array.append = MagicMock()

        def getitem(k: str) -> object:
            if k in keys:
                return keys[k]
            raise KeyError(k)

        def setitem(k: str, v: object) -> None:
            # Substitute our mock array so the subsequent getitem returns it.
            keys[k] = fake_array

        fake_ydoc = MagicMock()
        fake_ydoc.__getitem__.side_effect = getitem
        fake_ydoc.__setitem__.side_effect = setitem
        fake_room = MagicMock()
        fake_room.ydoc = fake_ydoc
        fake_server = MagicMock()
        fake_server.get_room = AsyncMock(return_value=fake_room)

        await _append_to_room(
            fake_server,
            {"session_id": "s1", "id": "m1", "role": "assistant", "content": "hi"},
        )
        fake_array.append.assert_called_once()

    @pytest.mark.asyncio
    async def test_drops_envelope_missing_session_id(self) -> None:
        fake_server = MagicMock()
        fake_server.get_room = AsyncMock()
        await _append_to_room(fake_server, {"id": "m1", "role": "assistant"})
        fake_server.get_room.assert_not_called()

    @pytest.mark.asyncio
    async def test_tolerates_get_room_failure(self) -> None:
        """A thrown exception from ``get_room`` must not crash the bridge."""
        fake_server = MagicMock()
        fake_server.get_room = AsyncMock(side_effect=RuntimeError("boom"))
        # Should not raise.
        await _append_to_room(
            fake_server,
            {"session_id": "s1", "id": "m1", "role": "assistant", "content": "x"},
        )


class TestLeaderLock:
    """The lock helpers use SET NX EX / Lua GET+PEXPIRE / Lua GET+DEL.

    These tests stub redis.asyncio so we can verify the exact arguments —
    drift here silently breaks coordination between bridges."""

    @pytest.mark.asyncio
    async def test_acquire_uses_nx_and_ex(self) -> None:
        r = MagicMock()
        r.set = AsyncMock(return_value=True)
        got = await _try_acquire_leader(r, "tok-123")
        assert got is True
        r.set.assert_awaited_once()
        kwargs = r.set.call_args.kwargs
        args = r.set.call_args.args
        assert args[0] == LEADER_KEY
        assert args[1] == "tok-123"
        # nx=True, ex=<ttl seconds>
        assert kwargs.get("nx") is True
        assert isinstance(kwargs.get("ex"), int) and kwargs["ex"] > 0

    @pytest.mark.asyncio
    async def test_acquire_returns_false_on_contention(self) -> None:
        r = MagicMock()
        r.set = AsyncMock(return_value=False)
        got = await _try_acquire_leader(r, "tok-123")
        assert got is False

    @pytest.mark.asyncio
    async def test_acquire_swallows_errors(self) -> None:
        """Redis transport errors must not crash the loop — caller retries."""
        r = MagicMock()
        r.set = AsyncMock(side_effect=RuntimeError("connection refused"))
        got = await _try_acquire_leader(r, "tok-123")
        assert got is False

    @pytest.mark.asyncio
    async def test_renew_success(self) -> None:
        """When the lock still has our token, PEXPIRE runs and returns 1."""
        r = MagicMock()
        r.eval = AsyncMock(return_value=1)
        ok = await _renew_leader(r, "tok-123")
        assert ok is True
        r.eval.assert_awaited_once()
        args = r.eval.call_args.args
        # eval(script, numkeys, key, token, ttl_ms)
        assert args[1] == 1
        assert args[2] == LEADER_KEY
        assert args[3] == "tok-123"

    @pytest.mark.asyncio
    async def test_renew_failure_when_lost(self) -> None:
        """Lua returned 0 → someone else owns the lock now."""
        r = MagicMock()
        r.eval = AsyncMock(return_value=0)
        assert await _renew_leader(r, "tok-123") is False

    @pytest.mark.asyncio
    async def test_renew_swallows_errors(self) -> None:
        r = MagicMock()
        r.eval = AsyncMock(side_effect=RuntimeError("down"))
        assert await _renew_leader(r, "tok-123") is False

    @pytest.mark.asyncio
    async def test_release_compare_and_delete(self) -> None:
        r = MagicMock()
        r.eval = AsyncMock(return_value=1)
        await _release_leader(r, "tok-123")
        r.eval.assert_awaited_once()
        args = r.eval.call_args.args
        assert args[2] == LEADER_KEY
        assert args[3] == "tok-123"

    @pytest.mark.asyncio
    async def test_release_silent_when_already_expired(self) -> None:
        """Release when the lock has already been taken over — must not
        raise, must not accidentally DEL someone else's lock (the Lua
        script's GET-compare is what enforces that on the Redis side)."""
        r = MagicMock()
        r.eval = AsyncMock(return_value=0)
        # Should simply return without raising.
        await _release_leader(r, "tok-123")


class TestLifecycle:
    """``start_mgrill_bridge(None)`` is a no-op so the server still boots
    when ``pycrdt-websocket`` is missing; ``stop`` is idempotent.

    Each test explicitly calls ``stop_mgrill_bridge`` first to clear any
    module-level ``_bridge_task`` left behind by prior tests in the suite
    (other tests instantiate the FastAPI app via ``TestClient`` which
    triggers the lifespan and starts a real bridge task).
    """

    @pytest.mark.asyncio
    async def test_start_no_yjs_server_is_noop(self) -> None:
        await stop_mgrill_bridge()
        await start_mgrill_bridge(None)
        await stop_mgrill_bridge()  # must be safe to call

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self) -> None:
        await stop_mgrill_bridge()
        await stop_mgrill_bridge()

    @pytest.mark.asyncio
    async def test_standby_process_does_not_drain_outbox(self) -> None:
        """A second bridge process that can't acquire the leader lock must
        not consume from the outbox — otherwise we regress to the
        split-brain state that motivated the lock in the first place."""
        await stop_mgrill_bridge()
        fake_server = MagicMock()
        fake_server.get_room = AsyncMock()

        fake_aioredis = MagicMock()
        fake_client = MagicMock()
        # Every acquire attempt fails (someone else holds the lock).
        fake_client.set = AsyncMock(return_value=False)
        fake_client.eval = AsyncMock(return_value=1)
        fake_client.lpop = AsyncMock(return_value=None)
        fake_client.close = AsyncMock()
        fake_aioredis.from_url.return_value = fake_client

        # NB: patch `redis.asyncio` as an attribute of the ``redis`` package.
        # A plain ``sys.modules["redis.asyncio"] = ...`` override is not
        # enough — once ``redis`` has cached the submodule as an attribute,
        # ``import redis.asyncio as aioredis`` resolves via ``getattr(redis,
        # "asyncio")`` and bypasses ``sys.modules``.
        with patch("redis.asyncio", fake_aioredis):
            await start_mgrill_bridge(fake_server)
            # Poll up to 2 s for the task to make its first r.set call.
            for _ in range(40):
                await asyncio.sleep(0.05)
                if fake_client.set.await_count > 0:
                    break
            await stop_mgrill_bridge()
            # The standby bridge must never LPOP the outbox.
            fake_client.lpop.assert_not_called()
            # But it does try to acquire (at least once).
            fake_client.set.assert_awaited()

    @pytest.mark.asyncio
    async def test_start_then_stop_cancels_task(self) -> None:
        """When started, the bridge task runs until ``stop`` cancels it."""
        await stop_mgrill_bridge()
        fake_server = MagicMock()
        fake_server.get_room = AsyncMock()

        fake_aioredis = MagicMock()
        fake_client = MagicMock()
        # Acquire succeeds on first try so the loop enters the draining branch.
        fake_client.set = AsyncMock(return_value=True)
        fake_client.eval = AsyncMock(return_value=1)  # renew / release OK
        fake_client.lpop = AsyncMock(return_value=None)
        fake_client.close = AsyncMock()
        fake_aioredis.from_url.return_value = fake_client

        with patch("redis.asyncio", fake_aioredis):
            await start_mgrill_bridge(fake_server)
            await asyncio.sleep(0.05)
            await stop_mgrill_bridge()
            # After stop, a second stop is a no-op.
            await stop_mgrill_bridge()
