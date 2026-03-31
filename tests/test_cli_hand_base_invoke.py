"""Tests for _TwoPhaseCLIHand._invoke_cli_with_cmd subprocess lifecycle.

_invoke_cli_with_cmd is the async subprocess driver at the heart of every CLI
hand: it spawns the external process, streams stdout, enforces idle timeouts,
handles interrupts, and maps exit codes to structured errors. Regressions here
affect every CLI backend (Claude Code, Codex, Gemini, Goose, Devin, OpenCode).
Critical invariants: FileNotFoundError triggers the npx fallback before raising
to the user; idle timeout terminates the process rather than hanging forever;
interrupt signals cleanly cancel the running process; non-zero exit codes with
a retry hook use the adjusted command on retry but refuse to loop if the retry
produces the same command.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub subclass
# ---------------------------------------------------------------------------
# Import after stdlib/third-party
from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand


class _Stub(_TwoPhaseCLIHand):
    """Minimal subclass that bypasses __init__ for isolated method tests."""

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


def _run(coro):
    return asyncio.run(coro)


def _noop_emit():
    async def _emit(chunk: str) -> None:
        pass

    return _emit


def _collecting_emit():
    chunks: list[str] = []

    async def _emit(chunk: str) -> None:
        chunks.append(chunk)

    return _emit, chunks


# ===================================================================
# _invoke_cli_with_cmd — FileNotFoundError without fallback
# ===================================================================


class TestInvokeCmdFileNotFoundNoFallback:
    def test_raises_runtime_error(self) -> None:
        stub = _Stub()
        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("not found"),
            ),
            pytest.raises(RuntimeError, match="command not found"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["nonexistent-cli", "--arg"],
                    emit=_noop_emit(),
                )
            )

    def test_error_message_includes_command_name(self) -> None:
        stub = _Stub()
        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("not found"),
            ),
            pytest.raises(RuntimeError, match="nonexistent-cli"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["nonexistent-cli"],
                    emit=_noop_emit(),
                )
            )


# ===================================================================
# _invoke_cli_with_cmd — FileNotFoundError with fallback
# ===================================================================


class TestInvokeCmdFileNotFoundWithFallback:
    def test_retries_with_fallback_command(self) -> None:
        stub = _Stub()
        emit, chunks = _collecting_emit()

        # First call raises FileNotFoundError, second succeeds
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout = AsyncMock()
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        call_count = 0

        async def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("not found")
            return mock_process

        with (
            patch("asyncio.create_subprocess_exec", side_effect=_side_effect),
            patch.object(
                stub,
                "_fallback_command_when_not_found",
                return_value=["alt-cli", "--arg"],
            ),
        ):
            _run(stub._invoke_cli_with_cmd(["orig-cli", "--arg"], emit=emit))

        # Should emit retry message
        assert any("not found" in c and "retrying" in c for c in chunks)

    def test_npx_fallback_emits_npx_message(self) -> None:
        stub = _Stub()
        emit, chunks = _collecting_emit()

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.stdout = AsyncMock()
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        call_count = 0

        async def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("not found")
            return mock_process

        with (
            patch("asyncio.create_subprocess_exec", side_effect=_side_effect),
            patch.object(
                stub,
                "_fallback_command_when_not_found",
                return_value=["npx", "@some/package", "--arg"],
            ),
        ):
            _run(stub._invoke_cli_with_cmd(["orig-cli", "--arg"], emit=emit))

        # Should emit the npx download message
        assert any("npx fallback" in c for c in chunks)

    def test_fallback_same_as_original_raises(self) -> None:
        stub = _Stub()
        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("not found"),
            ),
            patch.object(
                stub,
                "_fallback_command_when_not_found",
                return_value=["orig-cli", "--arg"],
            ),
            pytest.raises(RuntimeError, match="command not found"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["orig-cli", "--arg"],
                    emit=_noop_emit(),
                )
            )


# ===================================================================
# _invoke_cli_with_cmd — stdout is None
# ===================================================================


class TestInvokeCmdStdoutNone:
    def test_raises_runtime_error(self) -> None:
        stub = _Stub()
        mock_process = AsyncMock()
        mock_process.stdout = None
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.returncode = None

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            pytest.raises(RuntimeError, match="did not expose stdout"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["some-cli"],
                    emit=_noop_emit(),
                )
            )


# ===================================================================
# _invoke_cli_with_cmd — non-zero return code without retry
# ===================================================================


class TestInvokeCmdNonZeroNoRetry:
    def test_raises_runtime_error(self) -> None:
        stub = _Stub()
        mock_stdout = AsyncMock()
        mock_process = AsyncMock()
        mock_process.stdout = mock_stdout
        mock_process.returncode = None
        mock_process.wait = AsyncMock(return_value=1)

        read_count = 0

        async def _read(n):
            nonlocal read_count
            read_count += 1
            if read_count == 1:
                return b"error output here"
            # Signal end of output
            mock_process.returncode = 1
            return b""

        mock_stdout.read = _read

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            pytest.raises(RuntimeError, match=r"failed.*exit=1"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["some-cli"],
                    emit=_noop_emit(),
                )
            )


# ===================================================================
# _invoke_cli_with_cmd — non-zero return code with retry
# ===================================================================


class TestInvokeCmdNonZeroWithRetry:
    def test_retries_with_adjusted_command(self) -> None:
        stub = _Stub()
        emit, chunks = _collecting_emit()

        call_count = 0

        def _make_process(*, return_code):
            mock_stdout = MagicMock()
            read_done = False

            async def _read(n):
                nonlocal read_done
                if not read_done:
                    read_done = True
                    return b"output"
                return b""

            mock_stdout.read = _read
            proc = MagicMock()
            proc.stdout = mock_stdout
            proc.returncode = None

            async def _wait():
                proc.returncode = return_code
                return return_code

            proc.wait = _wait
            return proc

        async def _create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_process(return_code=1)
            return _make_process(return_code=0)

        with (
            patch("asyncio.create_subprocess_exec", side_effect=_create_subprocess),
            patch.object(
                stub,
                "_retry_command_after_failure",
                return_value=["some-cli", "--fixed-arg"],
            ),
        ):
            _run(stub._invoke_cli_with_cmd(["some-cli", "--arg"], emit=emit))

        assert any("retrying" in c for c in chunks)
        assert call_count == 2

    def test_retry_same_as_original_raises(self) -> None:
        stub = _Stub()

        async def _read(n):
            return b""

        mock_stdout = MagicMock()
        mock_stdout.read = _read
        proc = MagicMock()
        proc.stdout = mock_stdout
        proc.returncode = None

        async def _wait():
            proc.returncode = 1
            return 1

        proc.wait = _wait

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch.object(
                stub,
                "_retry_command_after_failure",
                return_value=["some-cli", "--arg"],
            ),
            pytest.raises(RuntimeError, match=r"failed.*exit=1"),
        ):
            _run(
                stub._invoke_cli_with_cmd(
                    ["some-cli", "--arg"],
                    emit=_noop_emit(),
                )
            )


# ===================================================================
# _invoke_cli_with_cmd — idle timeout
# ===================================================================


class TestInvokeCmdIdleTimeout:
    def test_terminates_on_idle_timeout(self) -> None:
        stub = _Stub()
        # Set very short idle timeout
        with (
            patch.object(stub, "_io_poll_seconds", return_value=0.01),
            patch.object(stub, "_heartbeat_seconds", return_value=0.005),
            patch.object(stub, "_idle_timeout_seconds", return_value=0.02),
        ):
            mock_stdout = MagicMock()

            async def _read_timeout(n):
                await asyncio.sleep(0.1)
                return b""

            mock_stdout.read = _read_timeout
            proc = MagicMock()
            proc.stdout = mock_stdout
            proc.returncode = None

            async def _wait():
                return 0

            proc.wait = _wait

            with (
                patch("asyncio.create_subprocess_exec", return_value=proc),
                patch.object(stub, "_terminate_active_process", new=AsyncMock()),
                pytest.raises(RuntimeError, match="no output"),
            ):
                _run(
                    stub._invoke_cli_with_cmd(
                        ["some-cli"],
                        emit=_noop_emit(),
                    )
                )


# ===================================================================
# _invoke_cli_with_cmd — verbose mode
# ===================================================================


class TestInvokeCmdVerbose:
    def test_verbose_emits_cmd_and_cwd(self) -> None:
        stub = _Stub()
        stub.config.verbose = True
        emit, chunks = _collecting_emit()

        async def _read(n):
            return b""

        mock_stdout = MagicMock()
        mock_stdout.read = _read
        proc = MagicMock()
        proc.stdout = mock_stdout
        proc.returncode = None

        async def _wait():
            proc.returncode = 0
            return 0

        proc.wait = _wait

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            _run(stub._invoke_cli_with_cmd(["some-cli", "--arg"], emit=emit))

        assert any("cmd:" in c for c in chunks)
        assert any("cwd:" in c for c in chunks)
        assert any("finished in" in c for c in chunks)


# ===================================================================
# _invoke_cli — delegates to _invoke_cli_with_cmd via _render_command
# ===================================================================


class TestInvokeCli:
    def test_delegates_to_invoke_cli_with_cmd(self) -> None:
        stub = _Stub()
        captured_cmds: list[list[str]] = []

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            captured_cmds.append(cmd)
            return "result from cli"

        stub._invoke_cli_with_cmd = fake_invoke_cli_with_cmd
        stub._render_command = lambda prompt: ["stub-cli", "-p", prompt]

        result = _run(stub._invoke_cli("do something", emit=_noop_emit()))
        assert result == "result from cli"
        assert captured_cmds == [["stub-cli", "-p", "do something"]]


# ===================================================================
# _invoke_backend — delegates to _invoke_cli
# ===================================================================


class TestInvokeBackend:
    def test_delegates_to_invoke_cli(self) -> None:
        stub = _Stub()
        calls: list[str] = []

        async def fake_invoke_cli(prompt, *, emit):
            calls.append(prompt)
            return "delegated"

        stub._invoke_cli = fake_invoke_cli

        async def emit(text: str) -> None:
            pass

        result = _run(stub._invoke_backend("hello", emit=emit))
        assert result == "delegated"
        assert calls == ["hello"]


# ===================================================================
# _run_two_phase_inner — verbose mode branches
# ===================================================================


class TestRunTwoPhaseInnerVerbose:
    @staticmethod
    def _make_stub(*, verbose: bool = True):
        stub = _Stub()
        stub.config.verbose = verbose
        stub.config.model = "gpt-5"
        stub.auto_pr = False
        stub._build_init_prompt = lambda: "init"
        stub._build_task_prompt = lambda prompt, learned_summary: "task"
        stub._should_retry_without_changes = lambda prompt: False
        stub._is_interrupted = lambda: False
        return stub

    def test_verbose_emits_model_heartbeat_and_phase_timings(self) -> None:
        stub = self._make_stub(verbose=True)
        emit, chunks = _collecting_emit()

        call_count = 0

        async def fake_invoke_backend(prompt, *, emit):
            nonlocal call_count
            call_count += 1
            return f"output{call_count}"

        stub._invoke_backend = fake_invoke_backend
        stub._describe_auth = lambda: "key set"
        stub._resolve_cli_model = lambda: "gpt-5"

        _run(stub._run_two_phase_inner("task", emit=emit))

        joined = "".join(chunks)
        assert "model=gpt-5" in joined
        assert "heartbeat=" in joined
        assert "idle_timeout=" in joined
        assert "phase 1 completed" in joined
        assert "phase 2 completed" in joined
        assert "total elapsed" in joined

    def test_verbose_auth_part_omitted_when_empty(self) -> None:
        stub = self._make_stub(verbose=False)
        emit, chunks = _collecting_emit()

        call_count = 0

        async def fake_invoke_backend(prompt, *, emit):
            nonlocal call_count
            call_count += 1
            return f"output{call_count}"

        stub._invoke_backend = fake_invoke_backend
        stub._describe_auth = lambda: ""

        _run(stub._run_two_phase_inner("task", emit=emit))

        isolation_msgs = [c for c in chunks if "isolation=" in c]
        assert len(isolation_msgs) == 1
        # No auth part appended when _describe_auth returns empty
        assert " | key" not in isolation_msgs[0]

    def test_verbose_default_model_when_resolve_returns_none(self) -> None:
        stub = self._make_stub(verbose=True)
        emit, chunks = _collecting_emit()

        call_count = 0

        async def fake_invoke_backend(prompt, *, emit):
            nonlocal call_count
            call_count += 1
            return f"output{call_count}"

        stub._invoke_backend = fake_invoke_backend
        stub._describe_auth = lambda: ""
        stub._resolve_cli_model = lambda: None

        _run(stub._run_two_phase_inner("task", emit=emit))

        joined = "".join(chunks)
        assert "model=(default)" in joined

    def test_auth_part_included_when_non_empty(self) -> None:
        stub = self._make_stub(verbose=False)
        emit, chunks = _collecting_emit()

        async def fake_invoke_backend(prompt, *, emit):
            return "done"

        stub._invoke_backend = fake_invoke_backend
        stub._describe_auth = lambda: "API key set"

        _run(stub._run_two_phase_inner("task", emit=emit))

        isolation_msgs = [c for c in chunks if "isolation=" in c]
        assert len(isolation_msgs) == 1
        assert "API key set" in isolation_msgs[0]


# ===================================================================
# _invoke_cli_with_cmd — interrupt during IO loop (lines 538-540)
# ===================================================================


class TestInvokeCmdInterruptDuringIOLoop:
    def test_interrupt_breaks_io_loop(self) -> None:
        """When _is_interrupted() returns True during the IO loop,
        the loop breaks after calling _terminate_active_process."""
        stub = _Stub()
        emit, chunks = _collecting_emit()

        mock_stdout = MagicMock()
        read_count = 0

        async def _read(n):
            nonlocal read_count
            read_count += 1
            if read_count == 1:
                return b"first chunk"
            # After first read, the interrupt should fire
            return b"second chunk"

        mock_stdout.read = _read
        proc = MagicMock()
        proc.stdout = mock_stdout
        proc.returncode = None

        async def _wait():
            proc.returncode = 0
            return 0

        proc.wait = _wait

        # _is_interrupted returns False first (for first read), then True
        call_count = 0

        def _is_interrupted_toggle():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # True on second call

        stub._is_interrupted = _is_interrupted_toggle
        terminate_mock = AsyncMock()

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch.object(stub, "_terminate_active_process", terminate_mock),
        ):
            _run(stub._invoke_cli_with_cmd(["some-cli"], emit=emit))

        # Only the first chunk should be in the output (loop broke on interrupt)
        combined = "".join(chunks)
        assert "first chunk" in combined
        terminate_mock.assert_awaited_once()


# ===================================================================
# _invoke_cli_with_cmd — process.returncode set during TimeoutError
# ===================================================================


class TestInvokeCmdProcessExitedDuringTimeout:
    def test_breaks_when_process_already_exited(self) -> None:
        """When asyncio.wait_for raises TimeoutError but process.returncode
        is already set, the loop breaks immediately (line 549)."""
        stub = _Stub()
        emit, _chunks = _collecting_emit()

        mock_stdout = MagicMock()

        async def _read(n):
            raise TimeoutError()

        mock_stdout.read = _read
        proc = MagicMock()
        proc.stdout = mock_stdout
        # process has already exited (returncode set)
        proc.returncode = 0

        async def _wait():
            return 0

        proc.wait = _wait

        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = _run(stub._invoke_cli_with_cmd(["some-cli"], emit=emit))

        # Should return empty string (no output collected) without error
        assert result == ""
