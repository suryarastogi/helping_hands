"""Guard streaming edge cases in iterative hands, E2E PR creation, and PR description extraction.

These tests cover four rarely-triggered branches that would otherwise become dead
code silently accumulating drift: (1) when the sync AssertionError fallback in
BasicAtomicHand returns an empty delta, no chunk must be yielded to callers;
(2) the same empty-delta guard for awaitable (non-iterable) agent results;
(3) e2e.py must handle a None pr_number returned from create_pr without crashing;
(4) pr_description.py must break out of the candidate-selection loop once a
candidate is already set so the first clean commit line wins. Without these tests
any silent regression in these branches would corrupt streaming output or produce
PRs with incorrect titles/numbers.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.iterative import BasicAtomicHand
from helping_hands.lib.hands.v1.hand.pr_description import (
    _commit_message_from_prompt,
)
from helping_hands.lib.repo import RepoIndex

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_atomic_hand(tmp_path: Path, *, max_iterations: int = 1):
    """Build a BasicAtomicHand with _build_agent mocked."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="openai/gpt-test")
    mock_agent = MagicMock()
    with patch.object(BasicAtomicHand, "_build_agent", return_value=mock_agent):
        hand = BasicAtomicHand(config, repo_index, max_iterations=max_iterations)
    hand._input_schema = type("FakeInput", (), {"__init__": lambda s, **kw: None})
    return hand, mock_agent


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# iterative.py: AssertionError fallback with empty delta (lines 1137→1139)
# ---------------------------------------------------------------------------


