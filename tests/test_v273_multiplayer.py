"""Tests for the multiplayer WebSocket relay (v273).

Covers:
- MultiplayerRoom lifecycle (connect, disconnect, broadcast)
- Message relay between multiple clients
- mount_multiplayer route registration
- Module exports and docstrings
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from helping_hands.server.multiplayer import (
    MSG_AWARENESS,
    MSG_SYNC,
    MultiplayerRoom,
    get_default_room,
    mount_multiplayer,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_ws() -> AsyncMock:
    """Create a mock WebSocket with async send/receive methods."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.receive_bytes = AsyncMock()
    return ws


def _run(coro):  # noqa: ANN001, ANN202
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ── MultiplayerRoom unit tests ──────────────────────────────────────────


class TestMultiplayerRoom:
    """Unit tests for MultiplayerRoom."""

    def test_initial_client_count(self) -> None:
        room = MultiplayerRoom()
        assert room.client_count == 0

    def test_connect_increments_count(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            await room.connect(ws)
            assert room.client_count == 1
            ws.accept.assert_awaited_once()

        _run(_test())

    def test_disconnect_decrements_count(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            await room.connect(ws)
            await room.disconnect(ws)
            assert room.client_count == 0

        _run(_test())

    def test_disconnect_unknown_client_is_safe(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            await room.disconnect(ws)
            assert room.client_count == 0

        _run(_test())

    def test_broadcast_sends_to_peers_not_sender(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws_a = _make_ws()
            ws_b = _make_ws()
            ws_c = _make_ws()
            await room.connect(ws_a)
            await room.connect(ws_b)
            await room.connect(ws_c)

            data = b"\x01test-awareness"
            await room.broadcast(data, sender=ws_a)

            ws_a.send_bytes.assert_not_awaited()
            ws_b.send_bytes.assert_awaited_once_with(data)
            ws_c.send_bytes.assert_awaited_once_with(data)

        _run(_test())

    def test_broadcast_tolerates_send_failure(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws_a = _make_ws()
            ws_b = _make_ws()
            ws_b.send_bytes.side_effect = RuntimeError("connection lost")
            ws_c = _make_ws()
            await room.connect(ws_a)
            await room.connect(ws_b)
            await room.connect(ws_c)

            data = b"\x01hello"
            await room.broadcast(data, sender=ws_a)

            ws_c.send_bytes.assert_awaited_once_with(data)

        _run(_test())

    def test_broadcast_no_peers(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            await room.connect(ws)
            await room.broadcast(b"\x00sync", sender=ws)
            ws.send_bytes.assert_not_awaited()

        _run(_test())

    def test_multiple_connect_disconnect_cycles(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            await room.connect(ws)
            assert room.client_count == 1
            await room.disconnect(ws)
            assert room.client_count == 0
            await room.connect(ws)
            assert room.client_count == 1

        _run(_test())


class TestMultiplayerRoomHandle:
    """Tests for the full handle() receive loop."""

    def test_handle_relays_messages_then_disconnects(self) -> None:
        from fastapi import WebSocketDisconnect

        async def _test() -> None:
            room = MultiplayerRoom()
            ws_sender = _make_ws()
            ws_receiver = _make_ws()

            ws_sender.receive_bytes.side_effect = [
                b"\x01msg1",
                b"\x01msg2",
                WebSocketDisconnect(),
            ]

            await room.connect(ws_receiver)
            await room.handle(ws_sender)

            assert ws_receiver.send_bytes.await_count == 2
            calls = [
                c.args[0] for c in ws_receiver.send_bytes.await_args_list
            ]
            assert calls == [b"\x01msg1", b"\x01msg2"]
            assert room.client_count == 1

        _run(_test())

    def test_handle_cleans_up_on_unexpected_error(self) -> None:
        async def _test() -> None:
            room = MultiplayerRoom()
            ws = _make_ws()
            ws.receive_bytes.side_effect = ConnectionError("reset")

            # handle should not propagate the error and should clean up.
            try:
                await room.handle(ws)
            except ConnectionError:
                pass
            # Either way, client should be removed from the room.
            assert room.client_count == 0

        _run(_test())


# ── Module-level exports ─────────────────────────────────────────────────


class TestModuleExports:
    """Verify module-level constants and functions."""

    def test_msg_constants(self) -> None:
        assert MSG_SYNC == 0
        assert MSG_AWARENESS == 1

    def test_get_default_room_returns_same_instance(self) -> None:
        r1 = get_default_room()
        r2 = get_default_room()
        assert r1 is r2
        assert isinstance(r1, MultiplayerRoom)

    def test_module_has_docstring(self) -> None:
        import helping_hands.server.multiplayer as mod

        assert mod.__doc__ is not None
        assert "awareness" in mod.__doc__.lower()

    def test_all_exports(self) -> None:
        import helping_hands.server.multiplayer as mod

        assert hasattr(mod, "__all__")
        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"


# ── mount_multiplayer ────────────────────────────────────────────────────


class TestMountMultiplayer:
    """Verify mount_multiplayer registers the expected WebSocket route."""

    def test_registers_ws_world_route(self) -> None:
        mock_app = MagicMock()
        mock_app.websocket = MagicMock(return_value=lambda fn: fn)

        mount_multiplayer(mock_app)

        mock_app.websocket.assert_called_once_with("/ws/world")
