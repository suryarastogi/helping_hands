"""Tests for _TwoPhaseCLIHand _ci_fix_loop, _poll_ci_checks, run(), and stream()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Stub subclass
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    """Minimal subclass that bypasses __init__ for isolated method tests."""

    _CLI_LABEL = "stub"
    _BACKEND_NAME = "stub-backend"

    def __init__(self, *, fix_ci: bool = False) -> None:
        self._interrupt_event = MagicMock()
        self._interrupt_event.is_set.return_value = False
        self._active_process = None
        self.fix_ci = fix_ci
        self.ci_check_wait_minutes = 0.001  # near-instant for tests
        self.ci_max_retries = 2
        self.repo_index = MagicMock()
        self.repo_index.root.resolve.return_value = "/fake/repo"
        self.config = MagicMock()
        self.config.model = "test-model"
        self.config.verbose = False
        self.auto_pr = True


def _run(coro):
    """Helper to run an async coroutine synchronously."""
    return asyncio.run(coro)


def _noop_emit():
    """Return an async no-op emitter."""

    async def _emit(chunk: str) -> None:
        pass

    return _emit


def _collecting_emit():
    """Return an emitter that collects chunks and the chunk list."""
    chunks: list[str] = []

    async def _emit(chunk: str) -> None:
        chunks.append(chunk)

    return _emit, chunks


# ===================================================================
# _ci_fix_loop — early returns
# ===================================================================


class TestCiFixLoopEarlyReturns:
    def test_fix_ci_disabled_returns_unchanged(self) -> None:
        stub = _Stub(fix_ci=False)
        meta = {"pr_status": "created", "pr_commit": "abc", "pr_branch": "b"}
        result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit()))
        assert result is meta

    def test_pr_status_not_created_or_updated(self) -> None:
        stub = _Stub(fix_ci=True)
        meta = {"pr_status": "disabled"}
        result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit()))
        assert result is meta

    def test_missing_pr_commit(self) -> None:
        stub = _Stub(fix_ci=True)
        meta = {"pr_status": "created", "pr_branch": "b"}
        result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit()))
        assert result is meta

    def test_missing_pr_branch(self) -> None:
        stub = _Stub(fix_ci=True)
        meta = {"pr_status": "created", "pr_commit": "abc"}
        result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit()))
        assert result is meta

    def test_no_github_repo(self) -> None:
        stub = _Stub(fix_ci=True)
        meta = {"pr_status": "created", "pr_commit": "abc", "pr_branch": "b"}
        with patch.object(
            _TwoPhaseCLIHand, "_github_repo_from_origin", return_value=None
        ):
            result = _run(
                stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit())
            )
        assert result is meta


# ===================================================================
# _ci_fix_loop — CI conclusion paths
# ===================================================================


class TestCiFixLoopConclusions:
    def _base_meta(self) -> dict[str, str]:
        return {"pr_status": "created", "pr_commit": "abc123", "pr_branch": "fix/ci"}

    def _run_loop(self, stub, poll_result):
        meta = self._base_meta()
        emit, chunks = _collecting_emit()
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(
                stub, "_poll_ci_checks", new=AsyncMock(return_value=poll_result)
            ),
        ):
            result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=emit))
        return result, chunks

    def test_ci_success(self) -> None:
        stub = _Stub(fix_ci=True)
        result, _ = self._run_loop(
            stub, {"conclusion": "success", "total_count": 3, "check_runs": []}
        )
        assert result["ci_fix_status"] == "success"

    def test_ci_no_checks(self) -> None:
        stub = _Stub(fix_ci=True)
        result, _ = self._run_loop(
            stub, {"conclusion": "no_checks", "total_count": 0, "check_runs": []}
        )
        assert result["ci_fix_status"] == "no_checks"

    def test_ci_pending_timeout(self) -> None:
        stub = _Stub(fix_ci=True)
        result, _ = self._run_loop(
            stub, {"conclusion": "pending", "total_count": 1, "check_runs": []}
        )
        assert result["ci_fix_status"] == "pending_timeout"

    def test_ci_failure_fix_no_changes(self) -> None:
        """CI fails, backend fix produces no changes -> continues to exhaustion."""
        stub = _Stub(fix_ci=True)
        meta = self._base_meta()
        emit, _chunks = _collecting_emit()
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        poll_result = {
            "conclusion": "failure",
            "total_count": 1,
            "check_runs": [{"name": "lint", "conclusion": "failure", "html_url": ""}],
        }

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(
                stub, "_poll_ci_checks", new=AsyncMock(return_value=poll_result)
            ),
            patch.object(stub, "_invoke_backend", new=AsyncMock(return_value="")),
            patch.object(stub, "_repo_has_changes", return_value=False),
        ):
            result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=emit))
        assert result["ci_fix_status"] == "exhausted"
        assert result["ci_fix_attempts"] == "2"

    def test_ci_failure_fix_with_changes_then_success(self) -> None:
        """CI fails, fix produces changes, push, then CI passes on next poll."""
        stub = _Stub(fix_ci=True)
        stub.ci_max_retries = 2
        meta = self._base_meta()
        emit, _chunks = _collecting_emit()
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        # First poll returns failure, second returns success
        poll_results = [
            {
                "conclusion": "failure",
                "total_count": 1,
                "check_runs": [
                    {"name": "test", "conclusion": "failure", "html_url": ""}
                ],
            },
            {"conclusion": "success", "total_count": 1, "check_runs": []},
        ]
        poll_mock = AsyncMock(side_effect=poll_results)

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(stub, "_poll_ci_checks", new=poll_mock),
            patch.object(stub, "_invoke_backend", new=AsyncMock(return_value="")),
            patch.object(stub, "_repo_has_changes", return_value=True),
            patch.object(_TwoPhaseCLIHand, "_push_noninteractive", return_value=None),
        ):
            mock_gh.add_and_commit = MagicMock(return_value="newsha123")
            result = _run(stub._ci_fix_loop(prompt="p", metadata=meta, emit=emit))
        assert result["ci_fix_status"] == "success"
        assert result["ci_fix_attempts"] == "1"
        assert result["pr_commit"] == "newsha123"


class TestCiFixLoopInterrupt:
    def test_interrupted_before_first_poll(self) -> None:
        stub = _Stub(fix_ci=True)
        stub._interrupt_event.is_set.return_value = True
        meta = {"pr_status": "created", "pr_commit": "abc", "pr_branch": "b"}
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
        ):
            result = _run(
                stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit())
            )
        assert result["ci_fix_status"] == "interrupted"

    def test_interrupted_after_fix(self) -> None:
        stub = _Stub(fix_ci=True)
        call_count = 0

        def _is_interrupted():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # interrupted after first poll

        stub._interrupt_event.is_set = _is_interrupted
        meta = {"pr_status": "created", "pr_commit": "abc", "pr_branch": "b"}
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)
        poll_result = {
            "conclusion": "failure",
            "total_count": 1,
            "check_runs": [],
        }

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(
                stub, "_poll_ci_checks", new=AsyncMock(return_value=poll_result)
            ),
            patch.object(stub, "_invoke_backend", new=AsyncMock(return_value="")),
        ):
            result = _run(
                stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit())
            )
        assert result["ci_fix_status"] == "interrupted"


class TestCiFixLoopException:
    def test_exception_sets_error_status(self) -> None:
        stub = _Stub(fix_ci=True)
        meta = {"pr_status": "updated", "pr_commit": "abc", "pr_branch": "b"}
        mock_gh = MagicMock()
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=mock_gh,
            ),
            patch.object(
                stub,
                "_poll_ci_checks",
                new=AsyncMock(side_effect=RuntimeError("network error")),
            ),
        ):
            result = _run(
                stub._ci_fix_loop(prompt="p", metadata=meta, emit=_noop_emit())
            )
        assert result["ci_fix_status"] == "error"
        assert "network error" in result["ci_fix_error"]


# ===================================================================
# _poll_ci_checks
# ===================================================================


class TestPollCiChecks:
    def test_returns_immediately_on_non_pending(self) -> None:
        stub = _Stub()
        mock_gh = MagicMock()
        mock_gh.get_check_runs.return_value = {
            "conclusion": "success",
            "total_count": 2,
        }
        emit = _noop_emit()
        result = _run(
            stub._poll_ci_checks(
                gh=mock_gh,
                repo="owner/repo",
                ref="abc123",
                emit=emit,
                initial_wait=0.001,
                max_poll_seconds=0.001,
            )
        )
        assert result["conclusion"] == "success"
        mock_gh.get_check_runs.assert_called_once()

    def test_polls_until_deadline_then_returns_final(self) -> None:
        stub = _Stub()
        mock_gh = MagicMock()
        mock_gh.get_check_runs.return_value = {
            "conclusion": "pending",
            "total_count": 1,
        }
        emit = _noop_emit()
        result = _run(
            stub._poll_ci_checks(
                gh=mock_gh,
                repo="owner/repo",
                ref="abc123",
                emit=emit,
                initial_wait=0.001,
                max_poll_seconds=0.001,
            )
        )
        assert result["conclusion"] == "pending"


# ===================================================================
# run() and stream() wrappers
# ===================================================================


class TestRunWrapper:
    def test_run_collects_output_and_finalizes(self) -> None:
        stub = _Stub(fix_ci=False)

        async def _fake_collect(prompt):
            return "collected output"

        with (
            patch.object(stub, "_collect_run_output", side_effect=_fake_collect),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
        ):
            response = stub.run("add tests")

        assert response.message == "collected output"
        assert response.metadata["backend"] == "stub-backend"
        assert response.metadata["pr_url"] == "https://pr/1"

    def test_run_with_ci_fix(self) -> None:
        stub = _Stub(fix_ci=True)

        async def _fake_collect(prompt):
            return "output"

        with (
            patch.object(stub, "_collect_run_output", side_effect=_fake_collect),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
            patch.object(
                stub,
                "_ci_fix_loop",
                new=AsyncMock(
                    return_value={
                        "pr_status": "created",
                        "pr_url": "https://pr/1",
                        "ci_fix_status": "success",
                    }
                ),
            ),
        ):
            response = stub.run("fix bug")

        assert response.metadata.get("ci_fix_status") == "success"

    def test_run_ci_fix_noop_emit_is_callable(self) -> None:
        """The _noop_emit closure inside run() is a valid async callable
        that silently discards chunks (covering line 985)."""
        stub = _Stub(fix_ci=True)

        async def _fake_collect(prompt):
            return "output"

        async def _ci_fix_that_calls_emit(*, prompt, metadata, emit):
            # Call the noop emit to cover the inner closure
            await emit("ci output that is discarded")
            return {
                "pr_status": "created",
                "pr_url": "https://pr/1",
                "ci_fix_status": "success",
            }

        with (
            patch.object(stub, "_collect_run_output", side_effect=_fake_collect),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
            patch.object(stub, "_ci_fix_loop", side_effect=_ci_fix_that_calls_emit),
        ):
            response = stub.run("fix bug")

        assert response.metadata.get("ci_fix_status") == "success"

    def test_run_no_ci_fix_when_pr_not_created(self) -> None:
        stub = _Stub(fix_ci=True)

        async def _fake_collect(prompt):
            return "output"

        with (
            patch.object(stub, "_collect_run_output", side_effect=_fake_collect),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "no_changes"},
            ),
        ):
            response = stub.run("explain code")

        assert "ci_fix_status" not in response.metadata


class TestStreamWrapper:
    def test_stream_yields_chunks_and_finalizes(self) -> None:
        stub = _Stub(fix_ci=False)

        async def _fake_two_phase(prompt, *, emit):
            await emit("chunk1")
            await emit("chunk2")
            return "chunk1chunk2"

        with (
            patch.object(stub, "_run_two_phase", side_effect=_fake_two_phase),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
            patch.object(
                stub,
                "_ci_fix_loop",
                new=AsyncMock(
                    return_value={"pr_status": "created", "pr_url": "https://pr/1"}
                ),
            ),
            patch.object(stub, "_format_ci_fix_message", return_value=None),
        ):

            async def _collect():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                return chunks

            chunks = _run(_collect())

        assert "chunk1" in chunks
        assert "chunk2" in chunks
        # PR status message should be yielded
        pr_msgs = [c for c in chunks if "PR created" in c]
        assert len(pr_msgs) == 1

    def test_stream_yields_ci_fix_message(self) -> None:
        stub = _Stub(fix_ci=True)

        async def _fake_two_phase(prompt, *, emit):
            await emit("work")
            return "work"

        with (
            patch.object(stub, "_run_two_phase", side_effect=_fake_two_phase),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
            patch.object(
                stub,
                "_ci_fix_loop",
                new=AsyncMock(
                    return_value={
                        "pr_status": "created",
                        "pr_url": "https://pr/1",
                        "ci_fix_status": "success",
                    }
                ),
            ),
        ):

            async def _collect():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                return chunks

            chunks = _run(_collect())

        joined = "".join(chunks)
        assert "CI checks passed" in joined

    def test_stream_no_pr_status_message_when_none(self) -> None:
        stub = _Stub(fix_ci=False)

        async def _fake_two_phase(prompt, *, emit):
            await emit("output")
            return "output"

        with (
            patch.object(stub, "_run_two_phase", side_effect=_fake_two_phase),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": ""},
            ),
            patch.object(
                stub,
                "_ci_fix_loop",
                new=AsyncMock(return_value={"pr_status": ""}),
            ),
            patch.object(stub, "_format_ci_fix_message", return_value=None),
        ):

            async def _collect():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                return chunks

            chunks = _run(_collect())

        # Only the original emitted chunk — no PR status or CI fix messages
        assert chunks == ["output"]

    def test_stream_ci_fix_exhausted_message(self) -> None:
        stub = _Stub(fix_ci=True)

        async def _fake_two_phase(prompt, *, emit):
            await emit("done")
            return "done"

        with (
            patch.object(stub, "_run_two_phase", side_effect=_fake_two_phase),
            patch.object(
                stub,
                "_finalize_after_run",
                return_value={"pr_status": "created", "pr_url": "https://pr/1"},
            ),
            patch.object(
                stub,
                "_ci_fix_loop",
                new=AsyncMock(
                    return_value={
                        "pr_status": "created",
                        "pr_url": "https://pr/1",
                        "ci_fix_status": "exhausted",
                        "ci_fix_attempts": "2",
                    }
                ),
            ),
        ):

            async def _collect():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                return chunks

            chunks = _run(_collect())

        joined = "".join(chunks)
        assert "CI fix failed after 2 attempt(s)" in joined

    def test_stream_producer_error_re_raised(self) -> None:
        stub = _Stub(fix_ci=False)

        async def _fake_two_phase(prompt, *, emit):
            await emit("partial")
            raise RuntimeError("producer boom")

        with (
            patch.object(stub, "_run_two_phase", side_effect=_fake_two_phase),
        ):

            async def _collect():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                return chunks

            with pytest.raises(RuntimeError, match="producer boom"):
                _run(_collect())

    def test_stream_consumer_break_cancels_producer(self) -> None:
        """When consumer breaks early, the producer task is cancelled cleanly."""
        stub = _Stub(fix_ci=False)
        producer_started = asyncio.Event()
        producer_cancelled = False

        async def _slow_two_phase(prompt, *, emit):
            nonlocal producer_cancelled
            await emit("chunk1")
            producer_started.set()
            try:
                # Simulate a long-running producer
                await asyncio.sleep(10)
                await emit("chunk2")
            except asyncio.CancelledError:
                producer_cancelled = True
                raise

        with patch.object(stub, "_run_two_phase", side_effect=_slow_two_phase):

            async def _partial_consume():
                chunks = []
                async for chunk in stub.stream("task"):
                    chunks.append(chunk)
                    if chunk == "chunk1":
                        break  # Consumer exits early
                return chunks

            chunks = _run(_partial_consume())

        assert chunks == ["chunk1"]
        assert producer_cancelled
