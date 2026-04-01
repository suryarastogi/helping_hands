"""Protects form-redirect field fidelity and failure-path debug logging.

_build_form_redirect_query must include all truthy optional fields and exclude
false/None/blank ones; if a field is dropped, the browser redirect after a
failed build submission silently loses user input (model, pr_number, etc.),
forcing the user to re-enter everything.

The logging tests verify that _update_pr_description, _schedule_to_response,
and _fetch_claude_usage emit structured debug messages on failure.  Without
these, silent exception swallowing makes production incidents undiagnosable.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

pytest.importorskip("fastapi")

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import Hand
from helping_hands.lib.repo import RepoIndex
from helping_hands.server.app import (
    _build_form_redirect_query,
    _fetch_claude_usage,
    _schedule_to_response,
)

# ---------------------------------------------------------------------------
# _build_form_redirect_query (server/app.py)
# ---------------------------------------------------------------------------


class TestBuildFormRedirectQuery:
    """Tests for the extracted _build_form_redirect_query helper."""

    def test_minimal_required_fields(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="do stuff",
            backend="codexcli",
            max_iterations=6,
            error="something broke",
        )
        assert result["repo_path"] == "/repo"
        assert result["prompt"] == "do stuff"
        assert result["backend"] == "codexcli"
        assert result["max_iterations"] == "6"
        assert result["error"] == "something broke"
        # Optional fields not present
        assert "model" not in result
        assert "no_pr" not in result
        assert "enable_execution" not in result
        assert "enable_web" not in result
        assert "use_native_cli_auth" not in result
        assert "fix_ci" not in result
        assert "ci_check_wait_minutes" not in result
        assert "pr_number" not in result
        assert "tools" not in result
        assert "skills" not in result

    def test_all_optional_fields_included(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=10,
            error="err",
            model="gpt-5.2",
            no_pr=True,
            enable_execution=True,
            enable_web=True,
            use_native_cli_auth=True,
            fix_ci=True,
            ci_check_wait_minutes=5.0,
            pr_number=42,
            tools="bash,python",
            skills="prd",
        )
        assert result["model"] == "gpt-5.2"
        assert result["no_pr"] == "1"
        assert result["enable_execution"] == "1"
        assert result["enable_web"] == "1"
        assert result["use_native_cli_auth"] == "1"
        assert result["fix_ci"] == "1"
        assert result["ci_check_wait_minutes"] == "5.0"
        assert result["pr_number"] == "42"
        assert result["tools"] == "bash,python"
        assert result["skills"] == "prd"

    def test_false_booleans_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            no_pr=False,
            enable_execution=False,
            enable_web=False,
            use_native_cli_auth=False,
            fix_ci=False,
        )
        assert "no_pr" not in result
        assert "enable_execution" not in result
        assert "enable_web" not in result
        assert "use_native_cli_auth" not in result
        assert "fix_ci" not in result

    def test_default_ci_check_wait_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            ci_check_wait_minutes=3.0,
        )
        assert "ci_check_wait_minutes" not in result

    def test_none_pr_number_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            pr_number=None,
        )
        assert "pr_number" not in result

    def test_empty_tools_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            tools="",
        )
        assert "tools" not in result

    def test_whitespace_tools_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            tools="   ",
        )
        assert "tools" not in result

    def test_whitespace_skills_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            skills="   ",
        )
        assert "skills" not in result

    def test_none_model_excluded(self) -> None:
        result = _build_form_redirect_query(
            repo_path="/repo",
            prompt="task",
            backend="codexcli",
            max_iterations=6,
            error="err",
            model=None,
        )
        assert "model" not in result


# ---------------------------------------------------------------------------
# _update_pr_description exception logging (base.py)
# ---------------------------------------------------------------------------


class _StubHand(Hand):
    """Minimal concrete Hand for testing base methods."""

    async def run(self, *, interrupt=None):
        return None

    async def stream(self, *, interrupt=None):
        yield ""

    def _pr_description_cmd(self):
        return None


class TestUpdatePrDescriptionLogging:
    """Verify exception is logged instead of silently suppressed."""

    def test_logs_debug_on_update_failure(
        self, tmp_path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        config = Config(repo=str(repo_dir), model="test-model")
        index = RepoIndex(root=repo_dir)
        hand = _StubHand(config, index)
        hand.pr_number = 99

        mock_gh = MagicMock()
        mock_gh.update_pr_body.side_effect = GithubException(500, "API error", None)

        with (
            patch(
                "helping_hands.lib.hands.v1.hand.pr_description"
                ".generate_pr_description",
                return_value=None,
            ),
            caplog.at_level(logging.DEBUG),
        ):
            # Should not raise
            hand._update_pr_description(
                gh=mock_gh,
                repo="owner/repo",
                repo_dir=repo_dir,
                backend="test",
                prompt="task",
                summary="done",
                base_branch="main",
                commit_sha="abc123",
            )

        assert any(
            "Failed to update PR #99 description" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _schedule_to_response exception logging (app.py)
# ---------------------------------------------------------------------------


class _FakeScheduledTask:
    def __init__(self, **kwargs):
        defaults = {
            "schedule_id": "sched-1",
            "name": "Test",
            "cron_expression": "0 * * * *",
            "repo_path": "/tmp/repo",
            "prompt": "fix",
            "backend": "codexcli",
            "model": None,
            "max_iterations": 6,
            "pr_number": None,
            "no_pr": False,
            "enable_execution": False,
            "enable_web": False,
            "use_native_cli_auth": False,
            "fix_ci": False,
            "ci_check_wait_minutes": 3.0,
            "github_token": None,
            "reference_repos": [],
            "tools": [],
            "skills": [],
            "enabled": True,
            "created_at": "2026-03-10T00:00:00",
            "last_run_at": "2026-03-10T00:00:00",
            "last_run_task_id": "task-0",
            "run_count": 0,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class TestScheduleToResponseLogging:
    """Verify next_run calculation errors are logged."""

    def test_logs_debug_on_next_run_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        task = _FakeScheduledTask(enabled=True, cron_expression="bad cron")

        with (
            patch(
                "helping_hands.server.schedules.next_run_time",
                side_effect=ValueError("invalid cron"),
            ),
            caplog.at_level(logging.DEBUG),
        ):
            resp = _schedule_to_response(task)

        assert resp.next_run_at is None
        assert any(
            "Failed to calculate next run for schedule sched-1" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _fetch_claude_usage error body logging (app.py)
# ---------------------------------------------------------------------------


class TestFetchClaudeUsageErrorBodyLogging:
    """Verify HTTP error body read failures are logged."""

    def test_logs_debug_when_error_body_unreadable(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        import urllib.error

        mock_exc = urllib.error.HTTPError(
            url="https://api.anthropic.com/api/oauth/usage",
            code=500,
            msg="Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        # Make read() raise to trigger the logging path
        mock_exc.read = MagicMock(side_effect=OSError("read failed"))

        with (
            patch(
                "helping_hands.server.app._get_claude_oauth_token",
                return_value="test-token",
            ),
            patch(
                "helping_hands.server.app.urllib_request.urlopen",
                side_effect=mock_exc,
            ),
            caplog.at_level(logging.DEBUG),
        ):
            resp = _fetch_claude_usage(force=True)

        assert resp.error is not None
        assert "500" in resp.error
        assert any(
            "Failed to read HTTP error body" in r.message for r in caplog.records
        )
