"""Tests for v137 — health check timeout and Anthropic API constants."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# server/app.py constants
# ---------------------------------------------------------------------------

pytest.importorskip("fastapi")


class TestAppHealthCheckTimeoutConstants:
    """Verify health-check timeout constants in server/app.py."""

    def test_keychain_timeout_value(self) -> None:
        from helping_hands.server.app import _KEYCHAIN_TIMEOUT_S

        assert _KEYCHAIN_TIMEOUT_S == 5

    def test_usage_api_timeout_value(self) -> None:
        from helping_hands.server.app import _USAGE_API_TIMEOUT_S

        assert _USAGE_API_TIMEOUT_S == 10

    def test_redis_health_timeout_value(self) -> None:
        from helping_hands.server.app import _REDIS_HEALTH_TIMEOUT_S

        assert _REDIS_HEALTH_TIMEOUT_S == 2

    def test_db_health_timeout_value(self) -> None:
        from helping_hands.server.app import _DB_HEALTH_TIMEOUT_S

        assert _DB_HEALTH_TIMEOUT_S == 3

    def test_celery_health_timeout_value(self) -> None:
        from helping_hands.server.app import _CELERY_HEALTH_TIMEOUT_S

        assert _CELERY_HEALTH_TIMEOUT_S == 2.0

    def test_celery_inspect_timeout_value(self) -> None:
        from helping_hands.server.app import _CELERY_INSPECT_TIMEOUT_S

        assert _CELERY_INSPECT_TIMEOUT_S == 1.0

    def test_all_timeouts_are_positive(self) -> None:
        from helping_hands.server.app import (
            _CELERY_HEALTH_TIMEOUT_S,
            _CELERY_INSPECT_TIMEOUT_S,
            _DB_HEALTH_TIMEOUT_S,
            _KEYCHAIN_TIMEOUT_S,
            _REDIS_HEALTH_TIMEOUT_S,
            _USAGE_API_TIMEOUT_S,
        )

        for name, val in [
            ("_KEYCHAIN_TIMEOUT_S", _KEYCHAIN_TIMEOUT_S),
            ("_USAGE_API_TIMEOUT_S", _USAGE_API_TIMEOUT_S),
            ("_REDIS_HEALTH_TIMEOUT_S", _REDIS_HEALTH_TIMEOUT_S),
            ("_DB_HEALTH_TIMEOUT_S", _DB_HEALTH_TIMEOUT_S),
            ("_CELERY_HEALTH_TIMEOUT_S", _CELERY_HEALTH_TIMEOUT_S),
            ("_CELERY_INSPECT_TIMEOUT_S", _CELERY_INSPECT_TIMEOUT_S),
        ]:
            assert isinstance(val, (int, float)), f"{name} should be numeric"
            assert val > 0, f"{name} should be positive"


class TestAppAnthropicApiConstants:
    """Verify Anthropic usage API constants in server/app.py."""

    def test_usage_url_value(self) -> None:
        from helping_hands.server.app import _ANTHROPIC_USAGE_URL

        assert _ANTHROPIC_USAGE_URL == "https://api.anthropic.com/api/oauth/usage"

    def test_usage_url_is_https(self) -> None:
        from helping_hands.server.app import _ANTHROPIC_USAGE_URL

        assert _ANTHROPIC_USAGE_URL.startswith("https://")

    def test_beta_header_value(self) -> None:
        from helping_hands.server.app import _ANTHROPIC_BETA_HEADER

        assert _ANTHROPIC_BETA_HEADER == "oauth-2025-04-20"

    def test_user_agent_value(self) -> None:
        from helping_hands.server.app import _USAGE_USER_AGENT

        assert _USAGE_USER_AGENT == "claude-code/2.0.32"

    def test_user_agent_has_version(self) -> None:
        from helping_hands.server.app import _USAGE_USER_AGENT

        assert "/" in _USAGE_USER_AGENT


# ---------------------------------------------------------------------------
# server/celery_app.py constants
# ---------------------------------------------------------------------------


class TestCeleryAppAnthropicApiConstants:
    """Verify Anthropic usage API constants in server/celery_app.py."""

    def test_usage_url_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _ANTHROPIC_USAGE_URL

        assert _ANTHROPIC_USAGE_URL == "https://api.anthropic.com/api/oauth/usage"

    def test_beta_header_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _ANTHROPIC_BETA_HEADER

        assert _ANTHROPIC_BETA_HEADER == "oauth-2025-04-20"

    def test_user_agent_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _USAGE_USER_AGENT

        assert _USAGE_USER_AGENT == "claude-code/2.0.32"

    def test_usage_api_timeout_value(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.celery_app import _USAGE_API_TIMEOUT_S

        assert _USAGE_API_TIMEOUT_S == 10

    def test_constants_match_app_module(self) -> None:
        """Ensure app.py and celery_app.py constants stay in sync."""
        pytest.importorskip("celery")
        from helping_hands.server import app as app_mod, celery_app as celery_mod

        assert app_mod._ANTHROPIC_USAGE_URL == celery_mod._ANTHROPIC_USAGE_URL
        assert app_mod._ANTHROPIC_BETA_HEADER == celery_mod._ANTHROPIC_BETA_HEADER
        assert app_mod._USAGE_USER_AGENT == celery_mod._USAGE_USER_AGENT
        assert app_mod._USAGE_API_TIMEOUT_S == celery_mod._USAGE_API_TIMEOUT_S
