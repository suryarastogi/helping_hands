"""Tests for v122 defensive hardening changes.

Covers:
- assert→explicit RuntimeError guards in command.py and e2e.py
- Debug logging in silent exception handlers (claude.py, schedules.py,
  iterative.py, e2e.py)
- MCP server input validation (build_feature, get_task_status, web_search,
  web_browse)
- ScheduledTask.from_dict required-field validation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

# ---------------------------------------------------------------------------
# command.py: assert→RuntimeError guards
# ---------------------------------------------------------------------------


class TestCommandAssertGuards:
    """Verify that command.py uses explicit RuntimeError instead of assert."""

    def test_run_bash_script_script_path_guard_is_runtime_error(self) -> None:
        """The guard at line 205 should be RuntimeError, not AssertionError."""
        import inspect

        from helping_hands.lib.meta.tools.command import run_bash_script

        source = inspect.getsource(run_bash_script)
        assert "assert script_path is not None" not in source
        assert "RuntimeError" in source

    def test_run_bash_script_inline_script_guard_is_runtime_error(self) -> None:
        """The guard at line 217 should be RuntimeError, not AssertionError."""
        import inspect

        from helping_hands.lib.meta.tools.command import run_bash_script

        source = inspect.getsource(run_bash_script)
        assert "assert inline_script is not None" not in source
        assert "RuntimeError" in source


# ---------------------------------------------------------------------------
# e2e.py: assert→RuntimeError guard
# ---------------------------------------------------------------------------


class TestE2EAssertGuard:
    """Verify that e2e.py uses explicit RuntimeError for pr_number."""

    def test_final_pr_number_guard_is_runtime_error(self) -> None:
        import inspect

        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        source = inspect.getsource(E2EHand.run)
        assert "assert final_pr_number is not None" not in source
        assert "RuntimeError" in source
        assert "final_pr_number is unexpectedly None" in source


# ---------------------------------------------------------------------------
# claude.py: geteuid exception logging
# ---------------------------------------------------------------------------


class TestClaudeGeteuidExceptionLogging:
    """Verify that _skip_permissions_enabled logs on geteuid failure."""

    @pytest.fixture()
    def claude_hand(self) -> Any:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        config = MagicMock()
        config.model = "claude-opus-4-6"
        config.verbose = False
        config.tools = None
        config.enabled_tools = ()
        config.enabled_skills = ()
        repo_index = MagicMock()
        return ClaudeCodeHand(config, repo_index)

    def test_logs_debug_when_geteuid_raises(
        self, claude_hand: Any, monkeypatch: pytest.MonkeyPatch, caplog: Any
    ) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _broken_geteuid() -> int:
            raise OSError("geteuid unavailable")

        monkeypatch.setattr("os.geteuid", _broken_geteuid)
        with caplog.at_level(
            logging.DEBUG, logger="helping_hands.lib.hands.v1.hand.cli.claude"
        ):
            result = claude_hand._skip_permissions_enabled()
        assert result is True
        assert "geteuid() check failed" in caplog.text


# ---------------------------------------------------------------------------
# schedules.py: KeyError logging in _delete_redbeat_entry
# ---------------------------------------------------------------------------


class TestDeleteRedbeatEntryLogging:
    """Verify that _delete_redbeat_entry logs on KeyError."""

    def test_logs_debug_when_entry_not_found(self, caplog: Any) -> None:
        pytest.importorskip("redbeat")
        from helping_hands.server.schedules import ScheduleManager

        mock_app = MagicMock()
        mock_app.conf = {"redbeat_redis_url": "redis://localhost:6379/0"}
        with patch("helping_hands.server.schedules.ScheduleManager._get_redis_client"):
            mgr = ScheduleManager(mock_app)

        # Mock RedBeatSchedulerEntry.from_key to raise KeyError
        with (
            patch(
                "helping_hands.server.schedules.RedBeatSchedulerEntry"
            ) as mock_entry_cls,
            caplog.at_level(logging.DEBUG, logger="helping_hands.server.schedules"),
        ):
            mock_entry_cls.from_key.side_effect = KeyError("not found")
            mgr._delete_redbeat_entry("sched_abc123")

        assert "RedBeat entry not found for schedule sched_abc123" in caplog.text


# ---------------------------------------------------------------------------
# schedules.py: ScheduledTask.from_dict required-field validation
# ---------------------------------------------------------------------------


class TestScheduledTaskFromDictValidation:
    """Verify that from_dict raises ValueError for missing required fields."""

    def test_raises_on_missing_schedule_id(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "name": "test",
            "cron_expression": "0 * * * *",
            "repo_path": "/tmp/repo",
            "prompt": "do stuff",
        }
        with pytest.raises(ValueError, match="schedule_id"):
            ScheduledTask.from_dict(data)

    def test_raises_on_missing_multiple_fields(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import ScheduledTask

        data: dict[str, Any] = {"name": "test"}
        with pytest.raises(ValueError, match="Missing required fields"):
            ScheduledTask.from_dict(data)

    def test_raises_on_empty_dict(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import ScheduledTask

        with pytest.raises(ValueError, match="Missing required fields"):
            ScheduledTask.from_dict({})

    def test_accepts_valid_data(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "sched_abc",
            "name": "test",
            "cron_expression": "0 * * * *",
            "repo_path": "/tmp/repo",
            "prompt": "do stuff",
        }
        task = ScheduledTask.from_dict(data)
        assert task.schedule_id == "sched_abc"
        assert task.backend == "claudecodecli"  # default

    def test_missing_prompt_only(self) -> None:
        pytest.importorskip("celery")
        from helping_hands.server.schedules import ScheduledTask

        data = {
            "schedule_id": "s1",
            "name": "test",
            "cron_expression": "0 * * * *",
            "repo_path": "/tmp/repo",
        }
        with pytest.raises(ValueError, match="prompt"):
            ScheduledTask.from_dict(data)


# ---------------------------------------------------------------------------
# iterative.py: _apply_inline_edits logging
# ---------------------------------------------------------------------------


class TestApplyInlineEditsLogging:
    """Verify that _apply_inline_edits logs on ValueError."""

    def test_logs_debug_when_write_raises_value_error(
        self, tmp_path: Path, caplog: Any
    ) -> None:
        from collections.abc import AsyncIterator

        from helping_hands.lib.hands.v1.hand.base import HandResponse
        from helping_hands.lib.hands.v1.hand.iterative import (
            _BasicIterativeHand,
        )

        # Create a concrete subclass to satisfy abstract methods
        class _ConcreteHand(_BasicIterativeHand):
            def run(self, prompt: str, **kw: Any) -> HandResponse:
                raise NotImplementedError

            async def stream(self, prompt: str) -> AsyncIterator[str]:
                raise NotImplementedError
                yield  # type: ignore[misc]

        config = MagicMock()
        config.model = "test"
        config.verbose = False
        config.enable_execution = False
        config.enable_web = False
        config.tools = None
        config.enabled_tools = ()
        config.enabled_skills = ()

        @dataclass
        class _FakeIndex:
            root: Path
            files: list[str]

            @classmethod
            def from_path(cls, path: Path) -> _FakeIndex:
                return cls(root=path, files=[])

        hand = _ConcreteHand(config, MagicMock())
        hand.repo_index = _FakeIndex(root=tmp_path, files=[])

        # Provide content with a file edit that triggers ValueError
        content = "@@FILE: ../escape/bad.py\n```python\nmalicious\n```"
        with caplog.at_level(
            logging.DEBUG, logger="helping_hands.lib.hands.v1.hand.iterative"
        ):
            changed = hand._apply_inline_edits(content)

        assert changed == []
        assert "Skipping inline edit" in caplog.text
        assert "../escape/bad.py" in caplog.text


# ---------------------------------------------------------------------------
# e2e.py: default_branch exception logging
# ---------------------------------------------------------------------------


class TestE2EDefaultBranchLogging:
    """Verify that E2EHand.run() logs when default_branch fails."""

    def test_logs_debug_when_default_branch_raises(
        self, tmp_path: Path, caplog: Any
    ) -> None:
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        config = MagicMock()
        config.repo = "owner/repo"
        config.model = "test"
        config.tools = None
        config.enabled_tools = ()
        config.enabled_skills = ()
        repo_index = MagicMock()
        hand = E2EHand(config, repo_index)

        mock_gh = MagicMock()
        mock_gh.default_branch.side_effect = GithubException(503, "API down", None)
        mock_gh.clone.return_value = None
        mock_gh.current_branch.return_value = "main"
        mock_gh.create_branch.return_value = None
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with (
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            caplog.at_level(
                logging.DEBUG, logger="helping_hands.lib.hands.v1.hand.e2e"
            ),
        ):
            result = hand.run("test prompt", dry_run=True)

        assert "Failed to fetch default branch" in caplog.text
        assert result.message == "E2EHand dry run complete. No push/PR performed."


# ---------------------------------------------------------------------------
# MCP server: input validation
# ---------------------------------------------------------------------------


class TestMcpBuildFeatureValidation:
    """Verify that MCP build_feature rejects empty repo_path/prompt."""

    def test_rejects_empty_repo_path(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="repo_path"):
            build_feature(repo_path="", prompt="do something")

    def test_rejects_whitespace_repo_path(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="repo_path"):
            build_feature(repo_path="   ", prompt="do something")

    def test_rejects_empty_prompt(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="prompt"):
            build_feature(repo_path="/tmp/repo", prompt="")

    def test_rejects_whitespace_prompt(self) -> None:
        from helping_hands.server.mcp_server import build_feature

        with pytest.raises(ValueError, match="prompt"):
            build_feature(repo_path="/tmp/repo", prompt="  \n  ")


class TestMcpGetTaskStatusValidation:
    """Verify that MCP get_task_status rejects empty task_id."""

    def test_rejects_empty_task_id(self) -> None:
        from helping_hands.server.mcp_server import get_task_status

        with pytest.raises(ValueError, match="task_id"):
            get_task_status(task_id="")

    def test_rejects_whitespace_task_id(self) -> None:
        from helping_hands.server.mcp_server import get_task_status

        with pytest.raises(ValueError, match="task_id"):
            get_task_status(task_id="   ")


class TestMcpWebSearchValidation:
    """Verify that MCP web_search rejects empty query."""

    def test_rejects_empty_query(self) -> None:
        from helping_hands.server.mcp_server import web_search

        with pytest.raises(ValueError, match="query"):
            web_search(query="")

    def test_rejects_whitespace_query(self) -> None:
        from helping_hands.server.mcp_server import web_search

        with pytest.raises(ValueError, match="query"):
            web_search(query="   ")


class TestMcpWebBrowseValidation:
    """Verify that MCP web_browse rejects empty url."""

    def test_rejects_empty_url(self) -> None:
        from helping_hands.server.mcp_server import web_browse

        with pytest.raises(ValueError, match="url"):
            web_browse(url="")

    def test_rejects_whitespace_url(self) -> None:
        from helping_hands.server.mcp_server import web_browse

        with pytest.raises(ValueError, match="url"):
            web_browse(url="   ")
