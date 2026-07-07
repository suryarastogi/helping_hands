"""Tests for the per-iteration timeout in iterative hands.

A single hung agent iteration must not stall the whole run. The streaming loop
wraps each agent invocation in ``asyncio.timeout()`` read from
``HELPING_HANDS_ITERATION_TIMEOUT_SECONDS`` (default 600s, ``0`` disables it).
On timeout the iteration is aborted with a clear message and the loop
continues.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.iterative import (
    _DEFAULT_ITERATION_TIMEOUT_SECONDS,
    _ITERATION_TIMEOUT_ENV,
    BasicLangGraphHand,
)
from helping_hands.lib.repo import RepoIndex


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks


def _make_langgraph_hand(tmp_path, *, max_iterations=2):
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="openai/gpt-test")
    mock_agent = MagicMock()
    with patch.object(BasicLangGraphHand, "_build_agent", return_value=mock_agent):
        hand = BasicLangGraphHand(config, repo_index, max_iterations=max_iterations)
    return hand, mock_agent


# ---------------------------------------------------------------------------
# _iteration_timeout_seconds — env parsing
# ---------------------------------------------------------------------------


def test_timeout_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_ITERATION_TIMEOUT_ENV, raising=False)
    assert (
        BasicLangGraphHand._iteration_timeout_seconds()
        == _DEFAULT_ITERATION_TIMEOUT_SECONDS
    )


def test_timeout_zero_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "0")
    assert BasicLangGraphHand._iteration_timeout_seconds() is None


def test_timeout_negative_disables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "-5")
    assert BasicLangGraphHand._iteration_timeout_seconds() is None


def test_timeout_custom_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "12.5")
    assert BasicLangGraphHand._iteration_timeout_seconds() == 12.5


def test_timeout_invalid_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "not-a-number")
    assert (
        BasicLangGraphHand._iteration_timeout_seconds()
        == _DEFAULT_ITERATION_TIMEOUT_SECONDS
    )


# ---------------------------------------------------------------------------
# stream() — a hung iteration is aborted and the loop continues
# ---------------------------------------------------------------------------


def test_stream_slow_iteration_times_out_and_continues(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "0.1")
    hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=2)

    async def _hanging_events(*args, **kwargs):
        # Never yields; simulates a hung model invoke.
        await asyncio.sleep(60)
        yield {}  # pragma: no cover - unreachable

    mock_agent.astream_events = _hanging_events

    with patch.object(hand, "_finalize_repo_pr", return_value={}):
        chunks = asyncio.run(
            asyncio.wait_for(_collect_stream(hand, "task"), timeout=10)
        )

    text = "".join(chunks)
    # Both iterations time out, then the run finishes normally (not hung).
    assert "timed out" in text
    assert "Max iterations reached" in text


def test_stream_normal_iteration_not_affected_by_timeout(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ITERATION_TIMEOUT_ENV, "30")
    hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=1)

    chunk = MagicMock()
    chunk.content = "All done.\nSATISFIED: yes"

    async def _fast_events(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

    mock_agent.astream_events = _fast_events

    with patch.object(hand, "_finalize_repo_pr", return_value={"pr_url": "u"}):
        chunks = asyncio.run(_collect_stream(hand, "task"))

    text = "".join(chunks)
    assert "timed out" not in text
    assert "All done." in text
