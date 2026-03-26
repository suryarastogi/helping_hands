"""Tests for the Yjs-based multiplayer synchronisation module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.server.multiplayer_yjs import (
    _clamp_float,
    _parse_awareness_state,
    _strip_control_chars,
    create_yjs_app,
    get_connected_players,
    get_multiplayer_stats,
    get_player_activity_summary,
    start_yjs_server,
    stop_yjs_server,
    validate_awareness_state,
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


class TestParseAwarenessState:
    """Tests for the ``_parse_awareness_state`` helper."""

    def test_returns_dict_as_is(self) -> None:
        state = {"player_id": "abc", "name": "Alice"}
        assert _parse_awareness_state(state) == state

    def test_parses_json_bytes(self) -> None:
        raw = b'{"player_id": "abc", "name": "Bob"}'
        result = _parse_awareness_state(raw)
        assert result == {"player_id": "abc", "name": "Bob"}

    def test_parses_json_string(self) -> None:
        raw = '{"player_id": "xyz"}'
        result = _parse_awareness_state(raw)
        assert result == {"player_id": "xyz"}

    def test_returns_none_for_invalid_json(self) -> None:
        assert _parse_awareness_state(b"not-json") is None

    def test_returns_none_for_non_string_non_dict(self) -> None:
        assert _parse_awareness_state(42) is None


class TestGetConnectedPlayers:
    """Tests for the ``get_connected_players`` function."""

    def test_returns_empty_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            result = get_connected_players()
            assert result == {"players": [], "count": 0}

    def test_returns_players_from_awareness_states(self) -> None:
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player_id": "p1",
                "name": "Alice",
                "color": "#e74c3c",
                "x": 25.0,
                "y": 50.0,
                "idle": False,
            },
            2: {
                "player_id": "p2",
                "name": "Bob",
                "color": "#3498db",
                "x": 75.0,
                "y": 30.0,
                "idle": True,
            },
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_room.clients = [MagicMock(), MagicMock()]
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result["count"] == 2
            assert len(result["players"]) == 2
            names = {p["name"] for p in result["players"]}
            assert names == {"Alice", "Bob"}

    def test_returns_empty_when_no_rooms(self) -> None:
        mock_server = MagicMock()
        mock_server.rooms = {}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result == {"players": [], "count": 0}

    def test_skips_rooms_without_awareness(self) -> None:
        mock_room = MagicMock()
        mock_room.awareness = None
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result == {"players": [], "count": 0}

    def test_handles_json_bytes_states(self) -> None:
        """Awareness states may arrive as JSON-encoded bytes."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: b'{"player_id": "p1", "name": "Charlie", "color": "#2ecc71", "x": 10, "y": 20, "idle": false}',
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result["count"] == 1
            assert result["players"][0]["name"] == "Charlie"

    def test_handles_exception_gracefully(self) -> None:
        mock_server = MagicMock()
        type(mock_server).rooms = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result == {"players": [], "count": 0}

    def test_uses_validated_state_for_position_clamping(self) -> None:
        """Positions outside [0, 100] should be clamped in the response."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player_id": "p1",
                "name": "Alice",
                "color": "#e74c3c",
                "x": -20.0,
                "y": 150.0,
                "idle": False,
            },
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            player = result["players"][0]
            assert player["x"] == 0.0
            assert player["y"] == 100.0


class TestValidateAwarenessState:
    """Tests for the ``validate_awareness_state`` function."""

    def test_valid_state_passes_through(self) -> None:
        state = {
            "player_id": "p1",
            "name": "Alice",
            "color": "#e74c3c",
            "x": 25.0,
            "y": 50.0,
            "idle": False,
            "direction": "up",
            "walking": True,
            "typing": False,
            "emote": "👋",
            "chat": "Hello!",
        }
        result = validate_awareness_state(state)
        assert result["player_id"] == "p1"
        assert result["name"] == "Alice"
        assert result["color"] == "#e74c3c"
        assert result["x"] == 25.0
        assert result["y"] == 50.0
        assert result["idle"] is False
        assert result["direction"] == "up"
        assert result["walking"] is True
        assert result["emote"] == "👋"
        assert result["chat"] == "Hello!"

    def test_clamps_x_below_zero(self) -> None:
        result = validate_awareness_state({"x": -10, "y": 50})
        assert result["x"] == 0.0

    def test_clamps_x_above_hundred(self) -> None:
        result = validate_awareness_state({"x": 200, "y": 50})
        assert result["x"] == 100.0

    def test_clamps_y_below_zero(self) -> None:
        result = validate_awareness_state({"x": 50, "y": -5})
        assert result["y"] == 0.0

    def test_clamps_y_above_hundred(self) -> None:
        result = validate_awareness_state({"x": 50, "y": 999})
        assert result["y"] == 100.0

    def test_defaults_non_numeric_position_to_midpoint(self) -> None:
        result = validate_awareness_state({"x": "not_a_number", "y": None})
        assert result["x"] == 50.0
        assert result["y"] == 50.0

    def test_truncates_long_name(self) -> None:
        long_name = "A" * 100
        result = validate_awareness_state({"name": long_name})
        assert len(result["name"]) == 50

    def test_strips_control_characters_from_name(self) -> None:
        result = validate_awareness_state({"name": "Ali\x00ce\x1f"})
        assert result["name"] == "Alice"

    def test_strips_control_characters_from_chat(self) -> None:
        result = validate_awareness_state({"chat": "Hello\x00World"})
        assert result["chat"] == "HelloWorld"

    def test_truncates_long_chat(self) -> None:
        long_chat = "x" * 200
        result = validate_awareness_state({"chat": long_chat})
        assert len(result["chat"]) == 120

    def test_truncates_long_emote(self) -> None:
        long_emote = "E" * 50
        result = validate_awareness_state({"emote": long_emote})
        assert len(result["emote"]) == 20

    def test_invalid_direction_defaults_to_down(self) -> None:
        result = validate_awareness_state({"direction": "sideways"})
        assert result["direction"] == "down"

    def test_null_emote_becomes_none(self) -> None:
        result = validate_awareness_state({"emote": None})
        assert result["emote"] is None

    def test_empty_chat_becomes_none(self) -> None:
        result = validate_awareness_state({"chat": ""})
        assert result["chat"] is None

    def test_coerces_numeric_player_id_to_string(self) -> None:
        result = validate_awareness_state({"player_id": 42})
        assert result["player_id"] == "42"

    def test_missing_fields_get_defaults(self) -> None:
        result = validate_awareness_state({})
        assert result["player_id"] == ""
        assert result["name"] == ""
        assert result["color"] == ""
        assert result["x"] == 50.0
        assert result["y"] == 50.0
        assert result["idle"] is False
        assert result["direction"] == "down"
        assert result["walking"] is False
        assert result["typing"] is False
        assert result["emote"] is None
        assert result["chat"] is None


class TestClampFloat:
    """Tests for the ``_clamp_float`` helper."""

    def test_clamps_below_range(self) -> None:
        assert _clamp_float(-5, 0.0, 100.0) == 0.0

    def test_clamps_above_range(self) -> None:
        assert _clamp_float(200, 0.0, 100.0) == 100.0

    def test_value_in_range_unchanged(self) -> None:
        assert _clamp_float(50, 0.0, 100.0) == 50.0

    def test_non_numeric_returns_midpoint(self) -> None:
        assert _clamp_float("abc", 0.0, 100.0) == 50.0

    def test_none_returns_midpoint(self) -> None:
        assert _clamp_float(None, 0.0, 100.0) == 50.0


class TestStripControlChars:
    """Tests for the ``_strip_control_chars`` helper."""

    def test_removes_null_bytes(self) -> None:
        assert _strip_control_chars("a\x00b") == "ab"

    def test_preserves_spaces(self) -> None:
        assert _strip_control_chars("hello world") == "hello world"

    def test_removes_tab_and_newline(self) -> None:
        assert _strip_control_chars("a\tb\nc") == "abc"

    def test_empty_string(self) -> None:
        assert _strip_control_chars("") == ""


class TestGetPlayerActivitySummary:
    """Tests for the ``get_player_activity_summary`` function."""

    def test_returns_empty_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            result = get_player_activity_summary()
            assert result == {"total": 0, "active": 0, "idle": 0, "players": []}

    def test_counts_active_and_idle_players(self) -> None:
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player_id": "p1",
                "name": "Alice",
                "color": "#e74c3c",
                "x": 25.0,
                "y": 50.0,
                "idle": False,
            },
            2: {
                "player_id": "p2",
                "name": "Bob",
                "color": "#3498db",
                "x": 75.0,
                "y": 30.0,
                "idle": True,
            },
            3: {
                "player_id": "p3",
                "name": "Charlie",
                "color": "#2ecc71",
                "x": 50.0,
                "y": 50.0,
                "idle": False,
            },
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_player_activity_summary()
            assert result["total"] == 3
            assert result["active"] == 2
            assert result["idle"] == 1
            assert len(result["players"]) == 3

    def test_validates_player_positions(self) -> None:
        """Returned players should have validated/clamped positions."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player_id": "p1",
                "name": "Hacker",
                "color": "#000",
                "x": -999,
                "y": 9999,
                "idle": False,
            },
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_player_activity_summary()
            player = result["players"][0]
            assert player["x"] == 0.0
            assert player["y"] == 100.0

    def test_handles_exception_gracefully(self) -> None:
        mock_server = MagicMock()
        type(mock_server).rooms = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_player_activity_summary()
            assert result == {"total": 0, "active": 0, "idle": 0, "players": []}
