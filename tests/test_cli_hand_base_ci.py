"""Tests for CLI base hand static/class helpers (CI fix, PR status, edit detection)."""

from __future__ import annotations

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
        assert "add feature X" in prompt

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


class TestBuildCiFixPromptUrlFormatting:
    """URL formatting: empty URLs omit parentheses, present URLs include them (v147)."""

    def test_present_url_included_in_parentheses(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {
                        "name": "lint",
                        "conclusion": "failure",
                        "html_url": "https://ci.example.com/lint/123",
                    },
                ],
            },
            original_prompt="task",
            attempt=1,
        )
        assert "lint: failure (https://ci.example.com/lint/123)" in prompt

    def test_empty_url_omits_parentheses(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {
                        "name": "test",
                        "conclusion": "failure",
                        "html_url": "",
                    },
                ],
            },
            original_prompt="task",
            attempt=1,
        )
        assert "test: failure" in prompt
        assert "()" not in prompt
        assert "test: failure (" not in prompt

    def test_missing_url_key_omits_parentheses(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {
                        "name": "build",
                        "conclusion": "cancelled",
                    },
                ],
            },
            original_prompt="task",
            attempt=1,
        )
        assert "build: cancelled" in prompt
        assert "()" not in prompt

    def test_mixed_urls_formatted_correctly(self) -> None:
        prompt = _TwoPhaseCLIHand._build_ci_fix_prompt(
            check_result={
                "check_runs": [
                    {
                        "name": "lint",
                        "conclusion": "failure",
                        "html_url": "https://ci.example.com/lint",
                    },
                    {
                        "name": "test",
                        "conclusion": "failure",
                        "html_url": "",
                    },
                ],
            },
            original_prompt="task",
            attempt=1,
        )
        assert "lint: failure (https://ci.example.com/lint)" in prompt
        assert "  - test: failure\n" in prompt or "  - test: failure" in prompt
        # test line should NOT have parentheses
        lines = prompt.split("\n")
        test_lines = [line for line in lines if "test: failure" in line]
        assert len(test_lines) == 1
        assert "(" not in test_lines[0]


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
