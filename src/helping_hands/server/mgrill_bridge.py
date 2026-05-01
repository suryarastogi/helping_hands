"""In-process bridge from the multiplayer-grill Celery worker to Yjs rooms.

The worker runs in a separate process from the FastAPI server (where the
Yjs ``WebsocketServer`` lives), so it cannot write directly to a room's
``Y.Doc``.  Rather than have the worker speak the Yjs sync protocol over
WebSocket (no client ships with ``pycrdt`` 0.12), the worker pushes each
AI-produced message onto a shared Redis list ``mgrill:ai_outbox`` and this
module's long-running asyncio task drains that list and appends each entry
to the matching room's ``messages`` Y.Array **in-process**.

Why this split:

* ``Y.Array.append`` in-process triggers the existing Yjs sync broadcast
  so all connected frontend clients receive the update with normal
  sub-100 ms latency — no new network hop, no hand-rolled Yjs client.
* Redis still buffers messages when the server is momentarily down: the
  ``LPUSH`` survives, and the bridge drains whatever accumulated on the
  next startup.
* The per-session registry + authoritative state (``status``,
  ``creator_token_hash``, ``turn_count``) stays in Redis so REST
  endpoints and the worker agree on a single source of truth.

Message envelope on the outbox queue::

    {
        "session_id": "<celery task id>",
        "id": "<uuid>",
        "role": "assistant" | "system",
        "content": "...",
        "type": "message" | "plan" | "error" | "timeout",
        "author_name": "Interviewer" | None,
        "author_player_id": None,
        "timestamp": 1699999999.0,
    }
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "AI_OUTBOX_KEY",
    "LEADER_KEY",
    "mgrill_room_name",
    "start_mgrill_bridge",
    "stop_mgrill_bridge",
]

AI_OUTBOX_KEY = "mgrill:ai_outbox"
"""Shared cross-session Redis list that the worker LPUSHes into."""

LEADER_KEY = "mgrill:bridge:leader"
"""Redis lock key ensuring at most one bridge drains the outbox.

When multiple FastAPI processes run (eg. ``uvicorn --workers N`` or leftover
zombies from a sloppy restart) each spins its own ``_bridge_loop`` task.
Without coordination they race on ``LPOP`` — the winner writes to *its*
in-process ``Y.Doc``, which nobody else observes, and the frontend sees
``turn_count`` advance while the transcript stays empty.  The leader lock
forces exactly one bridge to hold the drain right at a time; non-leaders
sleep until the incumbent's TTL lapses (crash recovery) or it releases on
clean shutdown.
"""

_LOCK_TTL_S = 5
"""Lock TTL — if the leader crashes, a challenger can take over within 5 s."""

_LOCK_RENEW_S = 2
"""How often the leader renews its lock while draining (must be < TTL)."""

_ACQUIRE_RETRY_S = 1.0
"""How long non-leaders sleep before re-attempting to acquire."""

_POLL_INTERVAL_S = 0.1
"""How often the bridge re-polls Redis when the queue is empty.

Kept short so worker-produced messages appear in the Yjs room within ~100 ms.
We use ``LPOP`` in a tight loop rather than ``BLPOP`` to avoid holding a
dedicated Redis connection and to make shutdown responsive.
"""

# Lua: atomic "renew if I still own it", returns 1 on success, 0 otherwise.
_LUA_RENEW = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('PEXPIRE', KEYS[1], ARGV[2])
    return 1
else
    return 0
end
"""

# Lua: atomic "release if I still own it".
_LUA_RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('DEL', KEYS[1])
    return 1
else
    return 0
