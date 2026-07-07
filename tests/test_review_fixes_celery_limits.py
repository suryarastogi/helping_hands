"""Tests for the Celery reliability fixes from the code review.

Covers the ``build_feature`` task time limits and the ``watch_issues_poll``
rate-limit retry countdown helper.
"""

from __future__ import annotations

import time

from helping_hands.server.celery_app import (
    _BUILD_HARD_TIME_LIMIT_S,
    _BUILD_SOFT_TIME_LIMIT_S,
    _WATCH_RATE_LIMIT_MAX_COUNTDOWN_S,
    _env_positive_int,
    _rate_limit_retry_countdown,
    build_feature,
)


class TestBuildTimeLimits:
    def test_soft_limit_registered_on_task(self) -> None:
        assert build_feature.soft_time_limit == _BUILD_SOFT_TIME_LIMIT_S

    def test_hard_limit_registered_on_task(self) -> None:
        assert build_feature.time_limit == _BUILD_HARD_TIME_LIMIT_S

    def test_hard_limit_exceeds_soft(self) -> None:
        # Graceful SoftTimeLimitExceeded must fire before the SIGKILL backstop.
        assert _BUILD_HARD_TIME_LIMIT_S > _BUILD_SOFT_TIME_LIMIT_S


class TestEnvPositiveInt:
    def test_returns_default_when_unset(self, monkeypatch) -> None:
        monkeypatch.delenv("HH_TEST_LIMIT", raising=False)
        assert _env_positive_int("HH_TEST_LIMIT", 42) == 42

    def test_parses_valid_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HH_TEST_LIMIT", "100")
        assert _env_positive_int("HH_TEST_LIMIT", 42) == 100

    def test_falls_back_on_non_numeric(self, monkeypatch) -> None:
        monkeypatch.setenv("HH_TEST_LIMIT", "abc")
        assert _env_positive_int("HH_TEST_LIMIT", 42) == 42

    def test_falls_back_on_non_positive(self, monkeypatch) -> None:
        monkeypatch.setenv("HH_TEST_LIMIT", "0")
        assert _env_positive_int("HH_TEST_LIMIT", 42) == 42
        monkeypatch.setenv("HH_TEST_LIMIT", "-5")
        assert _env_positive_int("HH_TEST_LIMIT", 42) == 42


class _FakeRateLimitError(Exception):
    def __init__(self, headers: dict[str, str]) -> None:
        super().__init__("rate limited")
        self.headers = headers


class TestRateLimitRetryCountdown:
    def test_uses_retry_after_header(self) -> None:
        exc = _FakeRateLimitError({"retry-after": "30"})
        assert _rate_limit_retry_countdown(exc) == 30

    def test_uses_reset_epoch_when_no_retry_after(self) -> None:
        future = time.time() + 45
        exc = _FakeRateLimitError({"x-ratelimit-reset": str(future)})
        countdown = _rate_limit_retry_countdown(exc)
        assert 40 <= countdown <= 46

    def test_clamps_to_max(self) -> None:
        exc = _FakeRateLimitError({"retry-after": "99999"})
        assert _rate_limit_retry_countdown(exc) == _WATCH_RATE_LIMIT_MAX_COUNTDOWN_S

    def test_floor_of_one_second(self) -> None:
        exc = _FakeRateLimitError({"retry-after": "0"})
        assert _rate_limit_retry_countdown(exc) == 1

    def test_defaults_when_no_headers(self) -> None:
        exc = _FakeRateLimitError({})
        assert _rate_limit_retry_countdown(exc) == 60
