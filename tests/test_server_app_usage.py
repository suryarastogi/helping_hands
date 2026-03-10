"""Tests for server app usage helpers: _get_claude_oauth_token, _fetch_claude_usage."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastapi")

from helping_hands.server.app import (
    ClaudeUsageResponse,
    _fetch_claude_usage,
    _get_claude_oauth_token,
)

# --- _get_claude_oauth_token ---


class TestGetClaudeOauthToken:
    """Direct unit tests for the macOS Keychain reader."""

    def test_returns_access_token_from_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        creds = {"claudeAiOauth": {"accessToken": "eyABC123"}}
        mock_result = SimpleNamespace(returncode=0, stdout=json.dumps(creds), stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() == "eyABC123"

    def test_returns_none_for_json_without_oauth_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(
            returncode=0, stdout='{"other": "data"}', stderr=""
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() is None

    def test_returns_plain_token_starting_with_ey(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(returncode=0, stdout="eyPlainJWT", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() == "eyPlainJWT"

    def test_returns_none_for_plain_non_jwt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(returncode=0, stdout="not-a-jwt-token", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() is None

    def test_returns_none_for_nonzero_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(returncode=44, stdout="", stderr="err")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() is None

    def test_returns_none_for_empty_stdout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(returncode=0, stdout="  \n  ", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        assert _get_claude_oauth_token() is None

    def test_returns_none_on_subprocess_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="security", timeout=5)

        monkeypatch.setattr(subprocess, "run", _raise)

        assert _get_claude_oauth_token() is None

    def test_returns_none_on_generic_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*a, **kw):
            raise FileNotFoundError("security not found")

        monkeypatch.setattr(subprocess, "run", _raise)

        assert _get_claude_oauth_token() is None

    def test_returns_none_for_malformed_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_result = SimpleNamespace(returncode=0, stdout="{bad json", stderr="")
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)

        # Malformed JSON that doesn't start with "ey" → None
        assert _get_claude_oauth_token() is None


# --- _fetch_claude_usage ---


class TestFetchClaudeUsage:
    """Direct unit tests for the usage API fetcher."""

    def _reset_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("helping_hands.server.app._usage_cache", None)
        monkeypatch.setattr("helping_hands.server.app._usage_cache_ts", 0.0)

    def test_returns_cache_hit_when_fresh(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import time

        cached = ClaudeUsageResponse(levels=[], error=None, fetched_at="cached")
        monkeypatch.setattr("helping_hands.server.app._usage_cache", cached)
        monkeypatch.setattr(
            "helping_hands.server.app._usage_cache_ts", time.monotonic()
        )

        result = _fetch_claude_usage()
        assert result.fetched_at == "cached"

    def test_cache_expired_refetches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cached = ClaudeUsageResponse(levels=[], error=None, fetched_at="stale")
        monkeypatch.setattr("helping_hands.server.app._usage_cache", cached)
        # Set cache timestamp far in the past
        monkeypatch.setattr("helping_hands.server.app._usage_cache_ts", 0.0)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token", lambda: None
        )

        result = _fetch_claude_usage()
        # Should have re-fetched (no token → error)
        assert result.fetched_at != "stale"
        assert "Keychain" in result.error

    def test_no_token_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token", lambda: None
        )

        result = _fetch_claude_usage()
        assert result.error is not None
        assert "Keychain" in result.error
        assert result.levels == []

    def test_http_error_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from urllib.error import HTTPError

        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        exc = HTTPError(
            url="https://api.anthropic.com/api/oauth/usage",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=MagicMock(read=lambda: b"rate limited"),
        )

        def _mock_urlopen(*a, **kw):
            raise exc

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )

        result = _fetch_claude_usage()
        assert "429" in result.error
        assert "rate limited" in result.error

    def test_generic_exception_returns_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        def _mock_urlopen(*a, **kw):
            raise ConnectionError("network down")

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen", _mock_urlopen
        )

        result = _fetch_claude_usage()
        assert "network down" in result.error

    def test_successful_fetch_with_session_and_weekly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        api_data = {
            "five_hour": {
                "utilization": 42.567,
                "resets_at": "2026-03-10T18:00:00Z",
            },
            "seven_day": {
                "utilization": 15.3,
                "resets_at": "2026-03-17T00:00:00Z",
            },
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(api_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_claude_usage()
        assert result.error is None
        assert len(result.levels) == 2
        assert result.levels[0].name == "Session"
        assert result.levels[0].percent_used == 42.6
        assert "Resets" in result.levels[0].detail
        assert result.levels[1].name == "Weekly"
        assert result.levels[1].percent_used == 15.3

    def test_no_usage_data_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"{}"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_claude_usage()
        assert "No usage data" in result.error

    def test_force_bypasses_fresh_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import time

        cached = ClaudeUsageResponse(levels=[], error=None, fetched_at="cached")
        monkeypatch.setattr("helping_hands.server.app._usage_cache", cached)
        monkeypatch.setattr(
            "helping_hands.server.app._usage_cache_ts", time.monotonic()
        )
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token", lambda: None
        )

        result = _fetch_claude_usage(force=True)
        assert result.fetched_at != "cached"

    def test_session_only_no_weekly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        api_data = {
            "five_hour": {"utilization": 10.0},
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(api_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_claude_usage()
        assert result.error is None
        assert len(result.levels) == 1
        assert result.levels[0].name == "Session"
        assert result.levels[0].detail == ""  # no resets_at

    def test_successful_fetch_updates_cache(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._reset_cache(monkeypatch)
        monkeypatch.setattr(
            "helping_hands.server.app._get_claude_oauth_token",
            lambda: "eyToken",
        )

        api_data = {"five_hour": {"utilization": 5.0}}

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(api_data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda s, *a: None

        monkeypatch.setattr(
            "helping_hands.server.app.urllib_request.urlopen",
            lambda *a, **kw: mock_resp,
        )

        result = _fetch_claude_usage()
        assert result.error is None

        # Second call should return cache
        cached_result = _fetch_claude_usage()
        assert cached_result.fetched_at == result.fetched_at
