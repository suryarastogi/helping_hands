"""Protects against corrupted Redis state, unbounded loops, and write failures.

_load_meta must return None (not crash) when Redis holds invalid JSON, partial
data, or non-dict values -- otherwise a single corrupted schedule entry takes
down the entire scheduler with a JSONDecodeError.

_MAX_ITERATIONS caps the iterative-hand loop at 1000 so adversarial or buggy
prompts cannot spin a worker indefinitely, exhausting API quota and blocking
the task queue.

_apply_inline_edits must swallow OSError per-file and continue, so one
permission-denied write does not abort an entire multi-file AI task.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import HandResponse
from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubIterativeHand(_BasicIterativeHand):
    """Concrete stub for testing _BasicIterativeHand."""

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield prompt


def _make_hand(
    tmp_path: Path,
    files: dict[str, str] | None = None,
    *,
    max_iterations: int = 6,
) -> _StubIterativeHand:
    if files:
        for rel_path, content in files.items():
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="test-model")
    with patch(
        "helping_hands.lib.meta.tools.registry.build_tool_runner_map",
        return_value={},
    ):
        hand = _StubIterativeHand(config, repo_index, max_iterations=max_iterations)
    return hand


# ---------------------------------------------------------------------------
# _load_meta corrupted data handling (schedules.py)
# ---------------------------------------------------------------------------


class TestLoadMetaCorruptedData:
    """_load_meta returns None and logs warning for corrupted Redis data."""

    @pytest.fixture()
    def manager(self):
        celery = pytest.importorskip("celery", reason="celery extra not installed")  # noqa: F841
        from helping_hands.server.schedules import ScheduleManager

        mock_app = MagicMock()
        mock_app.conf.get.return_value = "redis://localhost:6379/0"
        mock_app.conf.broker_url = "redis://localhost:6379/0"
        mock_redis = MagicMock()

        with patch.object(ScheduleManager, "__init__", lambda self, app: None):
            mgr = ScheduleManager(mock_app)
        mgr._app = mock_app
        mgr._redis = mock_redis
        return mgr, mock_redis

    def test_invalid_json_returns_none(self, manager, caplog) -> None:
        mgr, mock_redis = manager
        mock_redis.get.return_value = "not valid json{{"
        with caplog.at_level(logging.WARNING):
            result = mgr._load_meta("sched_corrupt")
        assert result is None
        assert "Corrupted schedule metadata" in caplog.text

    def test_missing_required_fields_returns_none(self, manager, caplog) -> None:
        mgr, mock_redis = manager
        mock_redis.get.return_value = json.dumps({"name": "partial"})
        with caplog.at_level(logging.WARNING):
            result = mgr._load_meta("sched_partial")
        assert result is None
        assert "Corrupted schedule metadata" in caplog.text

    def test_non_dict_json_returns_none(self, manager, caplog) -> None:
        mgr, mock_redis = manager
        mock_redis.get.return_value = json.dumps([1, 2, 3])
        with caplog.at_level(logging.WARNING):
            result = mgr._load_meta("sched_list")
        assert result is None
        assert "Corrupted schedule metadata" in caplog.text

    def test_valid_data_still_works(self, manager) -> None:
        mgr, mock_redis = manager
        from helping_hands.server.schedules import ScheduledTask

        task = ScheduledTask(
            schedule_id="sched_ok",
            name="OK",
            cron_expression="0 0 * * *",
            repo_path="owner/repo",
            prompt="fix",
        )
        mock_redis.get.return_value = json.dumps(task.to_dict())
        result = mgr._load_meta("sched_ok")
        assert result is not None
        assert result.name == "OK"


# ---------------------------------------------------------------------------
# _MAX_ITERATIONS upper bound (iterative.py)
# ---------------------------------------------------------------------------


class TestMaxIterationsBound:
    """_BasicIterativeHand clamps max_iterations at _MAX_ITERATIONS."""

    def test_normal_value_unchanged(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path, max_iterations=10)
        assert hand.max_iterations == 10

    def test_exceeds_cap_clamped(self, tmp_path: Path, caplog) -> None:
        with caplog.at_level(logging.WARNING):
            hand = _make_hand(tmp_path, max_iterations=5000)
        assert hand.max_iterations == _BasicIterativeHand._MAX_ITERATIONS
        assert "exceeds cap" in caplog.text

    def test_at_cap_unchanged(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path, max_iterations=1000)
        assert hand.max_iterations == 1000

    def test_below_minimum_clamped_to_one(self, tmp_path: Path) -> None:
        hand = _make_hand(tmp_path, max_iterations=-5)
        assert hand.max_iterations == 1

    def test_constant_value(self) -> None:
        assert _BasicIterativeHand._MAX_ITERATIONS == 1000


# ---------------------------------------------------------------------------
# _apply_inline_edits OSError handling (iterative.py)
# ---------------------------------------------------------------------------


class TestApplyInlineEditsOSError:
    """_apply_inline_edits catches OSError with warning log."""

    def test_oserror_skips_file_and_logs_warning(self, tmp_path: Path, caplog) -> None:
        hand = _make_hand(tmp_path)
        content = "@@FILE: test.py\n```python\nprint('hi')\n```"
        with (
            patch(
                "helping_hands.lib.meta.tools.filesystem.write_text_file",
                side_effect=OSError("Permission denied"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            changed = hand._apply_inline_edits(content)
        assert changed == []
        assert "Permission denied" in caplog.text
        assert "Failed to write inline edit" in caplog.text

    def test_oserror_does_not_stop_other_writes(self, tmp_path: Path, caplog) -> None:
        hand = _make_hand(tmp_path)
        content = (
            "@@FILE: bad.py\n```python\nbad\n```\n\n"
            "@@FILE: good.py\n```python\ngood\n```"
        )
        call_count = 0

        def _side_effect(root, rel_path, body):
            nonlocal call_count
            call_count += 1
            if "bad" in rel_path:
                raise OSError("Disk full")
            return rel_path

        with (
            patch(
                "helping_hands.lib.meta.tools.filesystem.write_text_file",
                side_effect=_side_effect,
            ),
            caplog.at_level(logging.WARNING),
        ):
            changed = hand._apply_inline_edits(content)
        assert changed == ["good.py"]
        assert call_count == 2
        assert "Disk full" in caplog.text

    def test_valueerror_still_handled(self, tmp_path: Path) -> None:
        """Existing ValueError handling is preserved."""
        hand = _make_hand(tmp_path)
        content = "@@FILE: ../escape.py\n```python\nevil\n```"
        changed = hand._apply_inline_edits(content)
        assert changed == []
