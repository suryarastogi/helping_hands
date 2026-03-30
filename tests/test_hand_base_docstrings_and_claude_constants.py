"""Tests for Hand base.py docstrings and claude.py stream-json constants.

Guards the stream-JSON parsing constants in ClaudeCodeHand's claude.py: if
_EVENT_TYPE_* or _BLOCK_TYPE_* values are changed or collide, the Claude CLI
output parser will silently misclassify events, dropping tool-use blocks or
result events without raising any exception.

# TODO: CLEANUP CANDIDATE
TestHandBaseDocstringsPresent verifies stylistic convention (Google-style
docstring sections) rather than behavioral invariants — these tests will fail
on any future method rename but do not protect against correctness regressions
in the Hand PR lifecycle.
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand.base import Hand
from helping_hands.lib.hands.v1.hand.cli.claude import (
    _BLOCK_TYPE_TEXT,
    _BLOCK_TYPE_TOOL_RESULT,
    _BLOCK_TYPE_TOOL_USE,
    _EVENT_TYPE_ASSISTANT,
    _EVENT_TYPE_RESULT,
    _EVENT_TYPE_USER,
)

# ---------------------------------------------------------------------------
# Hand base.py — docstring presence
# ---------------------------------------------------------------------------

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


class TestHandBaseDocstringsPresent:
    """Verify that key Hand methods have docstrings."""

    def test_all_key_methods_have_docstrings(self):
        for method_name in _BASE_METHODS_WITH_DOCSTRINGS:
            method = getattr(Hand, method_name)
            doc = inspect.getdoc(method)
            assert doc, f"{method_name} is missing a docstring"

    def test_docstrings_are_non_trivial(self):
        """Docstrings should be at least 10 characters (not just whitespace)."""
        for method_name in _BASE_METHODS_WITH_DOCSTRINGS:
            method = getattr(Hand, method_name)
            doc = inspect.getdoc(method)
            assert doc and len(doc.strip()) >= 10, (
                f"{method_name} docstring is too short"
            )

    def test_run_git_read_docstring_has_args(self):
        doc = inspect.getdoc(Hand._run_git_read)
        assert "Args:" in doc

    def test_run_git_read_docstring_has_returns(self):
        doc = inspect.getdoc(Hand._run_git_read)
        assert "Returns:" in doc

    def test_github_repo_from_origin_docstring_has_args(self):
        doc = inspect.getdoc(Hand._github_repo_from_origin)
        assert "Args:" in doc

    def test_github_repo_from_origin_docstring_has_returns(self):
        doc = inspect.getdoc(Hand._github_repo_from_origin)
        assert "Returns:" in doc

    def test_build_generic_pr_body_docstring_has_raises(self):
        doc = inspect.getdoc(Hand._build_generic_pr_body)
        assert "Raises:" in doc

    def test_configure_push_remote_docstring_has_raises(self):
        doc = inspect.getdoc(Hand._configure_authenticated_push_remote)
        assert "Raises:" in doc

    def test_run_precommit_docstring_has_raises(self):
        doc = inspect.getdoc(Hand._run_precommit_checks_and_fixes)
        assert "Raises:" in doc

    def test_finalize_repo_pr_docstring_has_returns(self):
        doc = inspect.getdoc(Hand._finalize_repo_pr)
        assert "Returns:" in doc

    def test_is_interrupted_docstring_has_returns(self):
        doc = inspect.getdoc(Hand._is_interrupted)
        assert "Returns:" in doc


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
