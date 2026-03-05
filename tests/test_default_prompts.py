"""Tests for helping_hands.lib.default_prompts."""

from __future__ import annotations

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT


class TestDefaultSmokeTestPrompt:
    def test_is_non_empty_string(self) -> None:
        assert isinstance(DEFAULT_SMOKE_TEST_PROMPT, str)
        assert len(DEFAULT_SMOKE_TEST_PROMPT) > 0

    def test_contains_read_directive(self) -> None:
        assert "@@READ" in DEFAULT_SMOKE_TEST_PROMPT

    def test_contains_file_directive(self) -> None:
        assert "@@FILE" in DEFAULT_SMOKE_TEST_PROMPT

    def test_contains_tool_directives(self) -> None:
        assert "@@TOOL python.run_code" in DEFAULT_SMOKE_TEST_PROMPT
        assert "@@TOOL python.run_script" in DEFAULT_SMOKE_TEST_PROMPT
        assert "@@TOOL bash.run_script" in DEFAULT_SMOKE_TEST_PROMPT
        assert "@@TOOL web.search" in DEFAULT_SMOKE_TEST_PROMPT
        assert "@@TOOL web.browse" in DEFAULT_SMOKE_TEST_PROMPT

    def test_references_readme(self) -> None:
        assert "README.md" in DEFAULT_SMOKE_TEST_PROMPT

    def test_mentions_execution_guard(self) -> None:
        assert "execution tools are enabled" in DEFAULT_SMOKE_TEST_PROMPT

    def test_mentions_web_guard(self) -> None:
        assert "web tools are enabled" in DEFAULT_SMOKE_TEST_PROMPT
