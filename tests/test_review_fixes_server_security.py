"""Tests for the server-layer security/reliability fixes from the code review.

Covers:
* constant-time token-hash comparison helpers (``_hashes_match`` / ``_tokens_match``),
* stricter path-parameter validation (charset + length),
* the per-session multiplayer-grill turn lock,
* the shared Redis connection pool,
* ``TemplateResponse`` no longer exposing ``owner_token_hash``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from helping_hands.server.app import (
    TemplateResponse,
    _hash_token,
    _hashes_match,
    _mgrill_turn_lock,
    _redis_pool,
    _tokens_match,
    _validate_path_param,
)


class TestConstantTimeComparison:
    def test_hashes_match_true_for_correct_token(self) -> None:
        token = "ghp_example"
        assert _hashes_match(token, _hash_token(token)) is True

    def test_hashes_match_false_for_wrong_token(self) -> None:
        assert _hashes_match("wrong", _hash_token("right")) is False

    def test_hashes_match_false_when_hash_missing(self) -> None:
        assert _hashes_match("anything", None) is False
        assert _hashes_match("anything", "") is False

    def test_tokens_match_true_for_equal(self) -> None:
        assert _tokens_match("admin-tok", "admin-tok") is True

    def test_tokens_match_false_for_unequal(self) -> None:
        assert _tokens_match("a", "b") is False

    def test_tokens_match_false_when_other_missing(self) -> None:
        assert _tokens_match("a", None) is False
        assert _tokens_match("a", "") is False


class TestValidatePathParam:
    def test_accepts_uuid_like_id(self) -> None:
        val = "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
        assert _validate_path_param(val, "session_id") == val

    def test_accepts_prefixed_hex_id(self) -> None:
        assert _validate_path_param("sched_abc123", "schedule_id") == "sched_abc123"

    def test_rejects_colon_injection(self) -> None:
        with pytest.raises(ValueError, match="session_id"):
            _validate_path_param("x:malicious:state", "session_id")

    def test_rejects_whitespace_and_slashes(self) -> None:
        with pytest.raises(ValueError):
            _validate_path_param("a/b", "session_id")

    def test_rejects_overlong_value(self) -> None:
        with pytest.raises(ValueError, match="maximum length"):
            _validate_path_param("a" * 129, "session_id")

    def test_still_strips_surrounding_whitespace(self) -> None:
        assert _validate_path_param("  abc  ", "task_id") == "abc"


class TestMgrillTurnLock:
    def test_acquires_and_releases(self) -> None:
        r = MagicMock()
        r.set.return_value = True  # lock acquired
        with _mgrill_turn_lock(r, "sess-1"):
            pass
        r.set.assert_called_once()
        # nx/ex flags present so it is a real lock, not a plain set.
        _, kwargs = r.set.call_args
        assert kwargs.get("nx") is True
        assert kwargs.get("ex")
        r.delete.assert_called_once_with("mgrill:sess-1:turn_lock")

    def test_second_holder_gets_409(self) -> None:
        from fastapi import HTTPException

        r = MagicMock()
        r.set.return_value = False  # already held
        with pytest.raises(HTTPException) as exc:  # noqa: SIM117
            with _mgrill_turn_lock(r, "sess-1"):
                pass
        assert exc.value.status_code == 409
        # Loser must not delete the incumbent's lock.
        r.delete.assert_not_called()

    def test_lock_released_on_exception(self) -> None:
        r = MagicMock()
        r.set.return_value = True
        with pytest.raises(RuntimeError):  # noqa: SIM117
            with _mgrill_turn_lock(r, "sess-1"):
                raise RuntimeError("boom")
        r.delete.assert_called_once_with("mgrill:sess-1:turn_lock")


class TestRedisPoolShared:
    def test_pool_is_cached_per_url(self) -> None:
        redis = pytest.importorskip("redis")
        pool_a = _redis_pool("redis://localhost:6379/0")
        pool_b = _redis_pool("redis://localhost:6379/0")
        pool_other = _redis_pool("redis://localhost:6379/1")
        assert pool_a is pool_b
        assert pool_a is not pool_other
        assert isinstance(pool_a, redis.ConnectionPool)


class TestTemplateResponseNoHashLeak:
    def test_owner_token_hash_not_in_schema(self) -> None:
        assert "owner_token_hash" not in TemplateResponse.model_fields
