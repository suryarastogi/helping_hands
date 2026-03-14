"""Tests for iterative.py module-level and class-level constants and docstrings.

Covers: _README_CANDIDATES, _AGENT_DOC_CANDIDATES, BasicLangGraphHand._BACKEND_NAME,
        BasicAtomicHand._BACKEND_NAME, and docstring presence on key methods.
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand.iterative import (
    _AGENT_DOC_CANDIDATES,
    _README_CANDIDATES,
    BasicAtomicHand,
    BasicLangGraphHand,
    _BasicIterativeHand,
)

# ---------------------------------------------------------------------------
# _README_CANDIDATES constant
# ---------------------------------------------------------------------------


class TestReadmeCandidates:
    def test_is_tuple(self):
        assert isinstance(_README_CANDIDATES, tuple)

    def test_contains_readme_md(self):
        assert "README.md" in _README_CANDIDATES

    def test_contains_lowercase_readme(self):
        assert "readme.md" in _README_CANDIDATES

    def test_all_strings(self):
        assert all(isinstance(c, str) for c in _README_CANDIDATES)

    def test_non_empty(self):
        assert len(_README_CANDIDATES) >= 2


# ---------------------------------------------------------------------------
# _AGENT_DOC_CANDIDATES constant
# ---------------------------------------------------------------------------


class TestAgentDocCandidates:
    def test_is_tuple(self):
        assert isinstance(_AGENT_DOC_CANDIDATES, tuple)

    def test_contains_agent_md(self):
        assert "AGENT.md" in _AGENT_DOC_CANDIDATES

    def test_contains_lowercase_agent(self):
        assert "agent.md" in _AGENT_DOC_CANDIDATES

    def test_all_strings(self):
        assert all(isinstance(c, str) for c in _AGENT_DOC_CANDIDATES)

    def test_non_empty(self):
        assert len(_AGENT_DOC_CANDIDATES) >= 2


# ---------------------------------------------------------------------------
# _BACKEND_NAME class-level constants
# ---------------------------------------------------------------------------


class TestBackendNameConstants:
    def test_langgraph_backend_name_value(self):
        assert BasicLangGraphHand._BACKEND_NAME == "basic-langgraph"

    def test_langgraph_backend_name_is_string(self):
        assert isinstance(BasicLangGraphHand._BACKEND_NAME, str)

    def test_atomic_backend_name_value(self):
        assert BasicAtomicHand._BACKEND_NAME == "basic-atomic"

    def test_atomic_backend_name_is_string(self):
        assert isinstance(BasicAtomicHand._BACKEND_NAME, str)

    def test_backend_names_are_distinct(self):
        assert BasicLangGraphHand._BACKEND_NAME != BasicAtomicHand._BACKEND_NAME

    def test_backend_names_contain_hyphen(self):
        """Backend names follow the hyphenated convention used in CLI --backend."""
        assert "-" in BasicLangGraphHand._BACKEND_NAME
        assert "-" in BasicAtomicHand._BACKEND_NAME


# ---------------------------------------------------------------------------
# Docstring presence on key methods
# ---------------------------------------------------------------------------

_METHODS_WITH_DOCSTRINGS = [
    "_execution_tools_enabled",
    "_web_tools_enabled",
    "_tool_instructions",
    "_format_command",
    "_tool_disabled_error",
    "_read_bootstrap_doc",
    "_build_tree_snapshot",
    "_build_bootstrap_context",
]


class TestDocstringsPresent:
    """Verify that key _BasicIterativeHand methods have docstrings."""

    def test_all_key_methods_have_docstrings(self):
        for method_name in _METHODS_WITH_DOCSTRINGS:
            method = getattr(_BasicIterativeHand, method_name)
            doc = inspect.getdoc(method)
            assert doc, f"{method_name} is missing a docstring"

    def test_docstrings_are_non_trivial(self):
        """Docstrings should be at least 10 characters (not just whitespace)."""
        for method_name in _METHODS_WITH_DOCSTRINGS:
            method = getattr(_BasicIterativeHand, method_name)
            doc = inspect.getdoc(method)
            assert doc and len(doc.strip()) >= 10, (
                f"{method_name} docstring is too short"
            )

    def test_tool_instructions_docstring_has_returns(self):
        doc = inspect.getdoc(_BasicIterativeHand._tool_instructions)
        assert "Returns:" in doc

    def test_format_command_docstring_has_args(self):
        doc = inspect.getdoc(_BasicIterativeHand._format_command)
        assert "Args:" in doc

    def test_read_bootstrap_doc_docstring_has_args(self):
        doc = inspect.getdoc(_BasicIterativeHand._read_bootstrap_doc)
        assert "Args:" in doc

    def test_build_tree_snapshot_docstring_has_returns(self):
        doc = inspect.getdoc(_BasicIterativeHand._build_tree_snapshot)
        assert "Returns:" in doc
