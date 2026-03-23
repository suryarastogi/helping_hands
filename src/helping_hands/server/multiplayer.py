"""WebSocket-based multiplayer synchronisation for Hand World.

Manages connected players and broadcasts position updates so that
multiple browser windows can see each other's avatars in real-time.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Player avatar colour palette — visually distinct, ordered by hue.
_PLAYER_COLORS = [
    "#e11d48",  # rose
    "#2563eb",  # blue
    "#16a34a",  # green
    "#d97706",  # amber
    "#7c3aed",  # violet
    "#0891b2",  # cyan
    "#dc2626",  # red
    "#4f46e5",  # indigo
    "#059669",  # emerald
    "#c026d3",  # fuchsia
]

_MAX_PLAYERS = 20
"""Hard cap on simultaneous connections to avoid resource exhaustion."""

_POSITION_KEYS = {"x", "y", "direction", "walking"}
"""Required keys in a position update message."""

_VALID_DIRECTIONS = {"up", "down", "left", "right"}

_BOUNDS_MIN_X = 4.0
_BOUNDS_MAX_X = 96.0
_BOUNDS_MIN_Y = 6.0
_BOUNDS_MAX_Y = 92.0


@dataclass
class PlayerState:
    """Tracks a single connected player."""

    player_id: str
    name: str
    color: str
    x: float = 50.0
    y: float = 50.0
    direction: str = "down"
    walking: bool = False
    websocket: WebSocket = field(repr=False, compare=False, default=None)  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-friendly dict (excludes the websocket)."""
        return {
            "player_id": self.player_id,
            "name": self.name,
            "color": self.color,
            "x": self.x,
            "y": self.y,
            "direction": self.direction,
            "walking": self.walking,
        }


class WorldConnectionManager:
    """Manages the set of connected Hand World players.

    Thread-safety note: FastAPI's WebSocket handling is async and
    single-threaded per event-loop, so a plain dict is sufficient.
    """

    def __init__(self) -> None:
        self._players: dict[str, PlayerState] = {}
        self._color_index = 0

    @property
    def player_count(self) -> int:
        """Return the number of currently connected players."""
        return len(self._players)

    def _next_color(self) -> str:
        color = _PLAYER_COLORS[self._color_index % len(_PLAYER_COLORS)]
        self._color_index += 1
        return color

    async def connect(self, websocket: WebSocket) -> PlayerState | None:
        """Accept a WebSocket and register a new player.

        Returns ``None`` if the server is at capacity.
        """
        if len(self._players) >= _MAX_PLAYERS:
            await websocket.close(code=1013, reason="Server at capacity")
            return None

        await websocket.accept()

        player_id = uuid.uuid4().hex[:8]
        player_number = self._color_index + 1
        player = PlayerState(
            player_id=player_id,
            name=f"Player {player_number}",
            color=self._next_color(),
            websocket=websocket,
        )
        self._players[player_id] = player

        # Send the newcomer the full state of existing players.
        existing = [p.to_dict() for p in self._players.values()]
        await websocket.send_json(
            {"type": "players_sync", "your_id": player_id, "players": existing}
        )

        # Tell everyone else about the new arrival.
        await self._broadcast(
            {"type": "player_joined", **player.to_dict()},
            exclude=player_id,
        )

        logger.info(
            "Player %s (%s) connected — %d total",
            player_id,
            player.name,
            len(self._players),
        )
        return player

    async def disconnect(self, player_id: str) -> None:
        """Remove a player and notify the remaining clients."""
        player = self._players.pop(player_id, None)
        if player is None:
            return

        await self._broadcast(
            {"type": "player_left", "player_id": player_id},
            exclude=player_id,
        )
        logger.info(
            "Player %s disconnected — %d remaining",
            player_id,
            len(self._players),
        )

    async def handle_position(self, player_id: str, data: dict[str, Any]) -> None:
        """Process and broadcast a position update from *player_id*."""
        player = self._players.get(player_id)
        if player is None:
            return

        x = float(data.get("x", player.x))
        y = float(data.get("y", player.y))
        direction = data.get("direction", player.direction)
        walking = bool(data.get("walking", player.walking))

        # Clamp to scene bounds.
        x = max(_BOUNDS_MIN_X, min(_BOUNDS_MAX_X, x))
        y = max(_BOUNDS_MIN_Y, min(_BOUNDS_MAX_Y, y))

        if direction not in _VALID_DIRECTIONS:
            direction = player.direction

        player.x = x
        player.y = y
        player.direction = direction
        player.walking = walking

        await self._broadcast(
            {
                "type": "player_moved",
                "player_id": player_id,
                "x": x,
                "y": y,
                "direction": direction,
                "walking": walking,
            },
            exclude=player_id,
        )

    async def _broadcast(
        self, message: dict[str, Any], *, exclude: str | None = None
    ) -> None:
        """Send *message* to every connected player except *exclude*."""
        text = json.dumps(message)
        dead: list[str] = []
        for pid, player in self._players.items():
            if pid == exclude:
                continue
            try:
                await player.websocket.send_text(text)
            except Exception:
                dead.append(pid)

        # Clean up any connections that died while broadcasting.
        for pid in dead:
            self._players.pop(pid, None)


# Module-level singleton — shared across all WebSocket connections.
world_manager = WorldConnectionManager()


async def world_websocket_endpoint(websocket: WebSocket) -> None:
    """FastAPI WebSocket handler for ``/ws/world``."""
    player = await world_manager.connect(websocket)
    if player is None:
        return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue

            msg_type = data.get("type")
            if msg_type == "position":
                await world_manager.handle_position(player.player_id, data)
            # Future message types (e.g. chat, emotes) can be added here.
    except WebSocketDisconnect:
        pass
    finally:
        await world_manager.disconnect(player.player_id)