end
"""

_bridge_task: asyncio.Task[None] | None = None


def mgrill_room_name(session_id: str) -> str:
    """Return the Yjs room name for a multiplayer-grill session.

    The pycrdt ``WebsocketServer`` keys rooms by the **full** ``scope["path"]``
    of the incoming WebSocket — contrary to the intuition that Starlette's
    ``app.mount("/ws/yjs", …)`` strips the prefix (it updates
    ``scope["root_path"]`` but not ``scope["path"]``).  Verified empirically:
    a client connecting to ``ws://host/ws/yjs/hand-world`` creates a room
    keyed ``"/ws/yjs/hand-world"`` on the server.  The bridge must call
    ``get_room()`` with the same full-path key or it creates a *second*
    Y.Doc that nobody else observes and every AI message is invisible
    to browsers.
    """
    return f"/ws/yjs/mgrill-{session_id}"


async def _append_to_room(yjs_server: Any, envelope: dict[str, Any]) -> None:
    """Append one outbox entry to the matching room's ``messages`` Y.Array.

    If the Y.Doc does not yet have a ``messages`` Array key, it is created.
    The original envelope is stored minus the ``session_id`` field, since
    the room identity already encodes that.
    """
    from pycrdt import Array

    session_id = envelope.get("session_id")
    if not session_id:
        logger.warning("mgrill_bridge: dropping outbox entry with no session_id")
        return

    room_name = mgrill_room_name(session_id)

    try:
        room = await yjs_server.get_room(room_name)
    except Exception:
        logger.exception("mgrill_bridge: failed to get room %s", room_name)
        return

    ydoc = getattr(room, "ydoc", None)
    if ydoc is None:
        logger.warning("mgrill_bridge: room %s has no ydoc, dropping", room_name)
        return

    # Strip session_id — room identity already encodes it.
    payload = {k: v for k, v in envelope.items() if k != "session_id"}

    try:
        try:
            arr = ydoc["messages"]
        except KeyError:
            ydoc["messages"] = Array()
            arr = ydoc["messages"]
        arr.append(payload)
    except Exception:
        logger.exception(
            "mgrill_bridge: failed to append message to room %s", room_name
        )


async def _try_acquire_leader(r: Any, token: str) -> bool:
    """Attempt to become the drain-leader via ``SET ... NX EX``.

    Returns True if this process now holds the lock.
    """
    try:
        return bool(await r.set(LEADER_KEY, token, nx=True, ex=_LOCK_TTL_S))
    except Exception:
        logger.exception("mgrill_bridge: leader acquire failed")
        return False


async def _renew_leader(r: Any, token: str) -> bool:
    """Renew the lock TTL iff this process still owns it (compare-and-expire).

    Returns True on success.  False means we lost leadership — either the
    lock expired and someone else grabbed it, or it was manually cleared.
    """
    try:
        result = await r.eval(_LUA_RENEW, 1, LEADER_KEY, token, str(_LOCK_TTL_S * 1000))
        return int(result) == 1
    except Exception:
        logger.exception("mgrill_bridge: leader renew failed")
        return False


async def _release_leader(r: Any, token: str) -> None:
    """Release the lock iff this process still owns it (best-effort)."""
    try:
        await r.eval(_LUA_RELEASE, 1, LEADER_KEY, token)
    except Exception:
        logger.debug("mgrill_bridge: leader release failed", exc_info=True)


async def _bridge_loop(yjs_server: Any) -> None:
    """Drain ``mgrill:ai_outbox`` into the matching rooms forever.

    Acquires a Redis leader lock before popping anything.  If another
    process already holds it, this task sleeps and re-attempts — standby
    mode.  On cancellation or lost leadership, releases/abandons the lock
    cleanly so a peer can take over.
    """
    try:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "mgrill_bridge: redis.asyncio not available — multiplayer grill "
            "AI messages will not be broadcast"
        )
        return

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    r = aioredis.from_url(redis_url, decode_responses=True)
    # Unique per-process token — leadership is reclaimable across restarts
    # but not forgeable by a peer that also runs in this process.
    token = f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
    is_leader = False
    last_renew = 0.0
    logger.info("mgrill_bridge: started (token=%s)", token)

    try:
        while True:
            now = asyncio.get_event_loop().time()

            if not is_leader:
                got = await _try_acquire_leader(r, token)
                if not got:
                    await asyncio.sleep(_ACQUIRE_RETRY_S)
                    continue
                is_leader = True
                last_renew = now
                logger.info("mgrill_bridge: acquired leader lock")
            elif now - last_renew >= _LOCK_RENEW_S:
                if not await _renew_leader(r, token):
                    logger.warning(
                        "mgrill_bridge: lost leadership (stale lock?), standing by"
                    )
                    is_leader = False
                    await asyncio.sleep(_ACQUIRE_RETRY_S)
                    continue
                last_renew = now

            try:
                raw = await r.lpop(AI_OUTBOX_KEY)
            except Exception:
                logger.exception("mgrill_bridge: redis LPOP failed")
                await asyncio.sleep(1.0)
                continue

            if raw is None:
                await asyncio.sleep(_POLL_INTERVAL_S)
                continue

            try:
                envelope = json.loads(raw)
            except (TypeError, ValueError):
                logger.warning("mgrill_bridge: invalid JSON in outbox, skipping")
                continue

            if not isinstance(envelope, dict):
                logger.warning("mgrill_bridge: non-dict outbox entry, skipping")
                continue

            await _append_to_room(yjs_server, envelope)

    except asyncio.CancelledError:
        logger.info("mgrill_bridge: cancelled, shutting down")
        raise
    finally:
        if is_leader:
            await _release_leader(r, token)
        with contextlib.suppress(Exception):
            await r.close()  # type: ignore[misc]


async def start_mgrill_bridge(yjs_server: Any | None) -> None:
    """Spawn the bridge task, wired to *yjs_server*.

    Safe to call when the Yjs server is not available (pycrdt-websocket not
    installed) — the bridge is skipped with a log line and multiplayer grill
    falls back to "frontend sees messages only via state polling", which is
    the behaviour before option (2).
    """
    global _bridge_task

    if yjs_server is None:
        logger.info("mgrill_bridge: Yjs server unavailable, bridge disabled")
        return

    if _bridge_task is not None and not _bridge_task.done():
        logger.debug("mgrill_bridge: already running, skipping start")
        return

    _bridge_task = asyncio.create_task(_bridge_loop(yjs_server))


async def stop_mgrill_bridge() -> None:
    """Cancel and await the bridge task.

    Defensively handles a stale ``_bridge_task`` bound to a closed event
    loop (can happen across pytest-asyncio test boundaries): we can't
    ``await`` such a task from the current loop, so we simply drop the
    reference and let the garbage collector handle it.
    """
    global _bridge_task

    if _bridge_task is None:
        return

    try:
        task_loop = _bridge_task.get_loop()
    except (AttributeError, RuntimeError):  # pragma: no cover
        task_loop = None

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover — not called from async context
        current_loop = None

    if (
        task_loop is not None
        and current_loop is not None
        and task_loop is not current_loop
    ):
        # Cross-loop stale reference; can't await safely.
        _bridge_task = None
        return

    if not _bridge_task.done():
        _bridge_task.cancel()
    try:
        await _bridge_task
    except asyncio.CancelledError:
        pass
    except Exception:  # pragma: no cover — best-effort cleanup
        logger.exception("mgrill_bridge: error during shutdown")
    finally:
        _bridge_task = None
