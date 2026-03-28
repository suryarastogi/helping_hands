"""Tests for _TwoPhaseCLIHand retry, apply-changes, and interrupt helpers.

_should_retry_without_changes guards the no-change retry loop: it only triggers
a second backend invocation when (a) the feature flag is on, (b) the prompt
looks like an edit request, (c) no interrupt was received, and (d) the repo
truly has no changes. A bug in any of those four conditions causes either wasted
retries on read-only prompts or missed retries on real edit tasks. The
_terminate_active_process logic ensures that an interrupt (or idle timeout)
escalates from SIGTERM to SIGKILL when the process does not exit promptly —
critical to prevent zombie subprocesses on long-running server deployments.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Stub subclass — minimal concrete impl for instance method testing
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    """Minimal subclass that bypasses __init__ for isolated method tests."""

    _CLI_LABEL = "stub"
    _RETRY_ON_NO_CHANGES = True

    def __init__(self) -> None:
        # Skip parent __init__ — we only need the methods under test.
        self._interrupt_event = MagicMock()
        self._active_process = None


class _StubRetryDisabled(_Stub):
    _RETRY_ON_NO_CHANGES = False


# ===================================================================
# _should_retry_without_changes
# ===================================================================


class TestShouldRetryWithoutChanges:
    """Exercises all four exit branches of _should_retry_without_changes."""

    def test_returns_false_when_feature_disabled(self) -> None:
        stub = _StubRetryDisabled()
        assert stub._should_retry_without_changes("fix the bug") is False

    def test_returns_false_when_interrupted(self) -> None:
        stub = _Stub()
        stub._interrupt_event.is_set.return_value = True
        assert stub._should_retry_without_changes("fix the bug") is False

    def test_returns_false_when_not_edit_request(self) -> None:
        stub = _Stub()
        stub._interrupt_event.is_set.return_value = False
        # "explain" is not an action verb
        assert stub._should_retry_without_changes("explain the code") is False

    def test_returns_false_when_repo_has_changes(self) -> None:
        stub = _Stub()
        stub._interrupt_event.is_set.return_value = False
        with patch.object(stub, "_repo_has_changes", return_value=True):
            assert stub._should_retry_without_changes("fix the bug") is False

    def test_returns_true_when_all_conditions_met(self) -> None:
        stub = _Stub()
        stub._interrupt_event.is_set.return_value = False
        with patch.object(stub, "_repo_has_changes", return_value=False):
            assert stub._should_retry_without_changes("fix the bug") is True


# ===================================================================
# _no_change_error_after_retries
# ===================================================================


class TestNoChangeErrorAfterRetries:
    def test_base_returns_none(self) -> None:
        stub = _Stub()
        result = stub._no_change_error_after_retries(
            prompt="add tests", combined_output="some output"
        )
        assert result is None


# ===================================================================
# _build_apply_changes_prompt
# ===================================================================


class TestBuildApplyChangesPrompt:
    def test_includes_prompt_and_output(self) -> None:
        result = _Stub()._build_apply_changes_prompt(
            prompt="add a login page", task_output="Here is the plan..."
        )
        assert "add a login page" in result
        assert "Here is the plan..." in result
        assert "Follow-up enforcement" in result

    def test_empty_output_shows_none(self) -> None:
        result = _Stub()._build_apply_changes_prompt(prompt="task", task_output="")
        assert "(none)" in result

    def test_long_output_truncated(self) -> None:
        long_output = "x" * 5000
        result = _Stub()._build_apply_changes_prompt(
            prompt="task", task_output=long_output
        )
        assert "[truncated]" in result


# ===================================================================
# _terminate_active_process
# ===================================================================


class TestTerminateActiveProcess:
    def test_no_process_is_noop(self) -> None:
        stub = _Stub()
        stub._active_process = None
        asyncio.run(stub._terminate_active_process())

    def test_already_exited_is_noop(self) -> None:
        stub = _Stub()
        proc = MagicMock()
        proc.returncode = 0
        stub._active_process = proc
        asyncio.run(stub._terminate_active_process())
        proc.terminate.assert_not_called()

    def test_terminate_on_active_process(self) -> None:
        stub = _Stub()
        proc = MagicMock()
        proc.returncode = None
        proc.wait = AsyncMock()
        stub._active_process = proc
        asyncio.run(stub._terminate_active_process())
        proc.terminate.assert_called_once()

    def test_kill_on_timeout(self) -> None:
        stub = _Stub()
        proc = MagicMock()
        proc.returncode = None
        call_count = 0

        async def _wait_side_effect() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError
            return None

        proc.wait = AsyncMock(side_effect=_wait_side_effect)
        stub._active_process = proc
        asyncio.run(stub._terminate_active_process())
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()


# ===================================================================
# interrupt()
# ===================================================================


class TestInterrupt:
    def test_terminates_active_process(self) -> None:
        stub = _Stub()
        proc = MagicMock()
        proc.returncode = None
        stub._active_process = proc
        with patch.object(_TwoPhaseCLIHand.__bases__[0], "interrupt"):
            stub.interrupt()
        proc.terminate.assert_called_once()

    def test_skips_when_no_process(self) -> None:
        stub = _Stub()
        stub._active_process = None
        with patch.object(_TwoPhaseCLIHand.__bases__[0], "interrupt"):
            stub.interrupt()
        # No exception raised — no-op

    def test_skips_when_process_already_exited(self) -> None:
        stub = _Stub()
        proc = MagicMock()
        proc.returncode = 0
        stub._active_process = proc
        with patch.object(_TwoPhaseCLIHand.__bases__[0], "interrupt"):
            stub.interrupt()
        proc.terminate.assert_not_called()
