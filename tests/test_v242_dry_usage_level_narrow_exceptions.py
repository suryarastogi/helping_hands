"""Protect Claude usage-level parsing robustness and exception specificity in the OAuth/usage fetch path.

_extract_usage_level parses the nested utilization object from the Anthropic
usage API. If it stops tolerating missing keys, None values, or non-numeric
types, the usage dashboard raises on every partial API response and silently
drops usage records -- operators lose visibility into rate-limit headroom.

_get_claude_oauth_token and _fetch_claude_usage must catch only OS/network/JSON
errors so that programming bugs (TypeError, AttributeError) propagate
immediately rather than hiding behind a generic "usage fetch failed" log line.
"""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    ClaudeUsageLevel,
    _extract_usage_level,
    _fetch_claude_usage,
    _get_claude_oauth_token,
)

# ---------------------------------------------------------------------------
# _extract_usage_level
# ---------------------------------------------------------------------------


class TestExtractUsageLevel:
    """Unit tests for the _extract_usage_level helper."""

    def test_extracts_session_with_resets(self) -> None:
        data: dict[str, Any] = {
            "five_hour": {
                "utilization": 42.567,
                "resets_at": "2026-03-16T18:00:00Z",
            }
        }
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert isinstance(result, ClaudeUsageLevel)
        assert result.name == "Session"
        assert result.percent_used == 42.6
        assert result.detail == "Resets 2026-03-16T18:00:00Z"

    def test_extracts_weekly_with_resets(self) -> None:
        data: dict[str, Any] = {
            "seven_day": {
                "utilization": 15.3,
                "resets_at": "2026-03-17T00:00:00Z",
            }
        }
        result = _extract_usage_level(data, "seven_day", "Weekly")
        assert result is not None
        assert result.name == "Weekly"
        assert result.percent_used == 15.3
        assert "Resets" in result.detail

    def test_returns_none_when_key_missing(self) -> None:
        assert _extract_usage_level({}, "five_hour", "Session") is None

    def test_returns_none_when_utilization_missing(self) -> None:
        data: dict[str, Any] = {"five_hour": {"resets_at": "2026-03-16T18:00:00Z"}}
        assert _extract_usage_level(data, "five_hour", "Session") is None

    def test_returns_none_when_utilization_is_string(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": "high"}}
        assert _extract_usage_level(data, "five_hour", "Session") is None

    def test_returns_none_when_utilization_is_none(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": None}}
        assert _extract_usage_level(data, "five_hour", "Session") is None

    def test_handles_int_utilization(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": 50}}
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert result.percent_used == 50.0

    def test_empty_detail_when_no_resets_at(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": 10.0}}
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert result.detail == ""

    def test_empty_detail_when_resets_at_empty(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": 10.0, "resets_at": ""}}
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert result.detail == ""

    def test_zero_utilization_is_valid(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": 0}}
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert result.percent_used == 0.0

    def test_rounding_to_one_decimal(self) -> None:
        data: dict[str, Any] = {"five_hour": {"utilization": 33.3333}}
        result = _extract_usage_level(data, "five_hour", "Session")
        assert result is not None
        assert result.percent_used == 33.3

    def test_custom_key_and_name(self) -> None:
        data: dict[str, Any] = {"custom_window": {"utilization": 75.0}}
        result = _extract_usage_level(data, "custom_window", "Custom")
        assert result is not None
        assert result.name == "Custom"


# ---------------------------------------------------------------------------
# Narrowed exception handlers
# ---------------------------------------------------------------------------


class TestGetClaudeOauthTokenNarrowedExceptions:
    """Verify _get_claude_oauth_token catches specific subprocess/OS errors."""

    def test_catches_subprocess_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a: Any, **kw: Any) -> None:
            raise subprocess.TimeoutExpired(cmd="security", timeout=5)

        monkeypatch.setattr(subprocess, "run", _raise)
        assert _get_claude_oauth_token() is None

    def test_catches_file_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a: Any, **kw: Any) -> None:
            raise FileNotFoundError("security not found")

        monkeypatch.setattr(subprocess, "run", _raise)
        assert _get_claude_oauth_token() is None

    def test_catches_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a: Any, **kw: Any) -> None:
            raise OSError("permission denied")

        monkeypatch.setattr(subprocess, "run", _raise)
        assert _get_claude_oauth_token() is None

    def test_catches_subprocess_called_process_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*a: Any, **kw: Any) -> None:
            raise subprocess.CalledProcessError(1, "security")

        monkeypatch.setattr(subprocess, "run", _raise)
        assert _get_claude_oauth_token() is None

    def test_does_not_catch_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a: Any, **kw: Any) -> None:
            raise ValueError("unexpected")

        monkeypatch.setattr(subprocess, "run", _raise)
        with pytest.raises(ValueError, match="unexpected"):
            _get_claude_oauth_token()


class TestFetchClaudeUsageNarrowedExceptions:
    """Verify _fetch_claude_usage catches specific URL/OS/JSON errors."""

    def _reset_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("helping_hands.server.app._usage_cache", None)
        monkeypatch.setattr("helping_hands.server.app._usage_cache_ts", 0.0)

    def test_catches_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        def _mock_urlopen(*a: Any, **kw: Any) -> None:
            raise ConnectionError("refused")

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )
        result = _fetch_claude_usage()
        assert "refused" in result.error

    def test_catches_json_decode_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )
        result = _fetch_claude_usage()
        assert result.error is not None

    def test_catches_url_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from urllib.error import URLError

        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        def _mock_urlopen(*a: Any, **kw: Any) -> None:
            raise URLError("DNS resolution failed")

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )
        result = _fetch_claude_usage()
        assert "DNS resolution failed" in result.error

    def test_catches_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        def _mock_urlopen(*a: Any, **kw: Any) -> None:
            raise OSError("network unreachable")

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )
        result = _fetch_claude_usage()
        assert "network unreachable" in result.error

    def test_does_not_catch_type_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        def _mock_urlopen(*a: Any, **kw: Any) -> None:
            raise TypeError("unexpected")

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )
        with pytest.raises(TypeError, match="unexpected"):
            _fetch_claude_usage()

    def test_http_error_body_read_failure_narrowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Inner except for reading HTTP error body is narrowed to OSError/UnicodeDecodeError."""
        from urllib.error import HTTPError

        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        exc = HTTPError(
            url="https://api.anthropic.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=MagicMock(read=MagicMock(side_effect=OSError("read failed"))),
        )

        def _mock_urlopen(*a: Any, **kw: Any) -> None:
            raise exc

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )
        result = _fetch_claude_usage()
        assert "500" in result.error
        # body should be empty since read failed
        assert result.error == "Usage API returned 500: "
