"""Tests for v169: Google-style docstrings on iterative.py methods.

Verifies that all 21 newly-documented methods have non-trivial docstrings
with the expected Args/Returns/Raises sections.
"""

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
