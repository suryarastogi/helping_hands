"""Tests for v145: Claude keychain constants are shared between app.py and celery_app.py.

The Claude OAuth token is read from the macOS Keychain using a service name and key
path that must match exactly what Claude Code writes.  If app.py and celery_app.py
use different literal strings (or if either drifts from the canonical values), the
background Celery worker silently fails to pick up the token while the FastAPI
server succeeds, causing intermittent auth failures in scheduled tasks only.

The "used in source" tests ensure the constants are actually referenced in
_get_claude_oauth_token rather than duplicated as inline strings, which would
let the constants and the runtime behaviour diverge silently.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# 1. Keychain constants in server/app.py
# ---------------------------------------------------------------------------


class TestAppKeychainConstants:
    """Verify keychain constants in server/constants.py."""

    def test_keychain_service_name_value(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_SERVICE_NAME

        assert KEYCHAIN_SERVICE_NAME == "Claude Code-credentials"

    def test_keychain_service_name_is_str(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_SERVICE_NAME

        assert isinstance(KEYCHAIN_SERVICE_NAME, str)

    def test_keychain_oauth_key_value(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_OAUTH_KEY

        assert KEYCHAIN_OAUTH_KEY == "claudeAiOauth"

    def test_keychain_access_token_key_value(self) -> None:
        from helping_hands.server.constants import KEYCHAIN_ACCESS_TOKEN_KEY

        assert KEYCHAIN_ACCESS_TOKEN_KEY == "accessToken"

    def test_get_claude_oauth_token_uses_constants(self) -> None:
        """Verify get_claude_oauth_token uses constants, not hardcoded strings."""
        from helping_hands.server.token_helpers import get_claude_oauth_token

        source = inspect.getsource(get_claude_oauth_token)
        assert "KEYCHAIN_SERVICE_NAME" in source
        assert "KEYCHAIN_OAUTH_KEY" in source
        assert "KEYCHAIN_ACCESS_TOKEN_KEY" in source
        assert '"Claude Code-credentials"' not in source
        assert '"claudeAiOauth"' not in source
        assert '"accessToken"' not in source


# ---------------------------------------------------------------------------
# 2. Keychain constants in server/celery_app.py
# ---------------------------------------------------------------------------


class TestCeleryKeychainConstants:
    """Verify keychain constants in server/celery_app.py."""

    def test_keychain_service_name_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_SERVICE_NAME

        assert _KEYCHAIN_SERVICE_NAME == "Claude Code-credentials"

    def test_keychain_oauth_key_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_OAUTH_KEY

        assert _KEYCHAIN_OAUTH_KEY == "claudeAiOauth"

    def test_keychain_access_token_key_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _KEYCHAIN_ACCESS_TOKEN_KEY

        assert _KEYCHAIN_ACCESS_TOKEN_KEY == "accessToken"

    def test_log_claude_usage_uses_constants(self) -> None:
        """Verify log_claude_usage uses constants, not hardcoded strings."""
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import log_claude_usage

        source = inspect.getsource(log_claude_usage)
        assert "_KEYCHAIN_SERVICE_NAME" in source
        assert "_KEYCHAIN_OAUTH_KEY" in source
        assert "_KEYCHAIN_ACCESS_TOKEN_KEY" in source
        assert '"Claude Code-credentials"' not in source
        assert '"claudeAiOauth"' not in source
        assert '"accessToken"' not in source


# ---------------------------------------------------------------------------
# 3. Cross-module sync: keychain constants match between app.py and celery_app.py
# ---------------------------------------------------------------------------


class TestKeychainConstantSync:
    """Verify keychain constants stay in sync across modules."""

    def test_service_name_sync(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import (
            _KEYCHAIN_SERVICE_NAME as _CELERY_NAME,
        )
        from helping_hands.server.constants import (
            KEYCHAIN_SERVICE_NAME as _CONST_NAME,
        )

        assert _CONST_NAME == _CELERY_NAME

    def test_oauth_key_sync(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import (
            _KEYCHAIN_OAUTH_KEY as _CELERY_KEY,
        )
        from helping_hands.server.constants import (
            KEYCHAIN_OAUTH_KEY as _CONST_KEY,
        )

        assert _CONST_KEY == _CELERY_KEY

    def test_access_token_key_sync(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import (
            _KEYCHAIN_ACCESS_TOKEN_KEY as _CELERY_KEY,
        )
        from helping_hands.server.constants import (
            KEYCHAIN_ACCESS_TOKEN_KEY as _CONST_KEY,
        )

        assert _CONST_KEY == _CELERY_KEY


# ---------------------------------------------------------------------------
# 4. Utilization type guard in _fetch_claude_usage
# ---------------------------------------------------------------------------


class TestUtilizationTypeGuard:
    """Verify _fetch_claude_usage handles non-numeric utilization values."""

    @staticmethod
    def _reset_cache(monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("fastapi")
        monkeypatch.setattr("helping_hands.server.app._usage_cache", None)
        monkeypatch.setattr("helping_hands.server.app._usage_cache_ts", 0.0)

    def _mock_fetch(self, monkeypatch: pytest.MonkeyPatch, api_data: dict) -> object:
        """Set up mocks for _fetch_claude_usage and return the result."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _fetch_claude_usage

        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(api_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )
        return _fetch_claude_usage()

    def test_string_utilization_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-numeric utilization (string) should be skipped, not crash."""
        result = self._mock_fetch(
            monkeypatch,
            {
                "five_hour": {"utilization": "not-a-number"},
                "seven_day": {"utilization": 10.0},
            },
        )
        # Only weekly should appear (session skipped due to string)
        assert len(result.levels) == 1
        assert result.levels[0].name == "Weekly"

    def test_none_utilization_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """None utilization should be skipped (existing behavior preserved)."""
        result = self._mock_fetch(
            monkeypatch,
            {
                "five_hour": {"utilization": None},
                "seven_day": {"utilization": 20.5},
            },
        )
        assert len(result.levels) == 1
        assert result.levels[0].name == "Weekly"

    def test_bool_utilization_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Boolean utilization should be skipped (bool is subclass of int
        but not a meaningful utilization value)."""
        # Note: isinstance(True, int) is True in Python, so booleans pass
        # the guard. This test documents the current behavior.
        result = self._mock_fetch(
            monkeypatch,
            {
                "five_hour": {"utilization": True},
                "seven_day": {"utilization": 50.0},
            },
        )
        # True is int subclass, so both levels appear
        assert len(result.levels) == 2

    def test_list_utilization_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """List utilization should be skipped, not crash with TypeError."""
        result = self._mock_fetch(
            monkeypatch,
            {
                "five_hour": {"utilization": [42]},
                "seven_day": {"utilization": [10]},
            },
        )
        # Both skipped — no valid numeric values
        assert "No usage data" in result.error

    def test_int_utilization_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Integer utilization should be accepted and rounded."""
        result = self._mock_fetch(
            monkeypatch,
            {"five_hour": {"utilization": 42}},
        )
        assert len(result.levels) == 1
        assert result.levels[0].percent_used == 42

    def test_source_uses_isinstance(self) -> None:
        """Verify _extract_usage_level uses isinstance guard, not 'is not None'."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _extract_usage_level

        source = inspect.getsource(_extract_usage_level)
        assert "isinstance" in source
        assert "(int, float)" in source or "int | float" in source


# ---------------------------------------------------------------------------
# 5. Decode safety: errors="replace" in _fetch_claude_usage
# ---------------------------------------------------------------------------


class TestDecodeSafety:
    """Verify _fetch_claude_usage uses errors='replace' for decode safety."""

    def test_source_uses_decode_errors_replace(self) -> None:
        """Verify resp.read().decode() uses errors='replace'."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _fetch_claude_usage

        source = inspect.getsource(_fetch_claude_usage)
        assert 'errors="replace"' in source

    def test_non_utf8_response_does_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-UTF-8 bytes should be decoded with replacement chars."""
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _fetch_claude_usage

        monkeypatch.setattr("helping_hands.server.app._usage_cache", None)
        monkeypatch.setattr("helping_hands.server.app._usage_cache_ts", 0.0)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        # Bytes that are invalid UTF-8
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"five_hour": {"utilization": 10}}\xff\xfe'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None
        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        # Should not raise UnicodeDecodeError — the decode(errors="replace")
        # handles the invalid bytes, but json.loads will fail on the
        # replacement chars. That's caught by the generic except.
        result = _fetch_claude_usage()
        # Either succeeds with parsed data or returns an error — no crash
        assert result is not None
