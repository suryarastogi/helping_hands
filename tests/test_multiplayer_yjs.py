"""Tests for the Yjs-based multiplayer synchronisation module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.server.multiplayer_yjs import (
    create_yjs_app,
    get_multiplayer_stats,
    start_yjs_server,
    stop_yjs_server,
)


class TestCreateYjsApp:
    """Tests for the ``create_yjs_app`` factory."""

    def test_returns_none_when_pycrdt_unavailable(self) -> None:
        with (
            patch("helping_hands.server.multiplayer_yjs._HAS_PYCRDT", False),
            patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None),
            patch("helping_hands.server.multiplayer_yjs.yjs_asgi_app", None),
        ):
            result = create_yjs_app()
            assert result is None

    def test_returns_asgi_app_when_pycrdt_available(self) -> None:
        mock_ws_server = MagicMock()
        mock_asgi = MagicMock()

        with (
            patch("helping_hands.server.multiplayer_yjs._HAS_PYCRDT", True),
            patch(
                "helping_hands.server.multiplayer_yjs.WebsocketServer",
                create=True,
                return_value=mock_ws_server,
            ),
            patch(
                "helping_hands.server.multiplayer_yjs.ASGIServer",
                create=True,
                return_value=mock_asgi,
            ),
        ):
            result = create_yjs_app()
            assert result is mock_asgi


class TestYjsServerLifecycle:
    """Tests for start/stop lifecycle functions."""

    @pytest.mark.asyncio
    async def test_start_calls_server_start(self) -> None:
        mock_server = AsyncMock()
        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            await start_yjs_server()
            mock_server.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_noop_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            await start_yjs_server()  # Should not raise.

    @pytest.mark.asyncio
    async def test_stop_calls_server_stop(self) -> None:
        mock_server = AsyncMock()
        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            await stop_yjs_server()
            mock_server.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_noop_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            await stop_yjs_server()  # Should not raise.


class TestYjsAppGlobals:
    """Tests that create_yjs_app sets module-level singletons correctly."""

    def test_create_sets_module_globals(self) -> None:
        """create_yjs_app populates yjs_websocket_server and yjs_asgi_app globals."""
        mock_ws_server = MagicMock()
        mock_asgi = MagicMock()

        with (
            patch("helping_hands.server.multiplayer_yjs._HAS_PYCRDT", True),
            patch(
                "helping_hands.server.multiplayer_yjs.WebsocketServer",
                create=True,
                return_value=mock_ws_server,
            ),
            patch(
                "helping_hands.server.multiplayer_yjs.ASGIServer",
                create=True,
                return_value=mock_asgi,
            ),
        ):
            import helping_hands.server.multiplayer_yjs as mod

            result = create_yjs_app()
            assert result is mock_asgi
            assert mod.yjs_websocket_server is mock_ws_server
            assert mod.yjs_asgi_app is mock_asgi

    def test_create_returns_none_leaves_globals_unchanged(self) -> None:
        """When pycrdt is unavailable, globals remain None."""
        with (
            patch("helping_hands.server.multiplayer_yjs._HAS_PYCRDT", False),
            patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None),
            patch("helping_hands.server.multiplayer_yjs.yjs_asgi_app", None),
        ):
            import helping_hands.server.multiplayer_yjs as mod

            result = create_yjs_app()
            assert result is None
            assert mod.yjs_websocket_server is None
            assert mod.yjs_asgi_app is None


class TestGetMultiplayerStats:
    """Tests for the ``get_multiplayer_stats`` function."""

    def test_returns_unavailable_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            result = get_multiplayer_stats()
            assert result == {"available": False, "rooms": 0, "connections": 0}

    def test_returns_stats_with_rooms_and_clients(self) -> None:
        mock_room = MagicMock()
        mock_room.clients = [MagicMock(), MagicMock(), MagicMock()]
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_multiplayer_stats()
            assert result == {"available": True, "rooms": 1, "connections": 3}

    def test_returns_zero_counts_with_empty_rooms(self) -> None:
        mock_server = MagicMock()
        mock_server.rooms = {}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_multiplayer_stats()
            assert result == {"available": True, "rooms": 0, "connections": 0}

    def test_handles_multiple_rooms(self) -> None:
        room_a = MagicMock()
        room_a.clients = [MagicMock(), MagicMock()]
        room_b = MagicMock()
        room_b.clients = [MagicMock()]
        mock_server = MagicMock()
        mock_server.rooms = {"room-a": room_a, "room-b": room_b}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_multiplayer_stats()
            assert result == {"available": True, "rooms": 2, "connections": 3}

    def test_handles_exception_gracefully(self) -> None:
        mock_server = MagicMock()
        mock_server.rooms = property(lambda self: (_ for _ in ()).throw(RuntimeError))
        # Make rooms access raise an exception.
        type(mock_server).rooms = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_multiplayer_stats()
            assert result == {"available": True, "rooms": 0, "connections": 0}
