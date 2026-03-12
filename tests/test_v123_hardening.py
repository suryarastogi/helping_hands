"""v123 — Tool summarization expansion, assert→RuntimeError guards, debug logging.

Tests for:
- schedules.py croniter/RedBeat assert→RuntimeError guards
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# schedules.py — croniter RuntimeError guards
# ---------------------------------------------------------------------------


class TestCroniterRuntimeErrorGuards:
    """Verify RuntimeError (not AssertionError) when croniter is None after check."""

    def test_validate_cron_expression_croniter_none(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.schedules as mod

        with (
            patch.object(mod, "croniter", None),
            patch.object(mod, "_check_croniter", lambda: None),
            pytest.raises(RuntimeError, match="croniter unavailable"),
        ):
            mod.validate_cron_expression("0 0 * * *")

    def test_next_run_time_croniter_none(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.schedules as mod

        with (
            patch.object(mod, "croniter", None),
            patch.object(mod, "_check_croniter", lambda: None),
            pytest.raises(RuntimeError, match="croniter unavailable"),
        ):
            mod.next_run_time("0 0 * * *")


# ---------------------------------------------------------------------------
# schedules.py — RedBeatSchedulerEntry RuntimeError guards
# ---------------------------------------------------------------------------


class TestRedBeatRuntimeErrorGuards:
    """Verify RuntimeError (not AssertionError) when RedBeatSchedulerEntry is None."""

    def test_create_redbeat_entry_none(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.schedules as mod

        with patch.object(mod, "RedBeatSchedulerEntry", None):
            mgr = MagicMock(spec=mod.ScheduleManager)
            mgr._app = MagicMock()

            task = mod.ScheduledTask(
                schedule_id="test_guard",
                name="Guard Test",
                cron_expression="0 0 * * *",
                repo_path="owner/repo",
                prompt="test",
            )

            with pytest.raises(RuntimeError, match="RedBeatSchedulerEntry unavailable"):
                mod.ScheduleManager._create_redbeat_entry(mgr, task)

    def test_delete_redbeat_entry_none(self) -> None:
        pytest.importorskip("celery")
        import helping_hands.server.schedules as mod

        with patch.object(mod, "RedBeatSchedulerEntry", None):
            mgr = MagicMock(spec=mod.ScheduleManager)
            mgr._app = MagicMock()

            with pytest.raises(RuntimeError, match="RedBeatSchedulerEntry unavailable"):
                mod.ScheduleManager._delete_redbeat_entry(mgr, "test_id")
