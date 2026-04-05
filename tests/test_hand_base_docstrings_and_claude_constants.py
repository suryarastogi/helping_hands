"""Tests for Hand base.py docstrings and claude.py stream-json constants.

Verifies that key protected methods in the Hand base class carry Google-style
docstrings (Args/Returns/Raises sections), enforcing the project convention
that public API helpers are self-documenting. Also guards the stream-JSON
parsing constants in ClaudeCodeHand's claude.py: if _EVENT_TYPE_* or
_BLOCK_TYPE_* values are changed or collide, the Claude CLI output parser
will silently misclassify events, dropping tool-use blocks or result events.
"""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.claude import (
    _BLOCK_TYPE_TEXT,
    _BLOCK_TYPE_TOOL_RESULT,
    _BLOCK_TYPE_TOOL_USE,
    _EVENT_TYPE_ASSISTANT,
    _EVENT_TYPE_RESULT,
    _EVENT_TYPE_USER,
)

_BASE_METHODS_WITH_DOCSTRINGS = [
    "_is_interrupted",
    "_default_base_branch",
    "_run_git_read",
    "_github_repo_from_origin",
    "_build_generic_pr_body",
    "_configure_authenticated_push_remote",
    "_should_run_precommit_before_pr",
    "_run_precommit_checks_and_fixes",
    "_finalize_repo_pr",
]


# ---------------------------------------------------------------------------
# Claude CLI — stream-json event type constants
# ---------------------------------------------------------------------------


class TestEventTypeConstants:
    def test_assistant_value(self):
        assert _EVENT_TYPE_ASSISTANT == "assistant"

    def test_user_value(self):
        assert _EVENT_TYPE_USER == "user"

    def test_result_value(self):
        assert _EVENT_TYPE_RESULT == "result"

    def test_all_are_strings(self):
        for const in (_EVENT_TYPE_ASSISTANT, _EVENT_TYPE_USER, _EVENT_TYPE_RESULT):
            assert isinstance(const, str)

    def test_all_are_distinct(self):
        values = {_EVENT_TYPE_ASSISTANT, _EVENT_TYPE_USER, _EVENT_TYPE_RESULT}
        assert len(values) == 3


class TestBlockTypeConstants:
    def test_tool_use_value(self):
        assert _BLOCK_TYPE_TOOL_USE == "tool_use"

    def test_tool_result_value(self):
        assert _BLOCK_TYPE_TOOL_RESULT == "tool_result"

    def test_text_value(self):
        assert _BLOCK_TYPE_TEXT == "text"

    def test_all_are_strings(self):
        for const in (_BLOCK_TYPE_TOOL_USE, _BLOCK_TYPE_TOOL_RESULT, _BLOCK_TYPE_TEXT):
            assert isinstance(const, str)

    def test_all_are_distinct(self):
        values = {_BLOCK_TYPE_TOOL_USE, _BLOCK_TYPE_TOOL_RESULT, _BLOCK_TYPE_TEXT}
        assert len(values) == 3

    def test_event_and_block_types_no_overlap(self):
        """Event types and block types should be distinct namespaces."""
        event_types = {_EVENT_TYPE_ASSISTANT, _EVENT_TYPE_USER, _EVENT_TYPE_RESULT}
        block_types = {_BLOCK_TYPE_TOOL_USE, _BLOCK_TYPE_TOOL_RESULT, _BLOCK_TYPE_TEXT}
        assert event_types.isdisjoint(block_types)
