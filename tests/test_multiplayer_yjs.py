"""Tests for the Yjs-based multiplayer synchronisation module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.server.multiplayer_yjs import (
    create_yjs_app,
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
