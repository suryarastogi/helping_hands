"""Multiplayer WebSocket relay for Hand World awareness sync.

Uses yjs awareness protocol to broadcast player presence (position, direction,
walking state, color) between connected clients.  The server acts as a simple
relay — it does not interpret yjs messages, just forwards them to all peers
in the same room.

The implementation intentionally avoids ``pycrdt`` document state on the server
side.  For the awareness-only use-case (ephemeral presence data, no persistent
document), a raw relay is simpler, more testable, and has fewer dependencies.
``pycrdt-websocket`` is still listed as a dependency for future document-sync
features (e.g., shared annotations).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# ── yjs protocol message types ──────────────────────────────────────────
# https://github.com/yjs/y-protocols — first byte indicates message kind.
MSG_SYNC = 0
MSG_AWARENESS = 1

__all__ = [
    "MSG_AWARENESS",
    "MSG_SYNC",
    "MultiplayerRoom",
    "mount_multiplayer",
]


class MultiplayerRoom:
    """In-memory room that relays WebSocket messages to all connected peers.

    Thread-safe: all mutation happens inside a single asyncio event loop.
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        """Return current number of connected clients."""
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        logger.info("Multiplayer client connected (total=%d)", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a client from the room."""
        async with self._lock:
            self._clients.discard(ws)
        logger.info("Multiplayer client disconnected (total=%d)", len(self._clients))

    async def broadcast(self, data: bytes, *, sender: WebSocket) -> None:
        """Forward *data* to every client except *sender*."""
        async with self._lock:
            peers = [c for c in self._clients if c is not sender]
        for peer in peers:
            try:
                await peer.send_bytes(data)
            except Exception:
                logger.debug("Failed to send to peer, will be cleaned up")

    async def handle(self, ws: WebSocket) -> None:
        """Run the receive loop for a single client until disconnect."""
        await self.connect(ws)
        try:
            while True:
                data = await ws.receive_bytes()
                await self.broadcast(data, sender=ws)
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(ws)


# Module-level default room instance (shared across requests).
_default_room = MultiplayerRoom()


def get_default_room() -> MultiplayerRoom:
    """Return the module-level default :class:`MultiplayerRoom`."""
    return _default_room


def mount_multiplayer(application: FastAPI) -> None:
    """Register the ``/ws/world`` WebSocket endpoint on *application*."""

    @application.websocket("/ws/world")
    async def _world_ws(ws: WebSocket) -> None:
        await _default_room.handle(ws)
