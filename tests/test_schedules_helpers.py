"""Unit tests for pure helper functions in server/schedules.py.

Covers interval/cron schedule validation, next-run-time calculations, and
schedule ID generation — all pure functions that need no Redis or Celery Beat.

Regressions here would cause schedules to fire at wrong times, reject valid
cron expressions, or generate malformed schedule IDs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("celery")

from helping_hands.server.schedules import (
    generate_schedule_id,
    next_interval_run_time,
    next_run_time,
    validate_cron_expression,
    validate_interval_seconds,
)

# ---------------------------------------------------------------------------
# validate_interval_seconds
# ---------------------------------------------------------------------------


class TestValidateIntervalSeconds:
    def test_valid_interval(self) -> None:
        assert validate_interval_seconds(300) == 300

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError, match="required"):
            validate_interval_seconds(None)

    def test_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match=">="):
            validate_interval_seconds(1)

    def test_too_large_raises(self) -> None:
        with pytest.raises(ValueError, match="<="):
            validate_interval_seconds(999_999_999)

    def test_minimum_boundary(self) -> None:
        # 60 is the minimum interval (1 minute)
        result = validate_interval_seconds(60)
        assert result == 60


# ---------------------------------------------------------------------------
# validate_cron_expression
# ---------------------------------------------------------------------------


class TestValidateCronExpression:
    def test_valid_cron(self) -> None:
        result = validate_cron_expression("0 * * * *")
        assert result == "0 * * * *"

    def test_strips_whitespace(self) -> None:
        result = validate_cron_expression("  0 * * * *  ")
        assert result == "0 * * * *"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cron"):
            validate_cron_expression("not a cron")

    def test_preset_resolved(self) -> None:
        # "@hourly" is a standard cron preset
        result = validate_cron_expression("@hourly")
        assert result  # should resolve to a valid expression


# ---------------------------------------------------------------------------
# next_run_time (cron)
# ---------------------------------------------------------------------------


class TestNextRunTime:
    def test_returns_future_datetime(self) -> None:
        base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        result = next_run_time("0 * * * *", base_time=base)
        assert result > base

    def test_hourly_advances_one_hour(self) -> None:
        base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        result = next_run_time("0 * * * *", base_time=base)
        expected = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
        assert result == expected

    def test_defaults_to_now_utc(self) -> None:
        result = next_run_time("0 * * * *")
        assert result.tzinfo is not None
        assert result > datetime.now(UTC) - timedelta(seconds=5)


# ---------------------------------------------------------------------------
# next_interval_run_time
# ---------------------------------------------------------------------------


class TestNextIntervalRunTime:
    def test_with_last_run(self) -> None:
        last = "2026-04-04T10:00:00+00:00"
        result = next_interval_run_time(300, last_run_at=last)
        expected = datetime(2026, 4, 4, 10, 5, tzinfo=UTC)
        assert result == expected

    def test_none_last_run_returns_now(self) -> None:
        result = next_interval_run_time(300, last_run_at=None)
        assert abs((result - datetime.now(UTC)).total_seconds()) < 5

    def test_naive_timestamp_gets_utc(self) -> None:
        last = "2026-04-04T10:00:00"
        result = next_interval_run_time(60, last_run_at=last)
        assert result.tzinfo is not None
        expected = datetime(2026, 4, 4, 10, 1, tzinfo=UTC)
        assert result == expected

    def test_large_interval(self) -> None:
        last = "2026-04-04T00:00:00+00:00"
        result = next_interval_run_time(86400, last_run_at=last)
        expected = datetime(2026, 4, 5, 0, 0, tzinfo=UTC)
        assert result == expected


# ---------------------------------------------------------------------------
# generate_schedule_id
# ---------------------------------------------------------------------------


class TestGenerateScheduleId:
    def test_prefix(self) -> None:
        sid = generate_schedule_id()
        assert sid.startswith("sched_")

    def test_length(self) -> None:
        sid = generate_schedule_id()
        # "sched_" (6 chars) + 12 hex chars = 18
        assert len(sid) == 18

    def test_hex_suffix(self) -> None:
        sid = generate_schedule_id()
        hex_part = sid[6:]
        int(hex_part, 16)  # should not raise

    def test_uniqueness(self) -> None:
        ids = {generate_schedule_id() for _ in range(100)}
        assert len(ids) == 100
