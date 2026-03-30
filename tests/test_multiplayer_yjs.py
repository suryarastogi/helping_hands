"""Tests for the Yjs-based multiplayer synchronisation module.

Protects the optional pycrdt-websocket integration used by the Hand World
feature.  Key invariants: create_yjs_app returns None when pycrdt-websocket is
not installed (allowing the server to start without it) and sets the
yjs_websocket_server/yjs_asgi_app module-level singletons when it is;
start_yjs_server and stop_yjs_server are no-ops when the server is None (safe
during startup/shutdown regardless of whether the feature is enabled);
get_multiplayer_stats reports zero counts when the server is absent and
aggregates clients across all rooms when it is, swallowing any exception from
the WebsocketServer to avoid crashing a stats endpoint.

If create_yjs_app raises instead of returning None when pycrdt-websocket is
absent, the entire FastAPI server fails to start in any environment that lacks
the optional dependency.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.server.multiplayer_yjs import (
    _clamp_float,
    _extract_player_state,
    _parse_awareness_state,
    _strip_control_chars,
    create_yjs_app,
    get_connected_players,
    get_decoration_state,
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
    async def test_start_calls_server_aenter(self) -> None:
        mock_server = AsyncMock()
        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            await start_yjs_server()
            mock_server.__aenter__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_noop_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            await start_yjs_server()  # Should not raise.

    @pytest.mark.asyncio
    async def test_stop_calls_server_aexit(self) -> None:
        mock_server = AsyncMock()
        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            await stop_yjs_server()
            mock_server.__aexit__.assert_awaited_once_with(None, None, None)

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

    def test_handles_bytes_with_invalid_utf8(self) -> None:
        """Invalid UTF-8 sequences should be replaced, not crash."""
        raw = b'{"name": "test\xff\xfe"}'
        result = _parse_awareness_state(raw)
        assert result is not None
        assert "name" in result

    def test_handles_bytearray(self) -> None:
        raw = bytearray(b'{"player_id": "ba1"}')
        result = _parse_awareness_state(raw)
        assert result == {"player_id": "ba1"}


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
                "player": {
                    "player_id": "p1",
                    "name": "Alice",
                    "color": "#e74c3c",
                    "x": 25.0,
                    "y": 50.0,
                    "idle": False,
                },
            },
            2: {
                "player": {
                    "player_id": "p2",
                    "name": "Bob",
                    "color": "#3498db",
                    "x": 75.0,
                    "y": 30.0,
                    "idle": True,
                },
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
        """Awareness states may arrive as JSON-encoded bytes with nested player."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: b'{"player": {"player_id": "p1", "name": "Charlie", "color": "#2ecc71", "x": 10, "y": 20, "idle": false}}',
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

    def test_skips_states_without_player_data(self) -> None:
        """States without a player sub-dict or flat player_id are skipped."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {"cursor": {"x": 10, "y": 10}},  # No player data
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            assert result == {"players": [], "count": 0}

    def test_handles_flat_legacy_states(self) -> None:
        """Flat awareness states (no player sub-dict) still work."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player_id": "p1",
                "name": "Legacy",
                "color": "#e74c3c",
                "x": 25.0,
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
            result = get_connected_players()
            assert result["count"] == 1
            assert result["players"][0]["name"] == "Legacy"

    def test_handles_partial_iteration_failure(self) -> None:
        """If one awareness state entry is malformed, others still parse."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player": {
                    "player_id": "p1",
                    "name": "GoodPlayer",
                    "color": "#e74c3c",
                    "x": 25.0,
                    "y": 50.0,
                    "idle": False,
                },
            },
            # Second entry is a non-parseable type
            2: 12345,
        }
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_connected_players()
            # The good player should still be returned
            assert result["count"] == 1
            assert result["players"][0]["name"] == "GoodPlayer"

    def test_uses_validated_state_for_position_clamping(self) -> None:
        """Positions outside [0, 100] should be clamped in the response."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {
                "player": {
                    "player_id": "p1",
                    "name": "Alice",
                    "color": "#e74c3c",
                    "x": -20.0,
                    "y": 150.0,
                    "idle": False,
                },
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

    def test_positive_infinity_clamps_to_hi(self) -> None:
        assert _clamp_float(float("inf"), 0.0, 100.0) == 100.0

    def test_negative_infinity_clamps_to_lo(self) -> None:
        assert _clamp_float(float("-inf"), 0.0, 100.0) == 0.0

    def test_nan_returns_midpoint(self) -> None:
        assert _clamp_float(float("nan"), 0.0, 100.0) == 50.0

    def test_numeric_string_is_coerced(self) -> None:
        assert _clamp_float("50.5", 0.0, 100.0) == 50.5


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

    def test_preserves_emoji(self) -> None:
        assert _strip_control_chars("hello 🎉 world") == "hello 🎉 world"

    def test_strips_control_chars_around_emoji(self) -> None:
        assert _strip_control_chars("\x00🌸\x1f") == "🌸"


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
                "player": {
                    "player_id": "p1",
                    "name": "Alice",
                    "color": "#e74c3c",
                    "x": 25.0,
                    "y": 50.0,
                    "idle": False,
                },
            },
            2: {
                "player": {
                    "player_id": "p2",
                    "name": "Bob",
                    "color": "#3498db",
                    "x": 75.0,
                    "y": 30.0,
                    "idle": True,
                },
            },
            3: {
                "player": {
                    "player_id": "p3",
                    "name": "Charlie",
                    "color": "#2ecc71",
                    "x": 50.0,
                    "y": 50.0,
                    "idle": False,
                },
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
                "player": {
                    "player_id": "p1",
                    "name": "Hacker",
                    "color": "#000",
                    "x": -999,
                    "y": 9999,
                    "idle": False,
                },
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

    def test_skips_room_with_awareness_none(self) -> None:
        """A room whose awareness is None should be skipped gracefully."""
        mock_room = MagicMock()
        mock_room.awareness = None

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_player_activity_summary()
            assert result == {"total": 0, "active": 0, "idle": 0, "players": []}

    def test_skips_unparseable_awareness_state(self) -> None:
        """When _parse_awareness_state returns None, the state is skipped."""
        mock_awareness = MagicMock()
        # bytes value that can't be parsed — _parse_awareness_state returns None
        mock_awareness.states = {1: b"invalid-msgpack-data"}
        mock_room = MagicMock()
        mock_room.awareness = mock_awareness
        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_player_activity_summary()
            assert result == {"total": 0, "active": 0, "idle": 0, "players": []}

    def test_skips_states_without_player_data(self) -> None:
        """States without player data are ignored in activity summary."""
        mock_awareness = MagicMock()
        mock_awareness.states = {
            1: {"cursor": {"x": 10, "y": 10}},
            2: {
                "player": {
                    "player_id": "p1",
                    "name": "Alice",
                    "color": "#e74c3c",
                    "x": 50.0,
                    "y": 50.0,
                    "idle": False,
                },
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
            assert result["total"] == 1
            assert result["active"] == 1

    def test_skips_unparseable_raw_state(self) -> None:
        """Raw states that ``_parse_awareness_state`` returns None for are skipped."""
        mock_awareness = MagicMock()
        # _parse_awareness_state returns None for non-dict, non-bytes data
        mock_awareness.states = {
            1: None,  # unparseable
            2: {
                "player": {
                    "player_id": "p1",
                    "name": "Alice",
                    "color": "#e74c3c",
                    "x": 50.0,
                    "y": 50.0,
                    "idle": False,
                },
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
            # Only the valid player should be counted
            assert result["total"] == 1
            assert result["active"] == 1


class TestExtractPlayerState:
    """Tests for the ``_extract_player_state`` helper."""

    def test_extracts_nested_player_dict(self) -> None:
        state = {"player": {"player_id": "p1", "name": "Alice", "x": 50, "y": 50}}
        result = _extract_player_state(state)
        assert result == {"player_id": "p1", "name": "Alice", "x": 50, "y": 50}

    def test_returns_flat_state_with_player_id(self) -> None:
        state = {"player_id": "p1", "name": "Alice", "x": 50, "y": 50}
        result = _extract_player_state(state)
        assert result is state

    def test_returns_flat_state_with_name_only(self) -> None:
        state = {"name": "Alice", "x": 50, "y": 50}
        result = _extract_player_state(state)
        assert result is state

    def test_returns_none_for_unrelated_state(self) -> None:
        state = {"cursor": {"x": 10, "y": 10}}
        result = _extract_player_state(state)
        assert result is None

    def test_returns_none_for_empty_state(self) -> None:
        result = _extract_player_state({})
        assert result is None

    def test_ignores_non_dict_player_field(self) -> None:
        state = {"player": "not a dict"}
        result = _extract_player_state(state)
        assert result is None

    def test_empty_player_dict_returned(self) -> None:
        """An empty nested player dict is returned (validate_awareness_state fills defaults)."""
        state = {"player": {}}
        result = _extract_player_state(state)
        assert result == {}

    def test_player_list_is_ignored(self) -> None:
        """A list value for player key should be treated as non-dict."""
        state = {"player": [1, 2, 3]}
        result = _extract_player_state(state)
        assert result is None


class TestGetDecorationState:
    """Tests for the ``get_decoration_state`` endpoint helper."""

    def test_returns_empty_when_server_is_none(self) -> None:
        with patch("helping_hands.server.multiplayer_yjs.yjs_websocket_server", None):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_returns_empty_when_no_rooms(self) -> None:
        mock_server = MagicMock()
        mock_server.rooms = {}
        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_returns_decorations_from_ydoc(self) -> None:
        """Decorations stored in Y.Map should be returned with validated fields."""
        mock_deco_map = MagicMock()
        mock_deco_map.__iter__ = MagicMock(return_value=iter(["d1", "d2"]))
        mock_deco_map.__getitem__ = MagicMock(
            side_effect=lambda k: {
                "d1": {
                    "emoji": "\U0001f338",
                    "x": 30.0,
                    "y": 40.0,
                    "placedBy": "Alice",
                    "color": "#e11d48",
                    "placedAt": 1000,
                },
                "d2": {
                    "emoji": "\u2b50",
                    "x": 60.0,
                    "y": 70.0,
                    "placedBy": "Bob",
                    "color": "#2563eb",
                    "placedAt": 2000,
                },
            }[k]
        )

        mock_ydoc = MagicMock()
        mock_ydoc.get.return_value = mock_deco_map

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result["count"] == 2
            decos = result["decorations"]
            assert len(decos) == 2
            assert decos[0]["emoji"] == "\U0001f338"
            assert decos[0]["placedBy"] == "Alice"
            assert decos[1]["emoji"] == "\u2b50"
            assert decos[1]["placedAt"] == 2000

    def test_clamps_decoration_positions(self) -> None:
        """Out-of-range decoration positions should be clamped to [0, 100]."""
        mock_deco_map = MagicMock()
        mock_deco_map.__iter__ = MagicMock(return_value=iter(["d1"]))
        mock_deco_map.__getitem__ = MagicMock(
            return_value={
                "emoji": "\U0001f525",
                "x": -10.0,
                "y": 200.0,
                "placedBy": "Eve",
                "color": "#fff",
                "placedAt": 500,
            }
        )

        mock_ydoc = MagicMock()
        mock_ydoc.get.return_value = mock_deco_map

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result["count"] == 1
            deco = result["decorations"][0]
            assert deco["x"] == 0.0
            assert deco["y"] == 100.0

    def test_skips_entries_without_emoji(self) -> None:
        """Map entries without an emoji field should be skipped."""
        mock_deco_map = MagicMock()
        mock_deco_map.__iter__ = MagicMock(return_value=iter(["d1", "d2"]))
        mock_deco_map.__getitem__ = MagicMock(
            side_effect=lambda k: {
                "d1": {"x": 50, "y": 50, "placedBy": "Alice"},  # no emoji
                "d2": {
                    "emoji": "\U0001f48e",
                    "x": 10,
                    "y": 20,
                    "placedBy": "Bob",
                    "color": "",
                    "placedAt": 100,
                },
            }[k]
        )

        mock_ydoc = MagicMock()
        mock_ydoc.get.return_value = mock_deco_map

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result["count"] == 1
            assert result["decorations"][0]["emoji"] == "\U0001f48e"

    def test_skips_room_with_ydoc_none(self) -> None:
        """A room whose ydoc is None should be skipped gracefully."""
        mock_room = MagicMock()
        mock_room.ydoc = None

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_skips_room_when_ydoc_get_raises(self) -> None:
        """When ydoc.get raises, the room is skipped gracefully."""
        mock_ydoc = MagicMock()
        mock_ydoc.get.side_effect = RuntimeError("corrupted ydoc")

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_skips_room_when_deco_map_is_none(self) -> None:
        """When ydoc.get returns None, the room is skipped."""
        mock_ydoc = MagicMock()
        mock_ydoc.get.return_value = None

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_handles_exception_gracefully(self) -> None:
        """Exceptions reading room state should return empty result."""
        mock_server = MagicMock()
        mock_server.rooms = MagicMock(side_effect=RuntimeError("boom"))
        # rooms is a property-like attribute that raises on access
        type(mock_server).rooms = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_skips_room_where_deco_map_get_raises(self) -> None:
        """When ``ydoc.get("decorations", ...)`` raises, the room is skipped."""
        mock_ydoc = MagicMock()
        mock_ydoc.get.side_effect = TypeError("unsupported type")

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}

    def test_skips_room_where_deco_map_is_none(self) -> None:
        """When ``ydoc.get()`` returns None, the room is skipped."""
        mock_ydoc = MagicMock()
        mock_ydoc.get.return_value = None

        mock_room = MagicMock()
        mock_room.ydoc = mock_ydoc

        mock_server = MagicMock()
        mock_server.rooms = {"hand-world": mock_room}

        with patch(
            "helping_hands.server.multiplayer_yjs.yjs_websocket_server", mock_server
        ):
            result = get_decoration_state()
            assert result == {"decorations": [], "count": 0}
