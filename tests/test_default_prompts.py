"""Tests for helping_hands.lib.default_prompts."""

from __future__ import annotations

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_is_non_empty() -> None:
    assert DEFAULT_SMOKE_TEST_PROMPT
    assert len(DEFAULT_SMOKE_TEST_PROMPT) > 0


def test_prompt_contains_read_marker() -> None:
    assert "@@READ" in DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_contains_file_marker() -> None:
    assert "@@FILE" in DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_contains_tool_markers() -> None:
    assert "@@TOOL python.run_code" in DEFAULT_SMOKE_TEST_PROMPT
    assert "@@TOOL python.run_script" in DEFAULT_SMOKE_TEST_PROMPT
    assert "@@TOOL bash.run_script" in DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_contains_web_tool_markers() -> None:
    assert "@@TOOL web.search" in DEFAULT_SMOKE_TEST_PROMPT
    assert "@@TOOL web.browse" in DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_references_readme() -> None:
    assert "README.md" in DEFAULT_SMOKE_TEST_PROMPT


def test_prompt_is_string() -> None:
    assert isinstance(DEFAULT_SMOKE_TEST_PROMPT, str)