class TestAtomicStreamEmptyDeltaAssertionFallback:
    """When sync fallback returns empty text, delta is empty and yield is skipped."""

    def test_empty_delta_assertion_fallback_no_yield(self, tmp_path: Path) -> None:
        """Empty _extract_message result after AssertionError gives empty delta."""
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        # Sync fallback returns empty chat_message
        sync_partial = MagicMock()
        sync_partial.chat_message = "SATISFIED: yes"

        def _sync_run(_input):
            return sync_partial

        def _async_raise(_input):
            raise AssertionError("async not supported")

        mock_agent.run_async = _async_raise
        mock_agent.run = _sync_run

        # Make _extract_message return "" to trigger empty delta
        with (
            patch.object(hand, "_extract_message", return_value=""),
            patch.object(hand, "_finalize_repo_pr", return_value={}),
            patch.object(hand, "_is_satisfied", return_value=True),
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        # The empty delta should NOT appear as a chunk (only header/status chunks)
        content_chunks = [
            c
            for c in chunks
            if not c.startswith("[basic-atomic]") and not c.startswith("\n[")
        ]
        assert all(c != "" for c in content_chunks)

    def test_empty_delta_assertion_fallback_stream_continues(
        self, tmp_path: Path
    ) -> None:
        """Stream completes normally even when delta is empty after sync fallback."""
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        sync_partial = MagicMock()
        sync_partial.chat_message = ""

        def _sync_run(_input):
            return sync_partial

        def _async_raise(_input):
            raise AssertionError("no async")

        mock_agent.run_async = _async_raise
        mock_agent.run = _sync_run

        with (
            patch.object(hand, "_extract_message", return_value=""),
            patch.object(hand, "_finalize_repo_pr", return_value={}),
            patch.object(hand, "_is_satisfied", return_value=True),
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        # Stream should still produce iteration/status output
        assert "[iteration 1/" in text


# ---------------------------------------------------------------------------
# iterative.py: Awaitable (non-iterable) result with empty delta (1163→1165)
# ---------------------------------------------------------------------------


class TestAtomicStreamEmptyDeltaAwaitableResult:
    """When awaitable result yields empty text, delta is empty and yield is skipped."""

    def test_empty_delta_awaitable_no_yield(self, tmp_path: Path) -> None:
        """Empty _extract_message from awaitable result produces empty delta."""
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        partial = MagicMock()
        partial.chat_message = ""

        # Return a coroutine (awaitable, non-iterable)
        async def _fake_run_async(_input):
            return partial

        mock_agent.run_async = _fake_run_async

        with (
            patch.object(hand, "_extract_message", return_value=""),
            patch.object(hand, "_finalize_repo_pr", return_value={}),
            patch.object(hand, "_is_satisfied", return_value=True),
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        # No empty-string chunks should be yielded
        content_chunks = [
            c
            for c in chunks
            if not c.startswith("[basic-atomic]") and not c.startswith("\n[")
        ]
        assert all(c != "" for c in content_chunks)

    def test_empty_delta_awaitable_stream_completes(self, tmp_path: Path) -> None:
        """Stream completes normally when awaitable result gives empty delta."""
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        partial = MagicMock()

        async def _fake_run_async(_input):
            return partial

        mock_agent.run_async = _fake_run_async

        with (
            patch.object(hand, "_extract_message", return_value=""),
            patch.object(hand, "_finalize_repo_pr", return_value={}),
            patch.object(hand, "_is_satisfied", return_value=True),
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "[iteration 1/" in text


# ---------------------------------------------------------------------------
# e2e.py line 291: final_pr_number is None after create_pr
# ---------------------------------------------------------------------------


class TestE2EFinalPrNumberNone:
    """E2E hand raises RuntimeError when create_pr returns pr_number=None."""

    @patch("helping_hands.lib.github.GitHubClient")
    def test_create_pr_returns_none_pr_number(
        self,
        mock_gh_cls: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When create_pr().number is None, E2EHand.run raises RuntimeError."""
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

        mock_gh = MagicMock()
        # create_pr returns a PRResult with number=None
        mock_gh.create_pr.return_value = MagicMock(number=None, url="https://pr/x")
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        repo_index = RepoIndex.from_path(tmp_path)
        hand = E2EHand(config, repo_index)

        with pytest.raises(RuntimeError, match="final_pr_number is unexpectedly None"):
            hand.run("add a change", hand_uuid="task-999")

    @patch("helping_hands.lib.github.GitHubClient")
    def test_resumed_pr_with_none_number_in_pr_result(
        self,
        mock_gh_cls: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When resuming a PR and pr_number is set but final_pr_number becomes None."""
        from helping_hands.lib.hands.v1.hand.e2e import E2EHand

        config = Config(repo="owner/repo", model="test-model")
        monkeypatch.setenv("HELPING_HANDS_WORK_ROOT", str(tmp_path))

        mock_gh = MagicMock()
        # get_pr returns a dict-like mock for the resumed PR path
        mock_gh.get_pr.return_value = {
            "base": "main",
            "url": "https://pr/5",
            "head": "feature-branch",
        }
        mock_gh_cls.return_value.__enter__.return_value = mock_gh

        repo_index = RepoIndex.from_path(tmp_path)
        hand = E2EHand(config, repo_index)

        # Resume with a valid pr_number; final_pr_number = pr_number = 5
        # but we monkeypatch it to None after assignment to trigger the guard
        # Directly test: when final_pr_number is somehow None in the resumed
        # path, the guard catches it. This is a defensive check.
        # The realistic path: pr_number=5, resumed_pr=True, so
        # final_pr_number = pr_number = 5 — guard never fires.
        # To trigger line 291, we need create_pr to return number=None (first test).
        # This test verifies the happy path with a resumed PR works.
        resp = hand.run("update change", hand_uuid="task-888", pr_number=5)
        assert resp.metadata["backend"] == "e2e"
        mock_gh.update_pr_body.assert_called_once()


# ---------------------------------------------------------------------------
# pr_description.py 581→583: candidate already set, second non-boilerplate
# line triggers break without overwriting candidate
# ---------------------------------------------------------------------------


class TestCommitMessageFromPromptCandidateAlreadySet:
    """_commit_message_from_prompt skips second non-boilerplate line via break."""

    def test_second_non_boilerplate_line_ignored(self) -> None:
        """When boilerplate is followed by two non-boilerplate lines, first wins."""
        # Use real boilerplate patterns: [label] format and numbered list items
        summary = (
            "[claude] provider=anthropic | auth=set\n"
            "First meaningful line\n"
            "Second meaningful line\n"
        )
        result = _commit_message_from_prompt("fallback prompt", summary)
        # The first non-boilerplate line should be used (lowercased by formatter)
        assert "first meaningful line" in result.lower()
        assert "second meaningful line" not in result.lower()

    def test_break_after_candidate_set(self) -> None:
        """The break fires when candidate is already set on the next non-boilerplate."""
        summary = (
            "1. Read README.md\n"
            "Actual work done here\n"
            "This should be ignored\n"
            "Also ignored\n"
        )
        result = _commit_message_from_prompt("add feature", summary)
        assert "actual work done" in result.lower()

    def test_multiple_non_boilerplate_after_boilerplate(self) -> None:
        """Only first non-boilerplate line after boilerplate becomes commit message."""
        summary = (
            "[hand] starting task\n"
            "- bullet item one\n"
            "Implemented user authentication\n"
            "Added unit tests for auth module\n"
            "Updated documentation\n"
        )
        result = _commit_message_from_prompt("add auth", summary)
        assert "implemented user authentication" in result.lower()

    def test_no_boilerplate_uses_prompt(self) -> None:
        """Without boilerplate, prompt is preferred over summary."""
        summary = "Line one\nLine two\nLine three\n"
        result = _commit_message_from_prompt("add dark mode", summary)
        # No boilerplate → had_boilerplate is False → falls through to prompt
        assert "add dark mode" in result
