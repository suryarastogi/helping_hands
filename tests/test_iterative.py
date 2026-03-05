"""Tests for _BasicIterativeHand parsing, extraction, and utility methods."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# _execute_read_requests — error paths (lines 204-217)
# ---------------------------------------------------------------------------


class TestExecuteReadRequestsErrors:
    _PATCH_TARGET = (
        "helping_hands.lib.hands.v1.hand.iterative.system_tools.read_text_file"
    )

    def test_value_error_on_invalid_path(self, tmp_path):
        hand = _make_hand(tmp_path, {"good.txt": "hello"})
        with patch(self._PATCH_TARGET, side_effect=ValueError("invalid path")):
            result = hand._execute_read_requests("@@READ: ../evil.py\n")
        assert "@@READ_RESULT: ../evil.py" in result
        assert "ERROR: invalid path" in result

    def test_file_not_found(self, tmp_path):
        hand = _make_hand(tmp_path)
        with patch(self._PATCH_TARGET, side_effect=FileNotFoundError):
            result = hand._execute_read_requests("@@READ: nonexistent.py\n")
        assert "ERROR: file not found" in result

    def test_is_a_directory(self, tmp_path):
        hand = _make_hand(tmp_path)
        with patch(self._PATCH_TARGET, side_effect=IsADirectoryError):
            result = hand._execute_read_requests("@@READ: subdir\n")
        assert "ERROR: path is a directory" in result

    def test_unicode_error(self, tmp_path):
        hand = _make_hand(tmp_path, {"binary.bin": "x"})
        with patch(self._PATCH_TARGET, side_effect=UnicodeError("not utf-8")):
            result = hand._execute_read_requests("@@READ: binary.bin\n")
        assert "ERROR: file is not UTF-8 text" in result


# ---------------------------------------------------------------------------
# _run_tool_request — dispatch branches (lines 365-376)
# ---------------------------------------------------------------------------


class TestRunToolRequest:
    def test_dispatches_web_search_result(self, tmp_path):
        hand = _make_hand(tmp_path)
        sr = WebSearchResult(query="q", results=[])
        hand._tool_runners["web_search"] = lambda _root, _payload: sr
        result = hand._run_tool_request(
            root=tmp_path, tool_name="web_search", payload={}
        )
        assert "@@TOOL_RESULT: web_search" in result
        assert "result_count: 0" in result

    def test_dispatches_web_browse_result(self, tmp_path):
        hand = _make_hand(tmp_path)
        br = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content="ok",
            truncated=False,
        )
        hand._tool_runners["web_browse"] = lambda _root, _payload: br
        result = hand._run_tool_request(
            root=tmp_path, tool_name="web_browse", payload={}
        )
        assert "@@TOOL_RESULT: web_browse" in result
        assert "url: https://example.com" in result

    def test_unsupported_type_raises(self, tmp_path):
        hand = _make_hand(tmp_path)
        hand._tool_runners["custom"] = lambda _root, _payload: "just a string"
        with pytest.raises(TypeError, match="unsupported tool result type"):
            hand._run_tool_request(root=tmp_path, tool_name="custom", payload={})

    def test_disabled_tool_raises(self, tmp_path):
        hand = _make_hand(tmp_path)
        with (
            patch(
                "helping_hands.lib.meta.tools.registry.category_name_for_tool",
                return_value=None,
            ),
            pytest.raises(ValueError, match="unsupported tool"),
        ):
            hand._run_tool_request(root=tmp_path, tool_name="nope", payload={})


# ---------------------------------------------------------------------------
# _execute_tool_requests — error/disabled paths (lines 386-405)
# ---------------------------------------------------------------------------


class TestExecuteToolRequests:
    def test_parse_error_in_payload(self, tmp_path):
        hand = _make_hand(tmp_path)
        content = "@@TOOL: shell_exec\n```json\n{invalid json}\n```"
        result = hand._execute_tool_requests(content)
        assert "@@TOOL_RESULT: shell_exec" in result
        assert "ERROR:" in result

    def test_runtime_error_caught(self, tmp_path):
        hand = _make_hand(tmp_path)
        hand._tool_runners["shell_exec"] = lambda _r, _p: (_ for _ in ()).throw(
            RuntimeError("boom")
        )
        content = '@@TOOL: shell_exec\n```json\n{"command": "ls"}\n```'
        result = hand._execute_tool_requests(content)
        assert "@@TOOL_RESULT: shell_exec" in result
        assert "ERROR: boom" in result

    def test_no_tool_requests_returns_empty(self, tmp_path):
        hand = _make_hand(tmp_path)
        result = hand._execute_tool_requests("no tools here")
        assert result == ""


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


async def _collect_stream(hand, prompt: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in hand.stream(prompt):
        chunks.append(chunk)
    return chunks


def _make_langgraph_hand(tmp_path, *, max_iterations=2):
    """Build a BasicLangGraphHand with _build_agent mocked."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="openai/gpt-test")
    mock_agent = MagicMock()
    with patch.object(BasicLangGraphHand, "_build_agent", return_value=mock_agent):
        hand = BasicLangGraphHand(config, repo_index, max_iterations=max_iterations)
    return hand, mock_agent


