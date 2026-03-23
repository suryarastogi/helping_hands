"""Yjs-based multiplayer synchronisation for Hand World.

Uses ``pycrdt-websocket`` to provide a standards-compliant Yjs WebSocket
server.  The Yjs *awareness* layer carries ephemeral player presence
(position, direction, walking state, emotes) while the Y.Doc itself stays
empty — we only need presence, not persistent shared state.

If ``pycrdt-websocket`` is not installed the module exposes ``None``
sentinels so the rest of the server can start without it.
"""

from __future__ import annotations

import logging
from typing import Any

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
