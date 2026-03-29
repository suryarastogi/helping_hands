"""Tests for _TwoPhaseCLIHand static helpers: CI-fix prompt building, PR status
formatting, edit-request detection, and failed-check log fetching.

These helpers govern what the AI sees when CI fails (prompt content and log
snippets) and what the user sees after a run completes (PR/CI status messages).
Regressions here silently degrade the AI's ability to fix CI failures — wrong
check filtering causes the agent to attempt fixes on passing checks, while
broken log fetching removes the exact error context it needs. The
_looks_like_edit_request heuristic controls whether a no-change run triggers
an automatic retry; misclassification either wastes retries on read-only
prompts or skips retries on real edit tasks.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


class TestBuildCiFixPrompt:
    def test_includes_failed_check_details(self) -> None:
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://example.com/lint",
                },
                {
                    "name": "test",
                    "conclusion": "success",
                    "html_url": "https://example.com/test",
                },
                {
                    "name": "build",
                    "conclusion": "cancelled",
                    "html_url": "https://example.com/build",
                },
            ],
        }
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result=check_result,
            original_prompt="add feature X",
            attempt=2,
        )
        assert "CI fix attempt 2" in prompt
        assert "lint: failure" in prompt
        assert "build: cancelled" in prompt
        assert "test: success" not in prompt

    def test_no_failed_checks_shows_fallback(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={"check_runs": []},
            original_prompt="task",
            attempt=1,
        )
        assert "(no details available)" in prompt

    def test_missing_check_fields(self) -> None:
        check_result = {
            "check_runs": [
                {"conclusion": "failure"},
            ],
        }
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result=check_result,
            original_prompt="task",
            attempt=1,
        )
        assert "unknown: failure" in prompt

    def test_includes_log_output_when_provided(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {"name": "lint", "conclusion": "failure", "html_url": ""},
                ],
            },
            original_prompt="task",
            attempt=1,
            log_output="error: black would reformat file.py",
        )
        assert "Failed check log output" in prompt
        assert "black would reformat file.py" in prompt

    def test_empty_log_output_omitted(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={"check_runs": []},
            original_prompt="task",
            attempt=1,
            log_output="   ",
        )
        assert "Failed check log output" not in prompt


class TestLooksLikeEditRequest:
    def test_positive_markers(self) -> None:
        for word in ("update", "fix", "add", "remove", "refactor", "create", "change"):
            assert _TwoPhaseCLIHand._looks_like_edit_request(f"Please {word} the code")

    def test_case_insensitive(self) -> None:
        assert _TwoPhaseCLIHand._looks_like_edit_request("UPDATE the readme")

    def test_negative_example(self) -> None:
        assert not _TwoPhaseCLIHand._looks_like_edit_request("explain how X works")

    def test_another_negative(self) -> None:
        assert not _TwoPhaseCLIHand._looks_like_edit_request("list all files")


class TestFormatPrStatusMessage:
    """Test _format_pr_status_message via a minimal subclass."""

    class _Stub(_TwoPhaseCLIHand):
        _CLI_LABEL = "test"

        def __init__(self) -> None:
            # Skip parent __init__; we only use the formatting method.
            pass

    def _make_stub(self) -> _Stub:
        return self._Stub()

    def test_created(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message(
            {"pr_status": "created", "pr_url": "https://pr/1"}
        )
        assert msg is not None
        assert "PR created" in msg
        assert "https://pr/1" in msg

    def test_updated(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message(
            {"pr_status": "updated", "pr_url": "https://pr/2"}
        )
        assert msg is not None
        assert "PR updated" in msg

    def test_disabled(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message({"pr_status": "disabled"})
        assert msg is not None
        assert "--no-pr" in msg

    def test_no_changes(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message({"pr_status": "no_changes"})
        assert msg is not None
        assert "no file changes" in msg

    def test_interrupted(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message({"pr_status": "interrupted"})
        assert msg is not None
        assert "Interrupted" in msg

    def test_error_with_message(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message(
            {"pr_status": "error", "pr_error": "auth failed"}
        )
        assert msg is not None
        assert "auth failed" in msg

    def test_unknown_status(self) -> None:
        stub = self._make_stub()
        msg = stub._format_pr_status_message({"pr_status": "some_other"})
        assert msg is not None
        assert "some_other" in msg

    def test_empty_status_returns_none(self) -> None:
        stub = self._make_stub()
        assert stub._format_pr_status_message({"pr_status": ""}) is None
        assert stub._format_pr_status_message({}) is None


class TestBuildCiFixPromptMalformed:
    """Defensive handling of malformed check_result dicts."""

    def test_missing_check_runs_key(self) -> None:
        """check_result with no 'check_runs' key uses empty list fallback."""
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={},
            original_prompt="task",
            attempt=1,
        )
        assert "(no details available)" in prompt

    def test_check_run_missing_all_fields(self) -> None:
        """check_run dicts with no fields get filtered out (no matching conclusion)."""
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={"check_runs": [{}]},
            original_prompt="task",
            attempt=1,
        )
        assert "(no details available)" in prompt

    def test_timed_out_conclusion_included(self) -> None:
        """check_run with 'timed_out' conclusion is included in failure summary."""
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {"name": "deploy", "conclusion": "timed_out", "html_url": ""},
                ],
            },
            original_prompt="task",
            attempt=1,
        )
        assert "deploy: timed_out" in prompt


class TestFormatCiFixMessage:
    """Test _format_ci_fix_message via a minimal subclass."""

    class _Stub(_TwoPhaseCLIHand):
        _CLI_LABEL = "test"

        def __init__(self) -> None:
            pass

    def _make_stub(self) -> _Stub:
        return self._Stub()

    def test_success(self) -> None:
        stub = self._make_stub()
        msg = stub._format_ci_fix_message({"ci_fix_status": "success"})
        assert msg is not None
        assert "CI checks passed" in msg

    def test_exhausted(self) -> None:
        stub = self._make_stub()
        msg = stub._format_ci_fix_message(
            {"ci_fix_status": "exhausted", "ci_fix_attempts": "3"}
        )
        assert msg is not None
        assert "3 attempt(s)" in msg

    def test_pending_timeout(self) -> None:
        stub = self._make_stub()
        msg = stub._format_ci_fix_message({"ci_fix_status": "pending_timeout"})
        assert msg is not None
        assert "still pending" in msg

    def test_error(self) -> None:
        stub = self._make_stub()
        msg = stub._format_ci_fix_message(
            {"ci_fix_status": "error", "ci_fix_error": "boom"}
        )
        assert msg is not None
        assert "boom" in msg

    def test_empty_returns_none(self) -> None:
        stub = self._make_stub()
        assert stub._format_ci_fix_message({}) is None

    def test_unknown_status_returns_none(self) -> None:
        stub = self._make_stub()
        assert stub._format_ci_fix_message({"ci_fix_status": "checking"}) is None


class TestFetchFailedCheckLogs:
    """Tests for _fetch_failed_check_logs static method."""

    def test_returns_empty_for_no_failures(self) -> None:
        result = _TwoPhaseCLIHand._fetch_failed_check_logs(
            None, "owner/repo", {"check_runs": []}
        )
        assert result == ""

    def test_returns_empty_for_success_only(self) -> None:
        result = _TwoPhaseCLIHand._fetch_failed_check_logs(
            None,
            "owner/repo",
            {
                "check_runs": [
                    {"name": "test", "conclusion": "success", "html_url": ""},
                ]
            },
        )
        assert result == ""

    def test_extracts_run_id_and_fetches_log(self) -> None:
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/12345/job/67890",
                },
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "error: formatting issue"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result
            )
        assert "formatting issue" in result
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "12345" in call_args

    def test_deduplicates_run_ids(self) -> None:
        """Two jobs in the same run should only fetch logs once."""
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/12345/job/111",
                },
                {
                    "name": "test",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/12345/job/222",
                },
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "log output"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _TwoPhaseCLIHand._fetch_failed_check_logs(None, "owner/repo", check_result)
        assert mock_run.call_count == 1

    def test_truncates_long_output(self) -> None:
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/1/job/2",
                },
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "x" * 20000
        with patch("subprocess.run", return_value=mock_result):
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result, max_chars=100
            )
        assert len(result) <= 100
        assert result.startswith("...")

    def test_handles_subprocess_failure(self) -> None:
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/1/job/2",
                },
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result
            )
        assert result == ""

    def test_handles_missing_html_url(self) -> None:
        check_result = {
            "check_runs": [
                {"name": "lint", "conclusion": "failure"},
            ],
        }
        result = _TwoPhaseCLIHand._fetch_failed_check_logs(
            None, "owner/repo", check_result
        )
        assert result == ""

    def test_subprocess_timeout_continues(self) -> None:
        """When gh subprocess times out, it's swallowed and returns empty."""
        import subprocess

        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/1/job/2",
                },
            ],
        }
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=30),
        ):
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result
            )
        assert result == ""

    def test_subprocess_file_not_found_continues(self) -> None:
        """When gh binary is not found, exception is swallowed."""
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/1/job/2",
                },
            ],
        }
        with patch(
            "subprocess.run",
            side_effect=FileNotFoundError("gh not found"),
        ):
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result
            )
        assert result == ""

    def test_max_lines_truncation(self) -> None:
        """When output exceeds max_lines, only last max_lines are kept."""
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/runs/1/job/2",
                },
            ],
        }
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Generate many lines
        mock_result.stdout = "\n".join(f"line {i}" for i in range(500))
        with patch("subprocess.run", return_value=mock_result):
            result = _TwoPhaseCLIHand._fetch_failed_check_logs(
                None, "owner/repo", check_result, max_lines=10, max_chars=100000
            )
        lines = result.splitlines()
        assert len(lines) == 10
        # Should keep the last 10 lines
        assert "line 499" in lines[-1]

    def test_duplicate_run_id_skipped(self) -> None:
        """When URL has no 'runs' segment, run_id is empty and skipped."""
        check_result = {
            "check_runs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "html_url": "https://github.com/o/r/actions/job/2",
                },
            ],
        }
        result = _TwoPhaseCLIHand._fetch_failed_check_logs(
            None, "owner/repo", check_result
        )
        assert result == ""


class TestCiFixModeIdleTimeout:
    """Tests that _ci_fix_mode uses shorter idle timeout."""

    class _Stub(_TwoPhaseCLIHand):
        _CLI_LABEL = "test"

        def __init__(self) -> None:
            self._ci_fix_mode = False

    def test_normal_mode_uses_default_timeout(self) -> None:
        stub = self._Stub()
        assert stub._idle_timeout_seconds() == 900.0

    def test_ci_fix_mode_uses_shorter_timeout(self) -> None:
        stub = self._Stub()
        stub._ci_fix_mode = True
        assert stub._idle_timeout_seconds() == 300.0

    def test_ci_fix_timeout_env_override(self, monkeypatch) -> None:
        stub = self._Stub()
        stub._ci_fix_mode = True
        monkeypatch.setenv("HELPING_HANDS_CLI_CI_FIX_IDLE_TIMEOUT_SECONDS", "120")
        assert stub._idle_timeout_seconds() == 120.0