def _make_atomic_hand(tmp_path, *, max_iterations=2):
    """Build a BasicAtomicHand with _build_agent mocked."""
    (tmp_path / "main.py").write_text("")
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="openai/gpt-test")
    mock_agent = MagicMock()
    with patch.object(BasicAtomicHand, "_build_agent", return_value=mock_agent):
        hand = BasicAtomicHand(config, repo_index, max_iterations=max_iterations)
    hand._input_schema = type("FakeInput", (), {"__init__": lambda s, **kw: None})
    return hand, mock_agent


# ---------------------------------------------------------------------------
# BasicLangGraphHand.stream() — coverage for lines 598-677
# ---------------------------------------------------------------------------


class TestBasicLangGraphHandStream:
    def test_stream_satisfied_first_iteration(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=3)

        chunk = MagicMock()
        chunk.content = "All done.\nSATISFIED: yes"

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(
            hand, "_finalize_repo_pr", return_value={"pr_url": "https://pr/1"}
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "satisfied" in text.lower() or "Task marked satisfied" in text
        assert "PR created" in text

    def test_stream_max_iterations_reached(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=2)

        chunk = MagicMock()
        chunk.content = "Working.\nSATISFIED: no"

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Max iterations reached" in text

    def test_stream_max_iterations_with_pr_status(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=1)

        chunk = MagicMock()
        chunk.content = "Partial.\nSATISFIED: no"

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(
            hand, "_finalize_repo_pr", return_value={"pr_status": "error"}
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "PR status: error" in text

    def test_stream_interrupted_before_iteration(self, tmp_path) -> None:
        hand, _mock_agent = _make_langgraph_hand(tmp_path)

        # Interrupt after reset_interrupt runs but before first iteration
        orig_build = hand._build_bootstrap_context

        def interrupt_then_build():
            result = orig_build()
            hand.interrupt()
            return result

        hand._build_bootstrap_context = interrupt_then_build

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "[interrupted]" in text

    def test_stream_interrupted_mid_stream(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path)

        call_count = 0

        async def _fake_events(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            chunk = MagicMock()
            chunk.content = "working"
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}
            # Interrupt after first iteration's stream
            if call_count >= 1:
                hand.interrupt()

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "[interrupted]" in text

    def test_stream_yields_file_changes_and_tool_results(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=1)

        chunk = MagicMock()
        chunk.content = (
            "@@FILE: main.py\n```python\nprint('hi')\n```\n"
            "@@READ: main.py\n"
            "SATISFIED: no"
        )

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "[files updated]" in text
        assert "[tool results]" in text

    def test_stream_satisfied_no_pr_url_no_changes(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=2)

        chunk = MagicMock()
        chunk.content = "Done.\nSATISFIED: yes"

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(
            hand, "_finalize_repo_pr", return_value={"pr_status": "no_changes"}
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Task marked satisfied" in text
        assert "PR created" not in text
        assert "PR status" not in text

    def test_stream_auth_header(self, tmp_path) -> None:
        hand, mock_agent = _make_langgraph_hand(tmp_path, max_iterations=1)

        chunk = MagicMock()
        chunk.content = "SATISFIED: yes"

        async def _fake_events(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "data": {"chunk": chunk}}

        mock_agent.astream_events = _fake_events

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        first = chunks[0]
        assert "[basic-langgraph]" in first
        assert "provider=" in first


# ---------------------------------------------------------------------------
# BasicAtomicHand.stream() — coverage for lines 795-900
# ---------------------------------------------------------------------------


class TestBasicAtomicHandStream:
    def test_stream_satisfied_first_iteration(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=3)

        partial = MagicMock()
        partial.chat_message = "Done.\nSATISFIED: yes"

        async def _fake_run_async(_input):
            yield partial

        mock_agent.run_async = _fake_run_async

        with patch.object(
            hand, "_finalize_repo_pr", return_value={"pr_url": "https://pr/2"}
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Task marked satisfied" in text
        assert "PR created" in text

    def test_stream_max_iterations(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=2)

        partial = MagicMock()
        partial.chat_message = "Working.\nSATISFIED: no"

        async def _fake_run_async(_input):
            yield partial

        mock_agent.run_async = _fake_run_async

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Max iterations reached" in text

    def test_stream_interrupted(self, tmp_path) -> None:
        hand, _mock_agent = _make_atomic_hand(tmp_path)

        orig_build = hand._build_bootstrap_context

        def interrupt_then_build():
            result = orig_build()
            hand.interrupt()
            return result

        hand._build_bootstrap_context = interrupt_then_build

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "[interrupted]" in text

    def test_stream_assertion_error_fallback(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        sync_partial = MagicMock()
        sync_partial.chat_message = "Sync fallback.\nSATISFIED: yes"

        def _sync_run(_input):
            return sync_partial

        def _async_raise(_input):
            raise AssertionError("async not supported")

        mock_agent.run_async = _async_raise
        mock_agent.run = _sync_run

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Sync fallback" in text

    def test_stream_awaitable_result(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        partial = MagicMock()
        partial.chat_message = "Awaited.\nSATISFIED: yes"

        async def _fake_run_async(_input):
            return partial

        mock_agent.run_async = _fake_run_async

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Awaited" in text

    def test_stream_awaitable_assertion_fallback(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        sync_partial = MagicMock()
        sync_partial.chat_message = "Sync via await fallback.\nSATISFIED: yes"

        async def _fake_run_async(_input):
            raise AssertionError("not supported")

        def _sync_run(_input):
            return sync_partial

        mock_agent.run_async = _fake_run_async
        mock_agent.run = _sync_run

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "Sync via await fallback" in text

    def test_stream_pr_status_on_max_iterations(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        partial = MagicMock()
        partial.chat_message = "Partial.\nSATISFIED: no"

        async def _fake_run_async(_input):
            yield partial

        mock_agent.run_async = _fake_run_async

        with patch.object(
            hand, "_finalize_repo_pr", return_value={"pr_status": "error"}
        ):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        text = "".join(chunks)
        assert "PR status: error" in text

    def test_stream_auth_header(self, tmp_path) -> None:
        hand, mock_agent = _make_atomic_hand(tmp_path, max_iterations=1)

        partial = MagicMock()
        partial.chat_message = "SATISFIED: yes"

        async def _fake_run_async(_input):
            yield partial

        mock_agent.run_async = _fake_run_async

        with patch.object(hand, "_finalize_repo_pr", return_value={}):
            chunks = asyncio.run(_collect_stream(hand, "task"))

        first = chunks[0]
        assert "[basic-atomic]" in first
        assert "provider=" in first
