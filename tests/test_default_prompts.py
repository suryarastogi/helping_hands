"""Tests for helping_hands.lib.default_prompts."""

from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT


def test_smoke_test_prompt_is_nonempty_string() -> None:
    assert isinstance(DEFAULT_SMOKE_TEST_PROMPT, str)
    assert len(DEFAULT_SMOKE_TEST_PROMPT) > 0


def test_smoke_test_prompt_mentions_readme() -> None:
    assert "README.md" in DEFAULT_SMOKE_TEST_PROMPT


def test_smoke_test_prompt_mentions_read_and_file_ops() -> None:
    assert "@@READ" in DEFAULT_SMOKE_TEST_PROMPT
    assert "@@FILE" in DEFAULT_SMOKE_TEST_PROMPT


def test_smoke_test_prompt_mentions_tool_ops() -> None:
    assert "@@TOOL" in DEFAULT_SMOKE_TEST_PROMPT
