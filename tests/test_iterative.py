"""Tests for _BasicIterativeHand parsing, extraction, and utility methods."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import HandResponse
from helping_hands.lib.hands.v1.hand.iterative import (
    BasicAtomicHand,
    BasicLangGraphHand,
    _BasicIterativeHand,
)
from helping_hands.lib.meta.tools.command import CommandResult
from helping_hands.lib.meta.tools.web import (
    WebBrowseResult,
    WebSearchItem,
    WebSearchResult,
)
from helping_hands.lib.repo import RepoIndex


class _StubIterativeHand(_BasicIterativeHand):
    """Concrete stub so we can instantiate _BasicIterativeHand for testing."""

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield prompt


def _make_hand(
    tmp_path: Path,
    files: dict[str, str] | None = None,
    **config_kwargs: object,
) -> _StubIterativeHand:
    """Create a _StubIterativeHand backed by a real tmp_path repo."""
    if files:
        for rel_path, content in files.items():
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
    repo_index = RepoIndex.from_path(tmp_path)
    defaults = {"repo": str(tmp_path), "model": "test-model"}
    defaults.update(config_kwargs)
    config = Config(**defaults)
    with patch(
        "helping_hands.lib.meta.tools.registry.build_tool_runner_map",
        return_value={},
    ):
        hand = _StubIterativeHand(config, repo_index)
    return hand


# ---------------------------------------------------------------------------
# _is_satisfied
# ---------------------------------------------------------------------------


class TestIsSatisfied:
    def test_yes(self):
        assert _BasicIterativeHand._is_satisfied("Done.\nSATISFIED: yes") is True

    def test_no(self):
        assert (
            _BasicIterativeHand._is_satisfied("Still working.\nSATISFIED: no") is False
        )

    def test_missing(self):
        assert _BasicIterativeHand._is_satisfied("No marker here.") is False

    def test_case_insensitive(self):
        assert _BasicIterativeHand._is_satisfied("satisfied: YES") is True

    def test_extra_whitespace(self):
        assert _BasicIterativeHand._is_satisfied("SATISFIED:  yes") is True


# ---------------------------------------------------------------------------
# _extract_inline_edits
# ---------------------------------------------------------------------------


class TestExtractInlineEdits:
    def test_single_edit(self):
        content = "@@FILE: src/main.py\n```python\nprint('hello')\n```"
        edits = _BasicIterativeHand._extract_inline_edits(content)
        assert len(edits) == 1
        assert edits[0] == ("src/main.py", "print('hello')")

    def test_multiple_edits(self):
        content = (
            "@@FILE: a.py\n```python\ncode_a\n```\n\n"
            "@@FILE: b.txt\n```text\ncode_b\n```"
        )
        edits = _BasicIterativeHand._extract_inline_edits(content)
        assert len(edits) == 2
        assert edits[0][0] == "a.py"
        assert edits[1][0] == "b.txt"

    def test_no_edits(self):
        assert _BasicIterativeHand._extract_inline_edits("No file blocks here.") == []

    def test_whitespace_in_path(self):
        content = "@@FILE:  src/hello.py \n```python\npass\n```"
        edits = _BasicIterativeHand._extract_inline_edits(content)
        assert len(edits) == 1
        assert edits[0][0] == "src/hello.py"

    def test_multiline_content(self):
        content = "@@FILE: config.yaml\n```yaml\nkey: value\nnested:\n  child: 1\n```"
        edits = _BasicIterativeHand._extract_inline_edits(content)
        assert len(edits) == 1
        assert "nested:" in edits[0][1]


# ---------------------------------------------------------------------------
# _extract_read_requests
# ---------------------------------------------------------------------------


class TestExtractReadRequests:
    def test_explicit_read(self):
        content = "@@READ: src/main.py\n"
        paths = _BasicIterativeHand._extract_read_requests(content)
        assert paths == ["src/main.py"]

    def test_multiple_reads(self):
        content = "@@READ: a.py\n@@READ: b.py\n"
        paths = _BasicIterativeHand._extract_read_requests(content)
        assert paths == ["a.py", "b.py"]

    def test_fallback_pattern(self):
        content = "Please read the file `src/config.py` for me."
        paths = _BasicIterativeHand._extract_read_requests(content)
        assert paths == ["src/config.py"]

    def test_no_requests(self):
        assert _BasicIterativeHand._extract_read_requests("Nothing here.") == []

    def test_explicit_takes_precedence_over_fallback(self):
        content = "@@READ: a.py\nPlease read the file `b.py`."
        paths = _BasicIterativeHand._extract_read_requests(content)
        assert paths == ["a.py"]


# ---------------------------------------------------------------------------
# _extract_tool_requests
# ---------------------------------------------------------------------------


class TestExtractToolRequests:
    def test_valid_tool(self):
        content = '@@TOOL: shell_exec\n```json\n{"command": "ls"}\n```'
        reqs = _BasicIterativeHand._extract_tool_requests(content)
        assert len(reqs) == 1
        name, payload, error = reqs[0]
        assert name == "shell_exec"
        assert payload == {"command": "ls"}
        assert error is None

    def test_invalid_json(self):
        content = "@@TOOL: bad_tool\n```json\n{not valid json}\n```"
        reqs = _BasicIterativeHand._extract_tool_requests(content)
        assert len(reqs) == 1
        assert reqs[0][1] == {}
        assert "invalid JSON" in reqs[0][2]

    def test_non_dict_payload(self):
        content = '@@TOOL: array_tool\n```json\n["a", "b"]\n```'
        reqs = _BasicIterativeHand._extract_tool_requests(content)
        assert len(reqs) == 1
        assert reqs[0][2] == "payload must be a JSON object"

    def test_no_tool_requests(self):
        assert _BasicIterativeHand._extract_tool_requests("No tools.") == []

    def test_multiple_tools(self):
        content = (
            '@@TOOL: a\n```json\n{"x": 1}\n```\n\n@@TOOL: b\n```json\n{"y": 2}\n```'
        )
        reqs = _BasicIterativeHand._extract_tool_requests(content)
        assert len(reqs) == 2
        assert reqs[0][0] == "a"
        assert reqs[1][0] == "b"


# ---------------------------------------------------------------------------
# _parse_str_list
# ---------------------------------------------------------------------------


class TestParseStrList:
    def test_valid_list(self):
        assert _BasicIterativeHand._parse_str_list(
            {"paths": ["a.py", "b.py"]}, key="paths"
        ) == ["a.py", "b.py"]

    def test_missing_key(self):
        assert _BasicIterativeHand._parse_str_list({}, key="paths") == []

    def test_none_value(self):
        assert _BasicIterativeHand._parse_str_list({"paths": None}, key="paths") == []

    def test_non_list_raises(self):
        with pytest.raises(ValueError, match="must be a list"):
            _BasicIterativeHand._parse_str_list({"paths": "single"}, key="paths")

    def test_non_string_items_raise(self):
        with pytest.raises(ValueError, match="must contain only strings"):
            _BasicIterativeHand._parse_str_list({"paths": [1, 2]}, key="paths")


# ---------------------------------------------------------------------------
# _parse_positive_int
# ---------------------------------------------------------------------------


class TestParsePositiveInt:
    def test_valid_int(self):
        assert (
            _BasicIterativeHand._parse_positive_int({"n": 5}, key="n", default=1) == 5
        )

    def test_default(self):
        assert _BasicIterativeHand._parse_positive_int({}, key="n", default=3) == 3

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="must be > 0"):
            _BasicIterativeHand._parse_positive_int({"n": 0}, key="n", default=1)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be > 0"):
            _BasicIterativeHand._parse_positive_int({"n": -1}, key="n", default=1)

    def test_bool_raises(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _BasicIterativeHand._parse_positive_int({"n": True}, key="n", default=1)

    def test_string_raises(self):
        with pytest.raises(ValueError, match="must be an integer"):
            _BasicIterativeHand._parse_positive_int({"n": "5"}, key="n", default=1)


# ---------------------------------------------------------------------------
# _parse_optional_str
# ---------------------------------------------------------------------------


class TestParseOptionalStr:
    def test_valid_string(self):
        assert (
            _BasicIterativeHand._parse_optional_str({"msg": "hello"}, key="msg")
            == "hello"
        )

    def test_none_returns_none(self):
        assert _BasicIterativeHand._parse_optional_str({}, key="msg") is None

    def test_empty_string_returns_none(self):
        assert _BasicIterativeHand._parse_optional_str({"msg": "  "}, key="msg") is None

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _BasicIterativeHand._parse_optional_str({"msg": 123}, key="msg")


# ---------------------------------------------------------------------------
# _truncate_tool_output
# ---------------------------------------------------------------------------


class TestTruncateToolOutput:
    def test_short_text_unchanged(self):
        text, truncated = _BasicIterativeHand._truncate_tool_output("short")
        assert text == "short"
        assert truncated is False

    def test_long_text_truncated(self):
        long_text = "x" * (_BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS + 100)
        text, truncated = _BasicIterativeHand._truncate_tool_output(long_text)
        assert len(text) == _BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS
        assert truncated is True

    def test_exact_limit_not_truncated(self):
        exact = "y" * _BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS
        text, truncated = _BasicIterativeHand._truncate_tool_output(exact)
        assert text == exact
        assert truncated is False


# ---------------------------------------------------------------------------
# _merge_iteration_summary
# ---------------------------------------------------------------------------


class TestMergeIterationSummary:
    def test_no_feedback(self):
        result = _BasicIterativeHand._merge_iteration_summary("content", "")
        assert result == "content"

    def test_with_feedback(self):
        result = _BasicIterativeHand._merge_iteration_summary("content", "tool output")
        assert "content" in result
        assert "Tool results:" in result
        assert "tool output" in result


# ---------------------------------------------------------------------------
# _format_command
# ---------------------------------------------------------------------------


class TestFormatCommand:
    def test_simple_tokens(self):
        assert _BasicIterativeHand._format_command(["ls", "-la"]) == "ls -la"

    def test_tokens_with_spaces_are_quoted(self):
        result = _BasicIterativeHand._format_command(["echo", "hello world"])
        assert result == "echo 'hello world'"

    def test_empty_command(self):
        assert _BasicIterativeHand._format_command([]) == ""

    def test_special_characters(self):
        result = _BasicIterativeHand._format_command(["grep", "foo|bar"])
        assert "'foo|bar'" in result


# ---------------------------------------------------------------------------
# _format_command_result
# ---------------------------------------------------------------------------


class TestFormatCommandResult:
    def test_successful_result(self):
        cr = CommandResult(
            command=["echo", "hi"],
            cwd="/tmp",
            exit_code=0,
            stdout="hi\n",
            stderr="",
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="shell_exec", result=cr
        )
        assert "@@TOOL_RESULT: shell_exec" in output
        assert "status: success" in output
        assert "exit_code: 0" in output
        assert "timed_out: false" in output
        assert "cwd: /tmp" in output
        assert "command: echo hi" in output
        assert "hi\n" in output

    def test_failed_result(self):
        cr = CommandResult(
            command=["false"],
            cwd="/tmp",
            exit_code=1,
            stdout="",
            stderr="error occurred",
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="shell_exec", result=cr
        )
        assert "status: failure" in output
        assert "exit_code: 1" in output
        assert "error occurred" in output

    def test_timed_out_result(self):
        cr = CommandResult(
            command=["sleep", "999"],
            cwd="/tmp",
            exit_code=-1,
            stdout="",
            stderr="",
            timed_out=True,
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="shell_exec", result=cr
        )
        assert "timed_out: true" in output

    def test_truncated_stdout(self):
        long_stdout = "x" * (_BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS + 100)
        cr = CommandResult(
            command=["cat", "big"],
            cwd="/tmp",
            exit_code=0,
            stdout=long_stdout,
            stderr="",
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="shell_exec", result=cr
        )
        assert "[truncated]" in output

    def test_truncated_stderr(self):
        long_stderr = "e" * (_BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS + 100)
        cr = CommandResult(
            command=["fail"],
            cwd="/tmp",
            exit_code=1,
            stdout="",
            stderr=long_stderr,
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="shell_exec", result=cr
        )
        assert output.count("[truncated]") >= 1


# ---------------------------------------------------------------------------
# _format_web_search_result
# ---------------------------------------------------------------------------


class TestFormatWebSearchResult:
    def test_basic_search_result(self):
        result = WebSearchResult(
            query="python docs",
            results=[
                WebSearchItem(
                    title="Python.org",
                    url="https://python.org",
                    snippet="Welcome to Python",
                ),
            ],
        )
        output = _BasicIterativeHand._format_web_search_result(
            tool_name="web_search", result=result
        )
        assert "@@TOOL_RESULT: web_search" in output
        assert "status: success" in output
        assert "query: python docs" in output
        assert "result_count: 1" in output
        assert "Python.org" in output
        assert "https://python.org" in output

    def test_empty_results(self):
        result = WebSearchResult(query="nothing", results=[])
        output = _BasicIterativeHand._format_web_search_result(
            tool_name="web_search", result=result
        )
        assert "result_count: 0" in output

    def test_truncated_search_results(self):
        items = [
            WebSearchItem(
                title=f"Result {i}",
                url=f"https://example.com/{i}",
                snippet="x" * 500,
            )
            for i in range(_BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS // 100)
        ]
        result = WebSearchResult(query="large", results=items)
        output = _BasicIterativeHand._format_web_search_result(
            tool_name="web_search", result=result
        )
        assert "[truncated]" in output


# ---------------------------------------------------------------------------
# _format_web_browse_result
# ---------------------------------------------------------------------------


class TestFormatWebBrowseResult:
    def test_basic_browse_result(self):
        result = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com/page",
            status_code=200,
            content="Hello World",
            truncated=False,
        )
        output = _BasicIterativeHand._format_web_browse_result(
            tool_name="web_browse", result=result
        )
        assert "@@TOOL_RESULT: web_browse" in output
        assert "status: success" in output
        assert "url: https://example.com" in output
        assert "final_url: https://example.com/page" in output
        assert "status_code: 200" in output
        assert "source_truncated: false" in output
        assert "Hello World" in output

    def test_source_truncated_flag(self):
        result = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content="short",
            truncated=True,
        )
        output = _BasicIterativeHand._format_web_browse_result(
            tool_name="web_browse", result=result
        )
        assert "source_truncated: true" in output

    def test_output_truncation(self):
        long_content = "c" * (_BasicIterativeHand._MAX_TOOL_OUTPUT_CHARS + 100)
        result = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content=long_content,
            truncated=False,
        )
        output = _BasicIterativeHand._format_web_browse_result(
            tool_name="web_browse", result=result
        )
        assert "[truncated]" in output

    def test_none_status_code(self):
        result = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=None,
            content="ok",
            truncated=False,
        )
        output = _BasicIterativeHand._format_web_browse_result(
            tool_name="web_browse", result=result
        )
        assert "status_code: None" in output


# ---------------------------------------------------------------------------
# _tool_disabled_error
# ---------------------------------------------------------------------------


class TestToolDisabledError:
    def test_known_tool_includes_category(self):
        with patch(
            "helping_hands.lib.meta.tools.registry.category_name_for_tool",
            return_value="execution",
        ):
            err = _BasicIterativeHand._tool_disabled_error("shell_exec")
            assert isinstance(err, ValueError)
            assert "disabled" in str(err)
            assert "--tools execution" in str(err)

    def test_unknown_tool_says_unsupported(self):
        with patch(
            "helping_hands.lib.meta.tools.registry.category_name_for_tool",
            return_value=None,
        ):
            err = _BasicIterativeHand._tool_disabled_error("nonexistent_tool")
            assert isinstance(err, ValueError)
            assert "unsupported tool" in str(err)


# ---------------------------------------------------------------------------
# _build_iteration_prompt
# ---------------------------------------------------------------------------


class TestBuildIterationPrompt:
    def test_basic_prompt_structure(self, tmp_path):
        hand = _make_hand(tmp_path, {"README.md": "hello"})
        result = hand._build_iteration_prompt(
            prompt="Fix the bug",
            iteration=1,
            max_iterations=3,
            previous_summary="",
            bootstrap_context="",
        )
        assert "Task request: Fix the bug" in result
        assert "Iteration: 1/3" in result
        assert "Previous iteration summary: none" in result
        assert "@@READ:" in result
        assert "@@FILE:" in result
        assert "SATISFIED: yes|no" in result

    def test_includes_bootstrap_context(self, tmp_path):
        hand = _make_hand(tmp_path)
        result = hand._build_iteration_prompt(
            prompt="task",
            iteration=1,
            max_iterations=5,
            previous_summary="",
            bootstrap_context="Repository tree snapshot:\n- src/\n- README.md",
        )
        assert "Bootstrap repository context:" in result
        assert "Repository tree snapshot:" in result

    def test_excludes_bootstrap_when_empty(self, tmp_path):
        hand = _make_hand(tmp_path)
        result = hand._build_iteration_prompt(
            prompt="task",
            iteration=2,
            max_iterations=5,
            previous_summary="did stuff",
            bootstrap_context="",
        )
        assert "Bootstrap repository context:" not in result

    def test_previous_summary_included(self, tmp_path):
        hand = _make_hand(tmp_path)
        result = hand._build_iteration_prompt(
            prompt="task",
            iteration=3,
            max_iterations=5,
            previous_summary="Made progress on X",
            bootstrap_context="",
        )
        assert "Previous iteration summary: Made progress on X" in result


# ---------------------------------------------------------------------------
# _execution_tools_enabled / _web_tools_enabled
# ---------------------------------------------------------------------------


class TestToolConfigFlags:
    def test_execution_tools_enabled_true(self, tmp_path):
        hand = _make_hand(tmp_path, enable_execution=True)
        assert hand._execution_tools_enabled() is True

    def test_execution_tools_enabled_false(self, tmp_path):
        hand = _make_hand(tmp_path, enable_execution=False)
        assert hand._execution_tools_enabled() is False

    def test_execution_tools_default_is_false(self, tmp_path):
        hand = _make_hand(tmp_path)
        assert hand._execution_tools_enabled() is False

    def test_web_tools_enabled_true(self, tmp_path):
        hand = _make_hand(tmp_path, enable_web=True)
        assert hand._web_tools_enabled() is True

    def test_web_tools_enabled_false(self, tmp_path):
        hand = _make_hand(tmp_path, enable_web=False)
        assert hand._web_tools_enabled() is False

    def test_web_tools_default_is_false(self, tmp_path):
        hand = _make_hand(tmp_path)
        assert hand._web_tools_enabled() is False


# ---------------------------------------------------------------------------
# _tool_instructions
# ---------------------------------------------------------------------------


class TestToolInstructions:
    def test_includes_tool_result_note(self, tmp_path):
        hand = _make_hand(tmp_path)
        result = hand._tool_instructions()
        assert "@@TOOL_RESULT" in result

    def test_includes_skill_knowledge_when_available(self, tmp_path):
        hand = _make_hand(tmp_path)
        with patch(
            "helping_hands.lib.meta.skills.format_skill_knowledge",
            return_value="SKILL: test_skill\nDoes cool things.",
        ):
            result = hand._tool_instructions()
            assert "SKILL: test_skill" in result

    def test_no_skill_section_when_empty(self, tmp_path):
        hand = _make_hand(tmp_path)
        with patch(
            "helping_hands.lib.meta.skills.format_skill_knowledge",
            return_value="",
        ):
            result = hand._tool_instructions()
            assert "SKILL:" not in result


# ---------------------------------------------------------------------------
# BasicLangGraphHand._result_content
# ---------------------------------------------------------------------------


class TestResultContent:
    def test_empty_messages(self):
        assert BasicLangGraphHand._result_content({"messages": []}) == ""

    def test_missing_messages_key(self):
        assert BasicLangGraphHand._result_content({}) == ""

    def test_none_messages(self):
        assert BasicLangGraphHand._result_content({"messages": None}) == ""

    def test_last_message_with_content_attr(self):
        class FakeMsg:
            content = "final answer"

        result = BasicLangGraphHand._result_content({"messages": [FakeMsg()]})
        assert result == "final answer"

    def test_fallback_to_str(self):
        result = BasicLangGraphHand._result_content({"messages": ["first", "second"]})
        assert result == "second"

    def test_multiple_messages_uses_last(self):
        class MsgA:
            content = "first"

        class MsgB:
            content = "last"

        result = BasicLangGraphHand._result_content({"messages": [MsgA(), MsgB()]})
        assert result == "last"


# ---------------------------------------------------------------------------
# BasicAtomicHand._extract_message
# ---------------------------------------------------------------------------


class TestExtractMessage:
    def test_chat_message_attribute(self):
        class FakeResponse:
            chat_message = "hello from atomic"

        assert BasicAtomicHand._extract_message(FakeResponse()) == "hello from atomic"

    def test_empty_chat_message_falls_back(self):
        class FakeResponse:
            chat_message = ""

        result = BasicAtomicHand._extract_message(FakeResponse())
        # Empty chat_message is falsy, so falls back to str()
        assert isinstance(result, str)

    def test_none_chat_message_falls_back(self):
        class FakeResponse:
            chat_message = None

        result = BasicAtomicHand._extract_message(FakeResponse())
        assert isinstance(result, str)

    def test_no_chat_message_attr(self):
        result = BasicAtomicHand._extract_message({"key": "value"})
        assert result == str({"key": "value"})

    def test_plain_string(self):
        result = BasicAtomicHand._extract_message("plain text")
        assert result == "plain text"
