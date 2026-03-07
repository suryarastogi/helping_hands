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


class TestDefaultSmokeTestPromptStructure:
    """Structural validation of DEFAULT_SMOKE_TEST_PROMPT."""

    def test_has_numbered_steps(self) -> None:
        for i in range(1, 7):
            assert f"{i}." in DEFAULT_SMOKE_TEST_PROMPT

    def test_no_duplicate_tool_directives(self) -> None:
        tools = [
            "@@TOOL python.run_code",
            "@@TOOL python.run_script",
            "@@TOOL bash.run_script",
            "@@TOOL web.search",
            "@@TOOL web.browse",
        ]
        for tool in tools:
            assert DEFAULT_SMOKE_TEST_PROMPT.count(tool) == 1, (
                f"Duplicate directive: {tool}"
            )

    def test_read_directive_appears_once(self) -> None:
        assert DEFAULT_SMOKE_TEST_PROMPT.count("@@READ") == 1

    def test_file_directive_appears_once(self) -> None:
        assert DEFAULT_SMOKE_TEST_PROMPT.count("@@FILE") == 1

    def test_execution_guard_precedes_execution_tools(self) -> None:
        guard_idx = DEFAULT_SMOKE_TEST_PROMPT.index("execution tools are enabled")
        run_code_idx = DEFAULT_SMOKE_TEST_PROMPT.index("@@TOOL python.run_code")
        assert guard_idx < run_code_idx

    def test_web_guard_precedes_web_tools(self) -> None:
        guard_idx = DEFAULT_SMOKE_TEST_PROMPT.index("web tools are enabled")
        web_search_idx = DEFAULT_SMOKE_TEST_PROMPT.index("@@TOOL web.search")
        assert guard_idx < web_search_idx

    def test_ends_with_safety_note(self) -> None:
        assert DEFAULT_SMOKE_TEST_PROMPT.strip().endswith("safe.")

    def test_reasonable_length(self) -> None:
        length = len(DEFAULT_SMOKE_TEST_PROMPT)
        assert 100 < length < 2000, f"Prompt length {length} outside expected range"

    def test_references_smoke_test_scripts(self) -> None:
        assert "scripts/smoke_test.py" in DEFAULT_SMOKE_TEST_PROMPT
        assert "scripts/smoke_test.sh" in DEFAULT_SMOKE_TEST_PROMPT

    def test_python_version_specified(self) -> None:
        assert "python_version=" in DEFAULT_SMOKE_TEST_PROMPT
