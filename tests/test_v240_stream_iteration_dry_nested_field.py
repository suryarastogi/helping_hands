"""Tests for v240: DRY stream iteration processing and nested field extraction.

_process_stream_iteration() is the per-iteration state machine in the iterative
hand loop; if it stops emitting the "satisfied" signal correctly, the hand
never exits the loop and runs until the max_iterations hard stop.

_stream_max_iterations_tail() emits the trailing status messages when the loop
exhausts its iteration budget; wrong message ordering here means users see
confusing interleaved output.

_extract_nested_str_field() is used to pull the model name and other string
fields from nested request/response dicts; if it stops handling missing keys
gracefully, metadata logging raises KeyError for responses with partial data.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# _process_stream_iteration (DRY helper on _BasicIterativeHand)
# ---------------------------------------------------------------------------


class TestProcessStreamIteration:
    """Verify _process_stream_iteration encapsulates post-response stream logic."""

    def _make_hand(self) -> MagicMock:
        """Create a hand-like mock with _process_stream_iteration bound."""
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = MagicMock(spec=_BasicIterativeHand)
        hand._BACKEND_NAME = "test-backend"
        hand._apply_inline_edits = MagicMock(return_value=[])
        hand._collect_tool_feedback = MagicMock(return_value="")
        hand._merge_iteration_summary = MagicMock(return_value="summary")
        hand._is_satisfied = MagicMock(return_value=False)
        hand._finalize_repo_pr = MagicMock(return_value={})
        hand._pr_status_line = MagicMock(return_value="")
        hand._process_stream_iteration = (
            _BasicIterativeHand._process_stream_iteration.__get__(hand)
        )
        return hand

    def test_not_satisfied_returns_continuing(self) -> None:
        hand = self._make_hand()
        messages, prior, satisfied = hand._process_stream_iteration("content", "prompt")
        assert not satisfied
        assert "\n\nContinuing...\n" in messages
        assert prior == "summary"

    def test_satisfied_returns_satisfied_message(self) -> None:
        hand = self._make_hand()
        hand._is_satisfied.return_value = True
        messages, _prior, satisfied = hand._process_stream_iteration(
            "content", "prompt"
        )
        assert satisfied
        assert "\n\nTask marked satisfied.\n" in messages
        assert "\n\nContinuing...\n" not in messages

    def test_satisfied_calls_finalize(self) -> None:
        hand = self._make_hand()
        hand._is_satisfied.return_value = True
        hand._process_stream_iteration("my content", "my prompt")
        hand._finalize_repo_pr.assert_called_once_with(
            backend="test-backend", prompt="my prompt", summary="my content"
        )

    def test_not_satisfied_does_not_finalize(self) -> None:
        hand = self._make_hand()
        hand._process_stream_iteration("content", "prompt")
        hand._finalize_repo_pr.assert_not_called()

    def test_changed_files_in_messages(self) -> None:
        hand = self._make_hand()
        hand._apply_inline_edits.return_value = ["a.py", "b.py"]
        messages, _, _ = hand._process_stream_iteration("content", "prompt")
        assert any("a.py" in m and "b.py" in m for m in messages)

    def test_tool_feedback_in_messages(self) -> None:
        hand = self._make_hand()
        hand._collect_tool_feedback.return_value = "feedback text"
        messages, _, _ = hand._process_stream_iteration("content", "prompt")
        assert any("feedback text" in m for m in messages)

    def test_no_feedback_no_tool_result_message(self) -> None:
        hand = self._make_hand()
        messages, _, _ = hand._process_stream_iteration("content", "prompt")
        assert not any("[tool results]" in m for m in messages)

    def test_no_changed_no_files_updated_message(self) -> None:
        hand = self._make_hand()
        messages, _, _ = hand._process_stream_iteration("content", "prompt")
        assert not any("[files updated]" in m for m in messages)

    def test_satisfied_with_pr_status_line(self) -> None:
        hand = self._make_hand()
        hand._is_satisfied.return_value = True
        hand._pr_status_line.return_value = "[PR #42 opened]"
        messages, _, satisfied = hand._process_stream_iteration("content", "prompt")
        assert satisfied
        assert "[PR #42 opened]" in messages

    def test_satisfied_without_pr_status_line(self) -> None:
        hand = self._make_hand()
        hand._is_satisfied.return_value = True
        hand._pr_status_line.return_value = ""
        messages, _, satisfied = hand._process_stream_iteration("content", "prompt")
        assert satisfied
        assert "" not in messages  # empty string not appended

    def test_merge_called_with_content_and_feedback(self) -> None:
        hand = self._make_hand()
        hand._collect_tool_feedback.return_value = "fb"
        hand._process_stream_iteration("the content", "prompt")
        hand._merge_iteration_summary.assert_called_once_with("the content", "fb")


# ---------------------------------------------------------------------------
# _stream_max_iterations_tail (DRY helper on _BasicIterativeHand)
# ---------------------------------------------------------------------------


class TestStreamMaxIterationsTail:
    """Verify _stream_max_iterations_tail encapsulates post-loop finalization."""

    def _make_hand(self) -> MagicMock:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        hand = MagicMock(spec=_BasicIterativeHand)
        hand._BACKEND_NAME = "test-backend"
        hand._finalize_repo_pr = MagicMock(return_value={})
        hand._pr_status_line = MagicMock(return_value="")
        hand._stream_max_iterations_tail = (
            _BasicIterativeHand._stream_max_iterations_tail.__get__(hand)
        )
        return hand

    def test_contains_max_iterations_message(self) -> None:
        hand = self._make_hand()
        messages = hand._stream_max_iterations_tail("prompt", "prior")
        assert "\n\nMax iterations reached.\n" in messages

    def test_calls_finalize(self) -> None:
        hand = self._make_hand()
        hand._stream_max_iterations_tail("my prompt", "my prior")
        hand._finalize_repo_pr.assert_called_once_with(
            backend="test-backend", prompt="my prompt", summary="my prior"
        )

    def test_includes_pr_status_line(self) -> None:
        hand = self._make_hand()
        hand._pr_status_line.return_value = "[PR #99]"
        messages = hand._stream_max_iterations_tail("prompt", "prior")
        assert "[PR #99]" in messages

    def test_no_pr_status_line_when_empty(self) -> None:
        hand = self._make_hand()
        hand._pr_status_line.return_value = ""
        messages = hand._stream_max_iterations_tail("prompt", "prior")
        assert "" not in messages
        assert len(messages) == 1  # only max-iterations message

    def test_pr_status_before_max_iterations(self) -> None:
        hand = self._make_hand()
        hand._pr_status_line.return_value = "[PR status]"
        messages = hand._stream_max_iterations_tail("prompt", "prior")
        pr_idx = messages.index("[PR status]")
        max_idx = messages.index("\n\nMax iterations reached.\n")
        assert pr_idx < max_idx


# ---------------------------------------------------------------------------
# Docstring presence for new helpers
# ---------------------------------------------------------------------------


class TestStreamHelperDocstrings:
    """Ensure new DRY helpers have docstrings."""

    def test_process_stream_iteration_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        assert _BasicIterativeHand._process_stream_iteration.__doc__

    def test_stream_max_iterations_tail_has_docstring(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        assert _BasicIterativeHand._stream_max_iterations_tail.__doc__


# ---------------------------------------------------------------------------
# _extract_nested_str_field (DRY helper in server/app.py)
# ---------------------------------------------------------------------------

_skip_no_fastapi = not importlib.util.find_spec("fastapi")


@pytest.mark.skipif(_skip_no_fastapi, reason="fastapi not installed")
class TestExtractNestedStrField:
    """Verify _extract_nested_str_field delegates to the right keys."""

    @staticmethod
    def _fn():  # type: ignore[no-untyped-def]
        from helping_hands.server.app import _extract_nested_str_field

        return _extract_nested_str_field

    def test_first_key_match(self) -> None:
        assert self._fn()({"a": "val"}, ("a", "b")) == "val"

    def test_second_key_match(self) -> None:
        assert self._fn()({"b": "val"}, ("a", "b")) == "val"

    def test_prefers_earlier_key(self) -> None:
        assert self._fn()({"a": "1", "b": "2"}, ("a", "b")) == "1"

    def test_returns_none_when_missing(self) -> None:
        assert self._fn()({}, ("a", "b")) is None

    def test_ignores_empty_string(self) -> None:
        assert self._fn()({"a": ""}, ("a",)) is None

    def test_ignores_whitespace_only(self) -> None:
        assert self._fn()({"a": "   "}, ("a",)) is None

    def test_strips_whitespace(self) -> None:
        assert self._fn()({"a": "  val  "}, ("a",)) == "val"

    def test_recurses_into_request(self) -> None:
        entry = {"request": {"x": "nested"}}
        assert self._fn()(entry, ("x",)) == "nested"

    def test_no_recursion_without_request(self) -> None:
        assert self._fn()({"other": {"x": "v"}}, ("x",)) is None

    def test_non_dict_request_ignored(self) -> None:
        assert self._fn()({"request": "str"}, ("a",)) is None

    def test_non_string_value_ignored(self) -> None:
        assert self._fn()({"a": 42}, ("a",)) is None

    def test_single_key_tuple(self) -> None:
        assert self._fn()({"z": "val"}, ("z",)) == "val"

    def test_empty_keys_returns_none(self) -> None:
        assert self._fn()({"a": "val"}, ()) is None

    def test_has_docstring(self) -> None:
        assert self._fn().__doc__
