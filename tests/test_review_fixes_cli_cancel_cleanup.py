"""Tests that CLI subprocesses are cleaned up on cancellation.

``_invoke_cli_with_cmd`` spawns an external process and streams its stdout. If
the coroutine is cancelled (e.g. the enclosing task is aborted) before the
process exits normally, the child must be terminated rather than orphaned, and
``CancelledError`` must still propagate.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


class _Stub(_TwoPhaseCLIHand):
    """Minimal subclass bypassing __init__ for isolated method tests."""

    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _BACKEND_NAME = "stub-backend"
    _COMMAND_ENV_VAR = "STUB_CLI_COMMAND"

    def __init__(self) -> None:
        self._interrupt_event = MagicMock()
        self._interrupt_event.is_set.return_value = False
        self._active_process = None
        self.repo_index = MagicMock()
        self.repo_index.root.resolve.return_value = "/fake/repo"
        self.config = MagicMock()
        self.config.model = "test-model"
        self.config.verbose = False
        self._ci_fix_mode = False


class _FakeProcess:
    """A subprocess double whose stdout.read hangs until terminated."""

    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminate_called = False
        self.kill_called = False
        self._done = asyncio.Event()

        async def _read(_n: int) -> bytes:
            # Block forever until terminate() flips the event.
            await self._done.wait()
            return b""

        self.stdout = MagicMock()
        self.stdout.read = _read

    def terminate(self) -> None:
        self.terminate_called = True
        self.returncode = -15
        self._done.set()

    def kill(self) -> None:
        self.kill_called = True
        self.returncode = -9
        self._done.set()

    async def wait(self) -> int:
        await self._done.wait()
        return self.returncode if self.returncode is not None else 0


async def _noop_emit(chunk: str) -> None:
    pass


def test_cancellation_terminates_child_and_reraises() -> None:
    proc = _FakeProcess()
    stub = _Stub()

    async def _scenario() -> None:
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            task = asyncio.create_task(
                stub._invoke_cli_with_cmd(["some-cli"], emit=_noop_emit)
            )
            # Let the task start and block on stdout.read.
            await asyncio.sleep(0.05)
            assert stub._active_process is proc
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(_scenario())

    # The child was terminated (not left running) and state was cleared.
    assert proc.terminate_called
    assert stub._active_process is None


def test_normal_completion_does_not_terminate() -> None:
    """On a clean exit the process is awaited, not force-terminated."""
    stub = _Stub()

    proc = MagicMock()
    proc.returncode = 0

    async def _read(_n: int) -> bytes:
        return b""  # immediate EOF -> normal completion

    proc.stdout = MagicMock()
    proc.stdout.read = _read

    async def _wait() -> int:
        return 0

    proc.wait = _wait

    async def _scenario() -> str:
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            return await stub._invoke_cli_with_cmd(["some-cli"], emit=_noop_emit)

    result = asyncio.run(_scenario())

    assert result == ""
    # returncode was already 0, so _terminate_active_process is a no-op:
    # terminate() must never have been called on a cleanly-finished process.
    proc.terminate.assert_not_called()
    assert stub._active_process is None
