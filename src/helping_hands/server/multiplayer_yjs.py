"""Yjs-based multiplayer synchronisation for Hand World.

Uses ``pycrdt-websocket`` to provide a standards-compliant Yjs WebSocket
server.  The Yjs *awareness* layer carries ephemeral player presence
(position, direction, walking state, emotes, chat, typing, idle) while
the Y.Doc carries persistent shared state such as the ``"decorations"``
Y.Map (emoji markers placed by players in the scene).

If ``pycrdt-websocket`` is not installed the module exposes ``None``
sentinels so the rest of the server can start without it.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

try:
    from pycrdt_websocket import (  # type: ignore[import-untyped]
        ASGIServer,
        WebsocketServer,
    )

    _HAS_PYCRDT = True
except ImportError:  # pragma: no cover
    _HAS_PYCRDT = False

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Singleton instances — initialised lazily via ``create_yjs_app()``.
yjs_websocket_server: Any | None = None
yjs_asgi_app: Any | None = None


def create_yjs_app() -> Any | None:
    """Create and return the ASGI sub-application for Yjs WebSocket sync.

    Returns ``None`` if ``pycrdt-websocket`` is not available.  The caller
    should skip mounting in that case and log a warning.
    """
    global yjs_websocket_server, yjs_asgi_app

    if not _HAS_PYCRDT:
        logger.warning(
            "pycrdt-websocket is not installed — Yjs multiplayer disabled. "
            "Install with: pip install 'pycrdt>=0.12' 'pycrdt-websocket>=0.15'"
        )
        return None

    yjs_websocket_server = WebsocketServer()
    yjs_asgi_app = ASGIServer(yjs_websocket_server)

    logger.info("Yjs WebSocket server created (mount at /ws/yjs)")
    return yjs_asgi_app


async def start_yjs_server() -> None:
    """Start the Yjs WebSocket server background task.

    Must be called during FastAPI startup (after ``create_yjs_app``).
    """
    if yjs_websocket_server is not None:
        await yjs_websocket_server.start()
        logger.info("Yjs WebSocket server started")


async def stop_yjs_server() -> None:
    """Stop the Yjs WebSocket server.

    Must be called during FastAPI shutdown.
    """
    if yjs_websocket_server is not None:
        await yjs_websocket_server.stop()
        logger.info("Yjs WebSocket server stopped")


def get_multiplayer_stats() -> dict[str, object]:
    """Return current multiplayer room/connection statistics.

    Queries the ``WebsocketServer`` singleton for room and connection counts.
    Returns a dict suitable for JSON serialisation::

        {"available": True, "rooms": 1, "connections": 3}

    When pycrdt-websocket is not installed or the server has not been
    created, returns ``{"available": False, "rooms": 0, "connections": 0}``.
    """
    if yjs_websocket_server is None:
        return {"available": False, "rooms": 0, "connections": 0}

    try:
        rooms = getattr(yjs_websocket_server, "rooms", {})
        room_count = len(rooms)
        connection_count = 0
        for room in rooms.values():
            clients = getattr(room, "clients", [])
            connection_count += len(clients)
        return {
            "available": True,
            "rooms": room_count,
            "connections": connection_count,
        }
    except Exception:
        logger.debug("Failed to read multiplayer stats", exc_info=True)
        return {"available": True, "rooms": 0, "connections": 0}


def get_connected_players() -> dict[str, object]:
    """Return a list of connected players with their awareness metadata.

    Iterates over Yjs rooms, reads each client's awareness state, and
    extracts player fields (``player_id``, ``name``, ``color``, ``x``,
    ``y``, ``idle``).  Returns::

        {
            "players": [
                {"player_id": "abc", "name": "Alice", "color": "#e74c3c",
                 "x": 50.0, "y": 50.0, "idle": false},
                ...
            ],
            "count": 1
        }

    When the Yjs server is unavailable, returns an empty player list.
    """
    if yjs_websocket_server is None:
        return {"players": [], "count": 0}

    players: list[dict[str, object]] = []
    try:
        rooms = getattr(yjs_websocket_server, "rooms", {})
        for room in rooms.values():
            awareness = getattr(room, "awareness", None)
            if awareness is None:
                continue
            # awareness.states is a dict[int, bytes] of encoded state per client
            states: dict[int, bytes] = getattr(awareness, "states", {})
            for _client_id, raw_state in states.items():
                state = _parse_awareness_state(raw_state)
                if state is None:
                    continue
                players.append(
                    {
                        "player_id": state.get("player_id", ""),
                        "name": state.get("name", ""),
                        "color": state.get("color", ""),
                        "x": state.get("x", 0),
                        "y": state.get("y", 0),
                        "idle": state.get("idle", False),
                    }
                )
    except Exception:
        logger.debug("Failed to read connected players", exc_info=True)

    return {"players": players, "count": len(players)}


def _parse_awareness_state(raw: object) -> dict[str, Any] | None:
    """Best-effort decode of an awareness state entry.

    The state may already be a dict (pycrdt in-process) or a JSON-encoded
    bytes/str blob (wire format).  Returns ``None`` on failure.
    """
    if isinstance(raw, dict):
        return cast(dict[str, Any], raw)
    try:
        if isinstance(raw, (bytes, bytearray)):
            return json.loads(raw.decode("utf-8", errors="replace"))  # type: ignore[no-any-return]
        if isinstance(raw, str):
            return json.loads(raw)  # type: ignore[no-any-return]
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return None
