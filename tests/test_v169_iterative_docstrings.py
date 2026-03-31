"""Tests for v169: Google-style docstrings on all 21 _BasicIterativeHand methods.

_BasicIterativeHand contains the core agentic loop shared by BasicLangGraphHand and
BasicAtomicHand.  Its helpers (_build_iteration_prompt, _extract_inline_edits,
_run_tool_request, etc.) are the primary extension surface for anyone adding a new
iterative backend or debugging a stuck loop.  Without Args/Returns/Raises sections,
the non-obvious parameter semantics (e.g. what counts as "satisfied", the @@READ
protocol in _execute_read_requests) are invisible to new contributors.

The Raises: requirement on _parse_str_list, _parse_positive_int, _parse_optional_str,
and _run_tool_request documents the exceptions that the iteration loop must catch;
missing these would cause silent swallowing of parse errors.
"""

# TODO: CLEANUP CANDIDATE — all tests only assert docstring presence and section
# keywords (Args:, Returns:, Raises:); no runtime behavior is exercised.  Could
# be replaced by enabling ruff D rules (pydocstyle) for this module.

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.iterative import (
    BasicAtomicHand,
    BasicLangGraphHand,
    _BasicIterativeHand,
)

# ---------------------------------------------------------------------------
# Method → expected sections mapping
# ---------------------------------------------------------------------------

_ITERATIVE_HAND_METHODS: dict[str, list[str]] = {
    "__init__": ["Args:"],
    "_build_iteration_prompt": ["Args:", "Returns:"],
    "_is_satisfied": ["Args:", "Returns:"],
    "_extract_inline_edits": ["Args:", "Returns:"],
    "_extract_read_requests": ["Args:", "Returns:"],
    "_extract_tool_requests": ["Args:", "Returns:"],
    "_merge_iteration_summary": ["Args:", "Returns:"],
    "_execute_read_requests": ["Args:", "Returns:"],
    "_parse_str_list": ["Args:", "Returns:", "Raises:"],
    "_parse_positive_int": ["Args:", "Returns:", "Raises:"],
    "_parse_optional_str": ["Args:", "Returns:", "Raises:"],
    "_truncate_tool_output": ["Args:", "Returns:"],
    "_format_command_result": ["Args:", "Returns:"],
    "_format_web_search_result": ["Args:", "Returns:"],
    "_format_web_browse_result": ["Args:", "Returns:"],
    "_run_tool_request": ["Args:", "Returns:", "Raises:"],
    "_execute_tool_requests": ["Args:", "Returns:"],
    "_apply_inline_edits": ["Args:", "Returns:"],
}

_LANGGRAPH_METHODS: dict[str, list[str]] = {
    "_result_content": ["Args:", "Returns:"],
}

_ATOMIC_METHODS: dict[str, list[str]] = {
    "_make_input": ["Args:", "Returns:"],
    "_extract_message": ["Args:", "Returns:"],
}


# ---------------------------------------------------------------------------
# _BasicIterativeHand docstring tests
# ---------------------------------------------------------------------------


class TestIterativeHandDocstrings:
    """Verify docstrings on _BasicIterativeHand methods."""

    @pytest.mark.parametrize("method_name", list(_ITERATIVE_HAND_METHODS.keys()))
    def test_docstring_exists(self, method_name: str) -> None:
        method = getattr(_BasicIterativeHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"

    @pytest.mark.parametrize("method_name", list(_ITERATIVE_HAND_METHODS.keys()))
    def test_docstring_non_trivial(self, method_name: str) -> None:
        method = getattr(_BasicIterativeHand, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, f"{method_name} docstring is too short"

    @pytest.mark.parametrize(
        "method_name,sections",
        list(_ITERATIVE_HAND_METHODS.items()),
    )
    def test_docstring_sections(self, method_name: str, sections: list[str]) -> None:
        method = getattr(_BasicIterativeHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"
        for section in sections:
            assert section in doc, (
                f"{method_name} docstring missing '{section}' section"
            )


# ---------------------------------------------------------------------------
# BasicLangGraphHand docstring tests
# ---------------------------------------------------------------------------


class TestLangGraphHandDocstrings:
    """Verify docstrings on BasicLangGraphHand methods."""

    @pytest.mark.parametrize("method_name", list(_LANGGRAPH_METHODS.keys()))
    def test_docstring_exists(self, method_name: str) -> None:
        method = getattr(BasicLangGraphHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"

    @pytest.mark.parametrize(
        "method_name,sections",
        list(_LANGGRAPH_METHODS.items()),
    )
    def test_docstring_sections(self, method_name: str, sections: list[str]) -> None:
        method = getattr(BasicLangGraphHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"
        for section in sections:
            assert section in doc, (
                f"{method_name} docstring missing '{section}' section"
            )


# ---------------------------------------------------------------------------
# BasicAtomicHand docstring tests
# ---------------------------------------------------------------------------


class TestAtomicHandDocstrings:
    """Verify docstrings on BasicAtomicHand methods."""

    @pytest.mark.parametrize("method_name", list(_ATOMIC_METHODS.keys()))
    def test_docstring_exists(self, method_name: str) -> None:
        method = getattr(BasicAtomicHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"

    @pytest.mark.parametrize(
        "method_name,sections",
        list(_ATOMIC_METHODS.items()),
    )
    def test_docstring_sections(self, method_name: str, sections: list[str]) -> None:
        method = getattr(BasicAtomicHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"{method_name} is missing a docstring"
        for section in sections:
            assert section in doc, (
                f"{method_name} docstring missing '{section}' section"
            )
