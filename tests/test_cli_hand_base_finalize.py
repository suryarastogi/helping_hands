"""Protects the boundary between backend output and GitHub PR creation.

_finalize_after_run must short-circuit on interrupt (returning a sentinel dict)
rather than pushing partial work to GitHub as a real PR. It also truncates long
AI output before embedding it in the PR description; exceeding the GitHub API
body limit causes a silent 422 that loses the entire PR. _collect_run_output
joins streamed chunks into the single string that feeds both the caller response
and the PR summary -- dropping chunks here silently truncates user-visible output
and produces misleading PR descriptions.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Minimal stub
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _BACKEND_NAME = "stub-backend"
    _COMMAND_ENV_VAR = "STUB_CLI_CMD"
    _DEFAULT_CLI_CMD = "stub-cli -p"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ()
    _CONTAINER_ENABLED_ENV_VAR = ""
    _CONTAINER_IMAGE_ENV_VAR = ""
    _SUMMARY_CHAR_LIMIT = 6000

    def __init__(self, *, interrupted: bool = False) -> None:
        self._interrupt_event = MagicMock()
        self._interrupt_event.is_set.return_value = interrupted
        self.config = SimpleNamespace(
            model="default",
            verbose=False,
            use_native_cli_auth=False,
        )
        self.repo_index = MagicMock()
        self.repo_index.root.resolve.return_value = "/fake/repo"
        self.auto_pr = True


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _finalize_after_run
# ---------------------------------------------------------------------------


class TestFinalizeAfterRun:
    """Direct tests for _finalize_after_run: interrupted and normal paths."""

    def test_interrupted_returns_interrupted_metadata(self) -> None:
        stub = _Stub(interrupted=True)
        result = stub._finalize_after_run(
            prompt="build feature", message="partial output"
        )
        assert result["pr_status"] == "interrupted"
        assert result["auto_pr"] == "true"
        assert result["pr_url"] == ""

    def test_normal_calls_finalize_repo_pr(self) -> None:
        stub = _Stub(interrupted=False)
        stub._finalize_repo_pr = MagicMock(
            return_value={"pr_status": "created", "pr_url": "https://example.com/pr/1"}
        )
        result = stub._finalize_after_run(
            prompt="build feature", message="completed output"
        )
        assert result["pr_status"] == "created"
        stub._finalize_repo_pr.assert_called_once()
        call_kwargs = stub._finalize_repo_pr.call_args
        assert call_kwargs[1]["backend"] == "stub-backend"
        assert call_kwargs[1]["prompt"] == "build feature"

    def test_summary_is_truncated_before_finalize(self) -> None:
        stub = _Stub(interrupted=False)
        stub._finalize_repo_pr = MagicMock(return_value={"pr_status": "no_changes"})
        long_message = "x" * 10000
        stub._finalize_after_run(prompt="task", message=long_message)
        call_kwargs = stub._finalize_repo_pr.call_args
        summary = call_kwargs[1]["summary"]
        assert len(summary) <= 6000 + len("\n...[truncated]")
        assert summary.endswith("...[truncated]")

    def test_summary_not_truncated_when_short(self) -> None:
        stub = _Stub(interrupted=False)
        stub._finalize_repo_pr = MagicMock(return_value={"pr_status": "no_changes"})
        stub._finalize_after_run(prompt="task", message="short")
        call_kwargs = stub._finalize_repo_pr.call_args
        assert call_kwargs[1]["summary"] == "short"

    def test_auto_pr_false_in_interrupted_metadata(self) -> None:
        stub = _Stub(interrupted=True)
        stub.auto_pr = False
        result = stub._finalize_after_run(prompt="build feature", message="partial")
        assert result["auto_pr"] == "false"


# ---------------------------------------------------------------------------
# _collect_run_output
# ---------------------------------------------------------------------------


class TestCollectRunOutput:
    """Direct tests for the _collect_run_output wrapper."""

    def test_collects_emitted_chunks(self) -> None:
        stub = _Stub()

        async def fake_run_two_phase(prompt, *, emit):
            await emit("chunk1 ")
            await emit("chunk2 ")
            await emit("chunk3")

        stub._run_two_phase = fake_run_two_phase
        result = _run(stub._collect_run_output("build it"))
        assert result == "chunk1 chunk2 chunk3"

    def test_returns_empty_when_no_chunks(self) -> None:
        stub = _Stub()

        async def fake_run_two_phase(prompt, *, emit):
            pass

        stub._run_two_phase = fake_run_two_phase
        result = _run(stub._collect_run_output("build it"))
        assert result == ""

    def test_preserves_newlines_in_chunks(self) -> None:
        stub = _Stub()

        async def fake_run_two_phase(prompt, *, emit):
            await emit("line1\n")
            await emit("line2\n")

        stub._run_two_phase = fake_run_two_phase
        result = _run(stub._collect_run_output("task"))
        assert result == "line1\nline2\n"


# ---------------------------------------------------------------------------
# _truncate_summary (static helper used by _finalize_after_run)
# ---------------------------------------------------------------------------


class TestTruncateSummary:
    """Direct tests for the _truncate_summary static helper."""

    def test_short_text_returned_stripped(self) -> None:
        result = _TwoPhaseCLIHand._truncate_summary("  hello  ", limit=100)
        assert result == "hello"

    def test_exact_limit_not_truncated(self) -> None:
        text = "a" * 100
        result = _TwoPhaseCLIHand._truncate_summary(text, limit=100)
        assert result == text
        assert "[truncated]" not in result

    def test_over_limit_truncated(self) -> None:
        text = "a" * 200
        result = _TwoPhaseCLIHand._truncate_summary(text, limit=100)
        assert result.startswith("a" * 100)
        assert result.endswith("...[truncated]")

    def test_empty_text_returns_empty(self) -> None:
        result = _TwoPhaseCLIHand._truncate_summary("", limit=100)
        assert result == ""

    def test_whitespace_only_returns_empty(self) -> None:
        result = _TwoPhaseCLIHand._truncate_summary("   ", limit=100)
        assert result == ""
