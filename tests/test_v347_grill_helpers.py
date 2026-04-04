"""Tests for server.grill Redis helper functions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock


class TestSetState:
    """Tests for _set_state Redis helper."""

    def test_writes_json_with_ttl(self) -> None:
        from helping_hands.server.grill import _set_state

        r = MagicMock()
        state = {"phase": "chat", "turns": 3}
        _set_state(r, "sess-1", state)
        r.set.assert_called_once()
        args, kwargs = r.set.call_args
        assert args[0] == "grill:sess-1:state"
        assert json.loads(args[1]) == state
        assert kwargs.get("ex") or args[2]  # TTL is set

    def test_key_includes_session_id(self) -> None:
        from helping_hands.server.grill import _set_state

        r = MagicMock()
        _set_state(r, "abc-123", {"phase": "form"})
        key = r.set.call_args[0][0]
        assert key == "grill:abc-123:state"

    def test_empty_state_dict(self) -> None:
        from helping_hands.server.grill import _set_state

        r = MagicMock()
        _set_state(r, "sess-1", {})
        stored = json.loads(r.set.call_args[0][1])
        assert stored == {}


class TestGetState:
    """Tests for _get_state Redis helper."""

    def test_returns_parsed_state(self) -> None:
        from helping_hands.server.grill import _get_state

        r = MagicMock()
        state = {"phase": "chat", "turns": 5}
        r.get.return_value = json.dumps(state)
        result = _get_state(r, "sess-1")
        assert result == state
        r.get.assert_called_once_with("grill:sess-1:state")

    def test_returns_none_for_missing_key(self) -> None:
        from helping_hands.server.grill import _get_state

        r = MagicMock()
        r.get.return_value = None
        result = _get_state(r, "nonexistent")
        assert result is None

    def test_key_includes_session_id(self) -> None:
        from helping_hands.server.grill import _get_state

        r = MagicMock()
        r.get.return_value = None
        _get_state(r, "xyz-789")
        r.get.assert_called_once_with("grill:xyz-789:state")


class TestPushAiMsg:
    """Tests for _push_ai_msg Redis helper."""

    def test_pushes_json_message_to_queue(self) -> None:
        from helping_hands.server.grill import _push_ai_msg

        r = MagicMock()
        _push_ai_msg(r, "sess-1", "assistant", "Hello!")
        r.rpush.assert_called_once()
        key, raw = r.rpush.call_args[0]
        assert key == "grill:sess-1:ai_msgs"
        msg = json.loads(raw)
        assert msg["role"] == "assistant"
        assert msg["content"] == "Hello!"
        assert msg["type"] == "message"
        assert "id" in msg
        assert "timestamp" in msg

    def test_custom_msg_type(self) -> None:
        from helping_hands.server.grill import _push_ai_msg

        r = MagicMock()
        _push_ai_msg(r, "sess-1", "assistant", "Done", msg_type="plan")
        msg = json.loads(r.rpush.call_args[0][1])
        assert msg["type"] == "plan"

    def test_sets_expire_on_queue(self) -> None:
        from helping_hands.server.grill import _push_ai_msg

        r = MagicMock()
        _push_ai_msg(r, "sess-1", "assistant", "Hi")
        r.expire.assert_called_once()
        key, ttl = r.expire.call_args[0]
        assert key == "grill:sess-1:ai_msgs"
        assert ttl > 0

    def test_message_id_is_uuid_format(self) -> None:
        from helping_hands.server.grill import _push_ai_msg

        r = MagicMock()
        _push_ai_msg(r, "sess-1", "assistant", "msg")
        msg = json.loads(r.rpush.call_args[0][1])
        # UUID4 format: 8-4-4-4-12 hex chars
        assert len(msg["id"].split("-")) == 5


class TestPopUserMsg:
    """Tests for _pop_user_msg Redis helper."""

    def test_returns_parsed_message(self) -> None:
        from helping_hands.server.grill import _pop_user_msg

        r = MagicMock()
        user_msg = {"role": "user", "content": "Tell me more"}
        r.lpop.return_value = json.dumps(user_msg)
        result = _pop_user_msg(r, "sess-1")
        assert result == user_msg
        r.lpop.assert_called_once_with("grill:sess-1:user_msgs")

    def test_returns_none_for_empty_queue(self) -> None:
        from helping_hands.server.grill import _pop_user_msg

        r = MagicMock()
        r.lpop.return_value = None
        result = _pop_user_msg(r, "sess-1")
        assert result is None

    def test_key_includes_session_id(self) -> None:
        from helping_hands.server.grill import _pop_user_msg

        r = MagicMock()
        r.lpop.return_value = None
        _pop_user_msg(r, "my-session")
        r.lpop.assert_called_once_with("grill:my-session:user_msgs")
