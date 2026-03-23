"""Tests for the Hand World multiplayer WebSocket module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from helping_hands.server.multiplayer import (
    _BOUNDS_MAX_X,
    _BOUNDS_MIN_Y,
    _MAX_PLAYERS,
    _PLAYER_COLORS,
    _VALID_EMOTES,
    PlayerState,
    WorldConnectionManager,
    world_websocket_endpoint,
)

# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------


class TestPlayerState:
    """Unit tests for PlayerState dataclass."""

    def test_to_dict_excludes_websocket(self) -> None:
        player = PlayerState(
            player_id="abc",
            name="Player 1",
            color="#e11d48",
            x=10.0,
            y=20.0,
            direction="left",
            walking=True,
        )
        d = player.to_dict()
        assert d == {
            "player_id": "abc",
            "name": "Player 1",
            "color": "#e11d48",
            "x": 10.0,
            "y": 20.0,
            "direction": "left",
            "walking": True,
        }
        assert "websocket" not in d

    def test_default_values(self) -> None:
        player = PlayerState(player_id="x", name="P", color="#000")
        assert player.x == 50.0
        assert player.y == 50.0
        assert player.direction == "down"
        assert player.walking is False


# ---------------------------------------------------------------------------
# WorldConnectionManager
# ---------------------------------------------------------------------------


def _make_ws() -> AsyncMock:
    """Create a mock WebSocket with the methods we use."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestWorldConnectionManager:
    """Unit tests for the connection manager."""

    @pytest.mark.asyncio
    async def test_connect_sends_sync_and_assigns_id(self) -> None:
        mgr = WorldConnectionManager()
        ws = _make_ws()
        player = await mgr.connect(ws)

        assert player is not None
        assert len(player.player_id) == 8
        assert player.color == _PLAYER_COLORS[0]
        assert mgr.player_count == 1

        # Should have called accept + send_json (players_sync).
        ws.accept.assert_awaited_once()
        ws.send_json.assert_awaited_once()
        sync_msg = ws.send_json.call_args[0][0]
        assert sync_msg["type"] == "players_sync"
        assert sync_msg["your_id"] == player.player_id

    @pytest.mark.asyncio
    async def test_second_player_gets_join_broadcast(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None
        assert mgr.player_count == 2

        # ws1 should have received a player_joined broadcast for p2.
        broadcast_calls = ws1.send_text.call_args_list
        assert len(broadcast_calls) == 1
        msg = json.loads(broadcast_calls[0][0][0])
        assert msg["type"] == "player_joined"
        assert msg["player_id"] == p2.player_id

    @pytest.mark.asyncio
    async def test_disconnect_broadcasts_player_left(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        ws1.send_text.reset_mock()
        await mgr.disconnect(p2.player_id)
        assert mgr.player_count == 1

        broadcast_calls = ws1.send_text.call_args_list
        assert len(broadcast_calls) == 1
        msg = json.loads(broadcast_calls[0][0][0])
        assert msg["type"] == "player_left"
        assert msg["player_id"] == p2.player_id

    @pytest.mark.asyncio
    async def test_disconnect_unknown_player_is_noop(self) -> None:
        mgr = WorldConnectionManager()
        await mgr.disconnect("nonexistent")  # Should not raise.
        assert mgr.player_count == 0

    @pytest.mark.asyncio
    async def test_handle_position_broadcasts_and_clamps(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        ws2.send_text.reset_mock()

        # p1 moves to out-of-bounds coords.
        await mgr.handle_position(
            p1.player_id,
            {"x": 200.0, "y": -10.0, "direction": "right", "walking": True},
        )

        # Verify clamping.
        assert p1.x == _BOUNDS_MAX_X
        assert p1.y == _BOUNDS_MIN_Y
        assert p1.direction == "right"
        assert p1.walking is True

        # ws2 should have received the update (clamped values).
        broadcast_calls = ws2.send_text.call_args_list
        assert len(broadcast_calls) == 1
        msg = json.loads(broadcast_calls[0][0][0])
        assert msg["type"] == "player_moved"
        assert msg["x"] == _BOUNDS_MAX_X
        assert msg["y"] == _BOUNDS_MIN_Y

    @pytest.mark.asyncio
    async def test_handle_position_invalid_direction_keeps_old(self) -> None:
        mgr = WorldConnectionManager()
        ws = _make_ws()
        player = await mgr.connect(ws)
        assert player is not None

        await mgr.handle_position(
            player.player_id,
            {"x": 50, "y": 50, "direction": "invalid", "walking": False},
        )
        assert player.direction == "down"  # Default unchanged.

    @pytest.mark.asyncio
    async def test_capacity_limit(self) -> None:
        mgr = WorldConnectionManager()
        websockets = []
        for _ in range(_MAX_PLAYERS):
            ws = _make_ws()
            websockets.append(ws)
            player = await mgr.connect(ws)
            assert player is not None

        assert mgr.player_count == _MAX_PLAYERS

        # Next connection should be rejected.
        ws_extra = _make_ws()
        result = await mgr.connect(ws_extra)
        assert result is None
        ws_extra.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_color_cycling(self) -> None:
        mgr = WorldConnectionManager()
        colors = []
        for _ in range(len(_PLAYER_COLORS) + 1):
            ws = _make_ws()
            player = await mgr.connect(ws)
            assert player is not None
            colors.append(player.color)

        # First N colours should match the palette.
        assert colors[: len(_PLAYER_COLORS)] == _PLAYER_COLORS
        # N+1 wraps around.
        assert colors[len(_PLAYER_COLORS)] == _PLAYER_COLORS[0]

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()
        ws2.send_text.side_effect = ConnectionError("gone")

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None
        assert mgr.player_count == 2

        # When p1 moves, broadcast to p2 will fail → p2 gets removed.
        await mgr.handle_position(
            p1.player_id,
            {"x": 60, "y": 60, "direction": "up", "walking": False},
        )
        assert mgr.player_count == 1
        assert p2.player_id not in mgr._players


# ---------------------------------------------------------------------------
# Emote handling
# ---------------------------------------------------------------------------


class TestEmoteHandling:
    """Unit tests for emote broadcast logic."""

    @pytest.mark.asyncio
    async def test_valid_emote_broadcasts_to_others(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        ws2.send_text.reset_mock()

        await mgr.handle_emote(p1.player_id, {"emote": "wave"})

        broadcast_calls = ws2.send_text.call_args_list
        assert len(broadcast_calls) == 1
        msg = json.loads(broadcast_calls[0][0][0])
        assert msg["type"] == "player_emoted"
        assert msg["player_id"] == p1.player_id
        assert msg["emote"] == "wave"

    @pytest.mark.asyncio
    async def test_invalid_emote_is_silently_ignored(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        ws2.send_text.reset_mock()

        await mgr.handle_emote(p1.player_id, {"emote": "invalid_emote"})

        # No broadcast should have been sent.
        ws2.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_emote_from_unknown_player_is_noop(self) -> None:
        mgr = WorldConnectionManager()
        ws = _make_ws()
        await mgr.connect(ws)

        # Should not raise.
        await mgr.handle_emote("nonexistent", {"emote": "wave"})

    @pytest.mark.asyncio
    async def test_emote_not_sent_back_to_sender(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()

        p1 = await mgr.connect(ws1)
        assert p1 is not None

        ws1.send_text.reset_mock()

        await mgr.handle_emote(p1.player_id, {"emote": "celebrate"})

        # Sender should not receive their own emote.
        ws1.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_all_valid_emotes_are_accepted(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        for emote in _VALID_EMOTES:
            ws2.send_text.reset_mock()
            await mgr.handle_emote(p1.player_id, {"emote": emote})
            assert ws2.send_text.call_count == 1
            msg = json.loads(ws2.send_text.call_args[0][0])
            assert msg["emote"] == emote

    @pytest.mark.asyncio
    async def test_emote_missing_key_is_ignored(self) -> None:
        mgr = WorldConnectionManager()
        ws1 = _make_ws()
        ws2 = _make_ws()

        p1 = await mgr.connect(ws1)
        p2 = await mgr.connect(ws2)
        assert p1 is not None and p2 is not None

        ws2.send_text.reset_mock()

        # No "emote" key in data.
        await mgr.handle_emote(p1.player_id, {})

        ws2.send_text.assert_not_awaited()


# ---------------------------------------------------------------------------
# WebSocket endpoint integration
# ---------------------------------------------------------------------------


class TestWorldWebSocketEndpoint:
    """Integration-style test for the endpoint function."""

    @pytest.mark.asyncio
    async def test_endpoint_handles_position_then_disconnect(self) -> None:
        ws = _make_ws()
        pos_msg = json.dumps(
            {"type": "position", "x": 30, "y": 40, "direction": "left", "walking": True}
        )
        # Simulate: first receive returns a position, second raises disconnect.
        from fastapi import WebSocketDisconnect

        ws.receive_text = AsyncMock(side_effect=[pos_msg, WebSocketDisconnect()])

        # Use a fresh manager to avoid pollution from other tests.
        fresh_mgr = WorldConnectionManager()
        with patch("helping_hands.server.multiplayer.world_manager", fresh_mgr):
            await world_websocket_endpoint(ws)

        # Player should have been cleaned up.
        assert fresh_mgr.player_count == 0

    @pytest.mark.asyncio
    async def test_endpoint_handles_emote_then_disconnect(self) -> None:
        ws = _make_ws()
        emote_msg = json.dumps({"type": "emote", "emote": "sparkle"})
        from fastapi import WebSocketDisconnect

        ws.receive_text = AsyncMock(side_effect=[emote_msg, WebSocketDisconnect()])

        fresh_mgr = WorldConnectionManager()
        with patch("helping_hands.server.multiplayer.world_manager", fresh_mgr):
            await world_websocket_endpoint(ws)

        assert fresh_mgr.player_count == 0

    @pytest.mark.asyncio
    async def test_endpoint_ignores_malformed_json(self) -> None:
        ws = _make_ws()
        from fastapi import WebSocketDisconnect

        ws.receive_text = AsyncMock(side_effect=["not-json", WebSocketDisconnect()])

        fresh_mgr = WorldConnectionManager()
        with patch("helping_hands.server.multiplayer.world_manager", fresh_mgr):
            await world_websocket_endpoint(ws)

        assert fresh_mgr.player_count == 0
