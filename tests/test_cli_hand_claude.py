"""Tests for ClaudeCodeHand static/pure helper methods.

ClaudeCodeHand wraps the `claude` CLI and adds Claude-specific logic: the
--dangerously-skip-permissions flag injection (with root-user safety guard),
stream-json output parsing (_StreamJsonEmitter), GPT model filtering, and the
npx fallback when the `claude` binary is not on PATH. A regression in
_skip_permissions_enabled causes either silent permission prompts (the AI
stalls waiting for user input) or a crash when running as root. The
_StreamJsonEmitter tests protect live-streaming output: if the JSON event
parsing breaks, users see no output during long Claude runs. The
--dangerously-skip-permissions retry logic covers the specific case where
Claude reports the flag is disallowed at runtime and must be stripped for the
retry.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from helping_hands.lib.hands.v1.hand.cli.claude import (
    _DEFAULT_BUDGET_TOKENS,
    _DEFAULT_MAX_TURNS_RESUME_LIMIT,
    ClaudeCodeHand,
    _StreamJsonEmitter,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def claude_hand(make_cli_hand):
    return make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# _build_claude_failure_message
# ---------------------------------------------------------------------------


class TestBuildClaudeFailureMessage:
    def test_generic_failure(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="some error"
        )
        assert "Claude Code CLI failed (exit=1)" in msg
        assert "some error" in msg

    def test_auth_failure_401(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg
        assert "ANTHROPIC_API_KEY" in msg

    def test_auth_failure_invalid_key(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="Error: invalid api key provided"
        )
        assert "authentication failed" in msg

    def test_auth_failure_anthropic_key_mention(self) -> None:
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output="missing ANTHROPIC_API_KEY"
        )
        assert "authentication failed" in msg

    def test_output_truncated_to_2000(self) -> None:
        long_output = "x" * 5000
        msg = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output=long_output
        )
        # The tail should be at most 2000 chars of the output
        assert len(msg) < 5000


# ---------------------------------------------------------------------------
# _resolve_cli_model
# ---------------------------------------------------------------------------


class TestResolveCliModel:
    def test_filters_gpt_models(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="gpt-5.2")
        assert hand._resolve_cli_model() == ""

    def test_filters_gpt_case_insensitive(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="GPT-4o")
        assert hand._resolve_cli_model() == ""

    def test_preserves_claude_model(self, claude_hand) -> None:
        result = claude_hand._resolve_cli_model()
        assert result == "claude-sonnet-4-5"

    def test_default_model_returns_opus(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="default")
        # _DEFAULT_MODEL is "claude-opus-4-6"
        result = hand._resolve_cli_model()
        assert result == "claude-opus-4-6"

    def test_empty_default_model_returns_empty(self, make_cli_hand) -> None:
        """When _DEFAULT_MODEL is empty and model is 'default', returns ''."""
        hand = make_cli_hand(ClaudeCodeHand, model="default")
        hand._DEFAULT_MODEL = ""
        assert hand._resolve_cli_model() == ""


# ---------------------------------------------------------------------------
# _skip_permissions_enabled
# ---------------------------------------------------------------------------


class TestSkipPermissionsEnabled:
    def test_defaults_to_true(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        # Default is "1" (truthy), and we're not root
        assert claude_hand._skip_permissions_enabled() is True

    def test_disabled_when_env_is_0(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", "0")
        assert claude_hand._skip_permissions_enabled() is False

    def test_disabled_when_env_is_false(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", "false")
        assert claude_hand._skip_permissions_enabled() is False

    def test_disabled_when_root(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        monkeypatch.setattr("os.geteuid", lambda: 0)
        assert claude_hand._skip_permissions_enabled() is False

    def test_enabled_when_geteuid_raises(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )

        def _broken_geteuid():
            raise OSError("geteuid unavailable")

        monkeypatch.setattr("os.geteuid", _broken_geteuid)
        assert claude_hand._skip_permissions_enabled() is True

    def test_enabled_when_geteuid_not_callable(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        monkeypatch.delattr("os.geteuid", raising=False)
        assert claude_hand._skip_permissions_enabled() is True


# ---------------------------------------------------------------------------
# _build_failure_message (instance delegation)
# ---------------------------------------------------------------------------


class TestBuildFailureMessageInstance:
    def test_delegates_to_static_method(self, claude_hand) -> None:
        msg = claude_hand._build_failure_message(
            return_code=1, output="401 Unauthorized"
        )
        assert "authentication failed" in msg
        assert "ANTHROPIC_API_KEY" in msg

    def test_generic_error_delegation(self, claude_hand) -> None:
        msg = claude_hand._build_failure_message(
            return_code=42, output="something broke"
        )
        assert "Claude Code CLI failed (exit=42)" in msg


# ---------------------------------------------------------------------------
# _apply_backend_defaults
# ---------------------------------------------------------------------------


class TestApplyBackendDefaults:
    def test_injects_skip_permissions(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        cmd = ["claude", "-p", "do stuff"]
        result = claude_hand._apply_backend_defaults(cmd)
        assert "--dangerously-skip-permissions" in result
        assert result[0] == "claude"

    def test_no_inject_when_already_present(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "do stuff"]
        result = claude_hand._apply_backend_defaults(cmd)
        assert result.count("--dangerously-skip-permissions") == 1

    def test_no_inject_for_non_claude_cmd(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv(
            "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", raising=False
        )
        cmd = ["npx", "-y", "@anthropic-ai/claude-code", "-p", "stuff"]
        result = claude_hand._apply_backend_defaults(cmd)
        assert "--dangerously-skip-permissions" not in result

    def test_no_inject_when_disabled(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS", "0")
        cmd = ["claude", "-p", "do stuff"]
        result = claude_hand._apply_backend_defaults(cmd)
        assert "--dangerously-skip-permissions" not in result


# ---------------------------------------------------------------------------
# _retry_command_after_failure
# ---------------------------------------------------------------------------


class TestRetryCommandAfterFailure:
    def test_retries_on_root_permission_error(self, claude_hand) -> None:
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "hi"]
        output = (
            "Error: --dangerously-skip-permissions cannot be used "
            "with root/sudo privileges"
        )
        result = claude_hand._retry_command_after_failure(
            cmd, output=output, return_code=1
        )
        assert result is not None
        assert "--dangerously-skip-permissions" not in result
        assert result == ["claude", "-p", "hi"]

    def test_no_retry_on_success(self, claude_hand) -> None:
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "hi"]
        result = claude_hand._retry_command_after_failure(
            cmd, output="all good", return_code=0
        )
        assert result is None

    def test_no_retry_without_skip_permissions_flag(self, claude_hand) -> None:
        cmd = ["claude", "-p", "hi"]
        output = "--dangerously-skip-permissions cannot be used with root/sudo"
        result = claude_hand._retry_command_after_failure(
            cmd, output=output, return_code=1
        )
        assert result is None

    def test_no_retry_on_other_error(self, claude_hand) -> None:
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "hi"]
        result = claude_hand._retry_command_after_failure(
            cmd, output="network error", return_code=1
        )
        assert result is None


# ---------------------------------------------------------------------------
# _no_change_error_after_retries
# ---------------------------------------------------------------------------


class TestNoChangeErrorAfterRetries:
    def test_detects_permission_prompt_markers(self, claude_hand) -> None:
        for marker in ClaudeCodeHand._PERMISSION_PROMPT_MARKERS:
            result = claude_hand._no_change_error_after_retries(
                prompt="fix bugs", combined_output=f"Output: {marker}"
            )
            assert result is not None
            assert "write permission" in result

    def test_returns_none_for_normal_output(self, claude_hand) -> None:
        result = claude_hand._no_change_error_after_retries(
            prompt="fix bugs", combined_output="completed successfully"
        )
        assert result is None


# ---------------------------------------------------------------------------
# _fallback_command_when_not_found
# ---------------------------------------------------------------------------


class TestFallbackCommandWhenNotFound:
    def test_falls_back_to_npx_when_available(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda name: "/usr/bin/npx" if name == "npx" else None
        )
        cmd = ["claude", "-p", "hello"]
        result = claude_hand._fallback_command_when_not_found(cmd)
        assert result is not None
        assert result[0] == "npx"
        assert "@anthropic-ai/claude-code" in result

    def test_no_fallback_when_npx_missing(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda name: None)
        cmd = ["claude", "-p", "hello"]
        result = claude_hand._fallback_command_when_not_found(cmd)
        assert result is None

    def test_no_fallback_for_non_claude_cmd(self, claude_hand) -> None:
        cmd = ["other-tool", "-p", "hello"]
        result = claude_hand._fallback_command_when_not_found(cmd)
        assert result is None


# ---------------------------------------------------------------------------
# _inject_output_format
# ---------------------------------------------------------------------------


class TestInjectOutputFormat:
    def test_injects_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_output_format(cmd, "stream-json")
        assert result == ["claude", "--output-format", "stream-json", "-p", "hello"]

    def test_no_inject_when_already_present(self) -> None:
        cmd = ["claude", "--output-format", "text", "-p", "hello"]
        result = ClaudeCodeHand._inject_output_format(cmd, "stream-json")
        assert result == cmd

    def test_no_inject_with_equals_syntax(self) -> None:
        cmd = ["claude", "--output-format=text", "-p", "hello"]
        result = ClaudeCodeHand._inject_output_format(cmd, "stream-json")
        assert result == cmd

    def test_appends_when_no_p_flag(self) -> None:
        cmd = ["claude", "hello"]
        result = ClaudeCodeHand._inject_output_format(cmd, "stream-json")
        assert "--output-format" in result
        assert "stream-json" in result


# ---------------------------------------------------------------------------
# _StreamJsonEmitter async processing
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterProcessing:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_assistant_text_event(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Hello world"}]},
            }
        )
        self._run(parser(event + "\n"))
        assert any("Hello world" in e for e in emitted)

    def test_assistant_tool_use_event(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/src/app.py"},
                        }
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        assert any("Read /src/app.py" in e for e in emitted)

    def test_user_tool_result_event(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": "file contents here",
                        }
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        assert any("file contents here" in e for e in emitted)

    def test_user_tool_result_list_content(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": [
                                {"text": "part1"},
                                {"text": "part2"},
                            ],
                        }
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        assert any("part1" in e for e in emitted)

    def test_result_event_captures_result(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "final answer",
                "total_cost_usd": 0.05,
                "duration_ms": 12000,
            }
        )
        self._run(parser(event + "\n"))
        assert parser.result_text() == "final answer"
        assert any("$0.0500" in e for e in emitted)
        assert any("12.0s" in e for e in emitted)

    def test_non_json_line_passed_through(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        self._run(parser("verbose log line\n"))
        assert any("verbose log line" in e for e in emitted)

    def test_flush_processes_remaining_buffer(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        # Send data without trailing newline
        self._run(parser("partial data"))
        assert len(emitted) == 0
        self._run(parser.flush())
        assert any("partial data" in e for e in emitted)

    def test_result_text_falls_back_to_text_parts(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "accumulated text"}]},
            }
        )
        self._run(parser(event + "\n"))
        assert parser.result_text() == "accumulated text"

    def test_result_text_empty_when_no_data(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        assert parser.result_text() == ""

    def test_text_preview_truncated_at_200(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        long_text = "a" * 300
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": long_text}]},
            }
        )
        self._run(parser(event + "\n"))
        # Preview should be truncated to 197 + "..."
        text_emissions = [e for e in emitted if "[test]" in e]
        assert text_emissions
        assert "..." in text_emissions[0]

    def test_user_tool_result_long_content_truncated(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        long_content = "b" * 300
        event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [{"type": "tool_result", "content": long_content}]
                },
            }
        )
        self._run(parser(event + "\n"))
        result_emissions = [e for e in emitted if "->" in e]
        assert result_emissions
        assert "..." in result_emissions[0]


# ---------------------------------------------------------------------------
# _command_not_found_message
# ---------------------------------------------------------------------------


class TestCommandNotFoundMessage:
    def test_includes_command_name(self, claude_hand) -> None:
        msg = claude_hand._command_not_found_message("claude")
        assert "claude" in msg
        assert "HELPING_HANDS_CLAUDE_CLI_CMD" in msg

    def test_includes_repr_of_custom_command(self, claude_hand) -> None:
        msg = claude_hand._command_not_found_message("/usr/bin/claude-custom")
        assert "/usr/bin/claude-custom" in msg


# ---------------------------------------------------------------------------
# _native_cli_auth_env_names
# ---------------------------------------------------------------------------


class TestNativeCliAuthEnvNames:
    def test_returns_anthropic_api_key(self, claude_hand) -> None:
        result = claude_hand._native_cli_auth_env_names()
        assert result == ("ANTHROPIC_API_KEY",)


# ---------------------------------------------------------------------------
# _pr_description_cmd
# ---------------------------------------------------------------------------


class TestPrDescriptionCmd:
    def test_returns_cmd_when_claude_available(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda name: "/usr/bin/claude" if name == "claude" else None
        )
        result = claude_hand._pr_description_cmd()
        assert result == ["claude", "-p", "--output-format", "text"]

    def test_returns_none_when_claude_not_found(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setattr("shutil.which", lambda name: None)
        result = claude_hand._pr_description_cmd()
        assert result is None


# ---------------------------------------------------------------------------
# _StreamJsonEmitter edge cases
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterEdgeCases:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_empty_text_block_not_emitted(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": ""}]},
            }
        )
        self._run(parser(event + "\n"))
        # Empty text should not produce a [test] emission
        text_emissions = [e for e in emitted if "[test]" in e]
        assert text_emissions == []

    def test_result_event_without_cost_or_duration(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "result", "result": "done"})
        self._run(parser(event + "\n"))
        assert parser.result_text() == "done"
        # No api summary line when cost/duration are absent
        api_emissions = [e for e in emitted if "api:" in e]
        assert api_emissions == []

    def test_result_event_with_only_cost(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "result", "result": "done", "total_cost_usd": 0.01})
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        assert len(api_emissions) == 1
        assert "$0.0100" in api_emissions[0]

    def test_result_event_with_usage_tokens(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "total_cost_usd": 0.05,
                "duration_ms": 5000,
                "usage": {"input_tokens": 1200, "output_tokens": 300},
            }
        )
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        assert len(api_emissions) == 1
        assert "in=1200" in api_emissions[0]
        assert "out=300" in api_emissions[0]
        assert "$0.0500" in api_emissions[0]
        assert "5.0s" in api_emissions[0]

    def test_result_event_with_usage_input_only(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "usage": {"input_tokens": 500},
            }
        )
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        assert len(api_emissions) == 1
        assert "in=500" in api_emissions[0]
        assert "out=" not in api_emissions[0]

    def test_result_event_with_usage_output_only(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "usage": {"output_tokens": 150},
            }
        )
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        assert len(api_emissions) == 1
        assert "out=150" in api_emissions[0]
        assert "in=" not in api_emissions[0]

    def test_result_event_with_non_dict_usage_ignored(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "usage": "not-a-dict",
            }
        )
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        # No cost/duration/tokens, so no api line
        assert api_emissions == []

    def test_result_event_with_empty_usage_dict(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "usage": {},
            }
        )
        self._run(parser(event + "\n"))
        api_emissions = [e for e in emitted if "api:" in e]
        # Empty usage dict has no tokens, no cost/duration either
        assert api_emissions == []

    def test_user_tool_result_empty_content_skipped(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "tool_result", "content": "   "}]},
            }
        )
        self._run(parser(event + "\n"))
        # Whitespace-only content should not produce a -> emission
        result_emissions = [e for e in emitted if "->" in e]
        assert result_emissions == []

    def test_user_event_non_tool_result_block_skipped(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "ignored user text"}]},
            }
        )
        self._run(parser(event + "\n"))
        # Non-tool_result blocks in user events produce no output
        assert emitted == []

    def test_tool_result_list_with_non_dict_items(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "content": [
                                {"text": "valid"},
                                "not-a-dict",
                                42,
                            ],
                        }
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        result_emissions = [e for e in emitted if "->" in e]
        assert len(result_emissions) == 1
        assert "valid" in result_emissions[0]

    def test_flush_on_empty_buffer_is_noop(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        self._run(parser.flush())
        assert emitted == []

    def test_multiple_newlines_in_single_chunk(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        line1 = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "first"}]},
            }
        )
        line2 = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "second"}]},
            }
        )
        self._run(parser(line1 + "\n" + line2 + "\n"))
        text_emissions = [e for e in emitted if "[test]" in e]
        assert len(text_emissions) == 2
        assert "first" in text_emissions[0]
        assert "second" in text_emissions[1]

    def test_unknown_event_type_produces_no_output(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "system", "data": "ignored"})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_unknown_content_block_type_skipped(self) -> None:
        """Content blocks with unknown type (not tool_use/text) are skipped."""
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "image", "source": {"data": "base64..."}},
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        # Unknown block types produce no labeled emission
        text_emissions = [e for e in emitted if "[test]" in e]
        assert text_emissions == []

    def test_whitespace_only_text_preview_not_emitted(self) -> None:
        """Text that is truthy but becomes empty after strip produces no emission."""
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "\n\n  \n"}]},
            }
        )
        self._run(parser(event + "\n"))
        # Text is truthy ("\n\n  \n") but after strip/replace it becomes ""
        text_emissions = [e for e in emitted if "[test]" in e]
        assert text_emissions == []
        # The text should still be captured in _text_parts
        assert len(parser._text_parts) == 1

    def test_empty_lines_between_events_skipped(self) -> None:
        """Lines that are blank after stripping should be silently skipped."""
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "hello"}]},
            }
        )
        # Chunk with blank lines between valid JSON lines
        self._run(parser(event + "\n\n   \n" + event + "\n"))
        text_emissions = [e for e in emitted if "[test]" in e]
        # Only the two valid events should produce output, blank lines skipped
        assert len(text_emissions) == 2


# ---------------------------------------------------------------------------
# _invoke_claude / _invoke_backend async tests
# ---------------------------------------------------------------------------


class TestInvokeClaude:
    def test_invoke_claude_wires_emitter_and_returns_result(
        self, claude_hand, monkeypatch
    ) -> None:
        captured_cmd: list[str] = []

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            captured_cmd.extend(cmd)
            # Simulate stream-json output
            result_event = json.dumps(
                {"type": "result", "result": "task done", "total_cost_usd": 0.02}
            )
            await emit(result_event + "\n")
            return "raw fallback"

        monkeypatch.setattr(
            claude_hand, "_invoke_cli_with_cmd", fake_invoke_cli_with_cmd
        )
        monkeypatch.setattr(
            claude_hand,
            "_render_command",
            lambda prompt: ["claude", "-p", prompt],
        )

        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        result = asyncio.run(claude_hand._invoke_claude("fix bug", emit=emit))
        assert result == "task done"
        # Command should have --output-format stream-json injected
        assert "--output-format" in captured_cmd
        assert "stream-json" in captured_cmd

    def test_invoke_claude_falls_back_to_raw(self, claude_hand, monkeypatch) -> None:
        """When no result event is parsed, falls back to raw CLI output."""

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            # No stream-json events, just raw output
            await emit("plain text output\n")
            return "raw result"

        monkeypatch.setattr(
            claude_hand, "_invoke_cli_with_cmd", fake_invoke_cli_with_cmd
        )
        monkeypatch.setattr(
            claude_hand,
            "_render_command",
            lambda prompt: ["claude", "-p", prompt],
        )

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(claude_hand._invoke_claude("fix bug", emit=emit))
        assert result == "raw result"

    def test_invoke_backend_delegates_to_invoke_claude(
        self, claude_hand, monkeypatch
    ) -> None:
        calls: list[str] = []

        async def fake_invoke_claude(prompt, *, emit):
            calls.append(prompt)
            return "delegated"

        monkeypatch.setattr(claude_hand, "_invoke_claude", fake_invoke_claude)

        async def emit(text: str) -> None:
            pass

        result = asyncio.run(claude_hand._invoke_backend("hello", emit=emit))
        assert result == "delegated"
        assert calls == ["hello"]

    def test_invoke_claude_flushes_parser_on_error(
        self, claude_hand, monkeypatch
    ) -> None:
        """Parser flush runs even when _invoke_cli_with_cmd raises."""

        async def failing_invoke(cmd, *, emit):
            # Feed partial buffer (no trailing newline) then crash
            await emit("partial data without newline")
            raise RuntimeError("subprocess crashed")

        monkeypatch.setattr(claude_hand, "_invoke_cli_with_cmd", failing_invoke)
        monkeypatch.setattr(
            claude_hand,
            "_render_command",
            lambda prompt: ["claude", "-p", prompt],
        )

        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        with pytest.raises(RuntimeError, match="subprocess crashed"):
            asyncio.run(claude_hand._invoke_claude("fix bug", emit=emit))

        # The partial buffer should have been flushed despite the error
        assert any("partial data" in e for e in emitted)


# ---------------------------------------------------------------------------
# _StreamJsonEmitter non-dict message defense
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterNonDictMessage:
    """Defensive handling when message field is not a dict."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_assistant_event_with_string_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "assistant", "message": "not a dict"})
        self._run(parser(event + "\n"))
        # Should silently skip — no crash, no emission
        assert emitted == []

    def test_assistant_event_with_null_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "assistant", "message": None})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_assistant_event_with_missing_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "assistant"})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_assistant_event_with_list_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "assistant", "message": [1, 2, 3]})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_user_event_with_string_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "user", "message": "not a dict"})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_user_event_with_null_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "user", "message": None})
        self._run(parser(event + "\n"))
        assert emitted == []

    def test_user_event_with_missing_message(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "user"})
        self._run(parser(event + "\n"))
        assert emitted == []


# ---------------------------------------------------------------------------
# _StreamJsonEmitter._summarize_tool (direct tests)
# ---------------------------------------------------------------------------


class TestSummarizeTool:
    def test_read_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Read", {"file_path": "/a/b.py"})
            == "Read /a/b.py"
        )

    def test_edit_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Edit", {"file_path": "/x.py"})
            == "Edit /x.py"
        )

    def test_write_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Write", {"file_path": "/out.txt"})
            == "Write /out.txt"
        )

    def test_bash_tool(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": "ls -la"})
        assert result == "$ ls -la"

    def test_bash_tool_truncates_long_command(self) -> None:
        long_cmd = "x" * 100
        result = _StreamJsonEmitter._summarize_tool("Bash", {"command": long_cmd})
        assert result.startswith("$ ")
        assert result.endswith("...")
        assert len(result) <= 82  # "$ " + 77 + "..."

    def test_glob_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Glob", {"pattern": "**/*.py"})
            == "Glob **/*.py"
        )

    def test_grep_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("Grep", {"pattern": "TODO"})
            == "Grep /TODO/"
        )

    def test_agent_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "Agent", {"description": "search codebase"}
            )
            == "Agent: search codebase"
        )

    def test_agent_tool_no_description(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("Agent", {}) == "Agent"

    def test_web_fetch_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "WebFetch", {"url": "https://example.com"}
            )
            == "WebFetch https://example.com"
        )

    def test_web_search_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("WebSearch", {"query": "python async"})
            == "WebSearch 'python async'"
        )

    def test_web_search_tool_no_query(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("WebSearch", {}) == "WebSearch"

    def test_notebook_edit_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "NotebookEdit", {"notebook_path": "/nb.ipynb"}
            )
            == "NotebookEdit /nb.ipynb"
        )

    def test_todo_write_tool(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("TodoWrite", {}) == "TodoWrite"

    def test_multi_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "MultiTool", {"tool_uses": [{"name": "a"}, {"name": "b"}]}
            )
            == "MultiTool (2 tools)"
        )

    def test_multi_tool_non_list(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("MultiTool", {"tool_uses": "bad"})
            == "MultiTool (0 tools)"
        )

    def test_unknown_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("SomeNewTool", {}) == "tool: SomeNewTool"
        )

    def test_missing_input_fields_default_to_empty(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("Read", {}) == "Read "
        assert _StreamJsonEmitter._summarize_tool("Bash", {}) == "$ "
        assert _StreamJsonEmitter._summarize_tool("Glob", {}) == "Glob "
        assert _StreamJsonEmitter._summarize_tool("Grep", {}) == "Grep //"

    # v123 — new tool type summarizations

    def test_cron_create_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "CronCreate", {"prompt": "run tests every hour"}
            )
            == "CronCreate 'run tests every hour'"
        )

    def test_cron_create_tool_truncates_long_prompt(self) -> None:
        long_prompt = "x" * 100
        result = _StreamJsonEmitter._summarize_tool(
            "CronCreate", {"prompt": long_prompt}
        )
        assert result.startswith("CronCreate '")
        assert result.endswith("...'")

    def test_cron_create_tool_no_prompt(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("CronCreate", {}) == "CronCreate"

    def test_cron_delete_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("CronDelete", {"id": "abc123"})
            == "CronDelete abc123"
        )

    def test_cron_delete_tool_no_id(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("CronDelete", {}) == "CronDelete"

    def test_cron_list_tool(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("CronList", {}) == "CronList"

    def test_enter_worktree_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "EnterWorktree", {"name": "feature-branch"}
            )
            == "EnterWorktree feature-branch"
        )

    def test_enter_worktree_tool_no_name(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("EnterWorktree", {}) == "EnterWorktree"
        )

    def test_exit_worktree_tool(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("ExitWorktree", {"action": "merge"})
            == "ExitWorktree merge"
        )

    def test_exit_worktree_tool_no_action(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("ExitWorktree", {}) == "ExitWorktree"


# ---------------------------------------------------------------------------
# _inject_output_format edge cases
# ---------------------------------------------------------------------------


class TestInjectOutputFormatEdgeCases:
    def test_empty_cmd(self) -> None:
        result = ClaudeCodeHand._inject_output_format([], "stream-json")
        assert result == ["--output-format", "stream-json"]


# ---------------------------------------------------------------------------
# _resolve_max_turns
# ---------------------------------------------------------------------------


class TestResolveMaxTurns:
    def test_default_unlimited(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MAX_TURNS", raising=False)
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_valid_positive_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "25")
        assert ClaudeCodeHand._resolve_max_turns() == 25

    def test_zero_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "0")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_negative_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "-5")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_non_integer_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "abc")
        assert ClaudeCodeHand._resolve_max_turns() == 0

    def test_whitespace_only_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS", "   ")
        assert ClaudeCodeHand._resolve_max_turns() == 0


# ---------------------------------------------------------------------------
# _inject_max_turns
# ---------------------------------------------------------------------------


class TestInjectMaxTurns:
    def test_injects_before_p_flag(self) -> None:
        cmd = ["claude", "--dangerously-skip-permissions", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 10)
        assert "--max-turns" in result
        assert result[result.index("--max-turns") + 1] == "10"
        # --max-turns should appear before -p
        assert result.index("--max-turns") < result.index("-p")

    def test_zero_max_turns_skips_injection(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 0)
        assert "--max-turns" not in result

    def test_already_present_skips_injection(self) -> None:
        cmd = ["claude", "--max-turns", "5", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 10)
        # Should not add a second --max-turns
        assert result.count("--max-turns") == 1
        assert result[result.index("--max-turns") + 1] == "5"

    def test_no_p_flag_appends(self) -> None:
        cmd = ["claude", "do stuff"]
        result = ClaudeCodeHand._inject_max_turns(cmd, 15)
        assert "--max-turns" in result
        assert result[result.index("--max-turns") + 1] == "15"


# ---------------------------------------------------------------------------
# _resolve_system_prompt / _inject_system_prompt
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_explicit_env_var_takes_priority(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", "custom instructions")
        assert claude_hand._resolve_system_prompt() == "custom instructions"

    def test_reads_agent_md(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        agent_md = claude_hand.repo_index.root / "AGENT.md"
        agent_md.write_text("# Agent Guidelines\nDo good things.")
        result = claude_hand._resolve_system_prompt()
        assert "Agent Guidelines" in result

    def test_reads_claude_md_as_fallback(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        claude_md = claude_hand.repo_index.root / "CLAUDE.md"
        claude_md.write_text("# Claude Instructions\nBe helpful.")
        result = claude_hand._resolve_system_prompt()
        assert "Claude Instructions" in result

    def test_agent_md_takes_priority_over_claude_md(
        self, claude_hand, monkeypatch
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        (claude_hand.repo_index.root / "AGENT.md").write_text("agent doc")
        (claude_hand.repo_index.root / "CLAUDE.md").write_text("claude doc")
        result = claude_hand._resolve_system_prompt()
        assert result == "agent doc"

    def test_empty_when_no_files(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        assert claude_hand._resolve_system_prompt() == ""

    def test_truncates_long_content(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        (claude_hand.repo_index.root / "AGENT.md").write_text("x" * 20000)
        result = claude_hand._resolve_system_prompt()
        assert len(result) < 20000
        assert result.endswith("...[truncated]")

    def test_inject_system_prompt_inserts_before_p(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_system_prompt(cmd, "be careful")
        assert "--append-system-prompt" in result
        assert result.index("--append-system-prompt") < result.index("-p")

    def test_inject_system_prompt_skips_empty(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_system_prompt(cmd, "")
        assert "--append-system-prompt" not in result

    def test_inject_system_prompt_skips_if_already_present(self) -> None:
        cmd = ["claude", "--append-system-prompt", "existing", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_system_prompt(cmd, "new prompt")
        assert result.count("--append-system-prompt") == 1

    def test_inject_system_prompt_skips_if_system_prompt_present(self) -> None:
        cmd = ["claude", "--system-prompt", "existing", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_system_prompt(cmd, "new prompt")
        assert "--append-system-prompt" not in result


# ---------------------------------------------------------------------------
# _resolve_tool_filters / _inject_tool_filters
# ---------------------------------------------------------------------------


class TestToolFilters:
    def test_empty_when_no_env(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)
        allowed, disallowed = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == []
        assert disallowed == []

    def test_parses_allowed_tools(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", "Bash,Read,Write")
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)
        allowed, disallowed = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == ["Bash", "Read", "Write"]
        assert disallowed == []

    def test_parses_disallowed_tools(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", raising=False)
        monkeypatch.setenv(
            "HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", "WebFetch,WebSearch"
        )
        allowed, disallowed = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == []
        assert disallowed == ["WebFetch", "WebSearch"]

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", " Bash , Read ")
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)
        allowed, _ = ClaudeCodeHand._resolve_tool_filters()
        assert allowed == ["Bash", "Read"]

    def test_inject_tool_filters_inserts_both(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=["Bash", "Read"], disallowed=["WebFetch"]
        )
        assert "--allowedTools" in result
        assert "Bash,Read" in result
        assert "--disallowedTools" in result
        assert "WebFetch" in result
        assert result.index("--allowedTools") < result.index("-p")

    def test_inject_tool_filters_skips_empty(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_tool_filters(cmd, allowed=[], disallowed=[])
        assert "--allowedTools" not in result
        assert "--disallowedTools" not in result

    def test_inject_tool_filters_respects_existing(self) -> None:
        cmd = ["claude", "--allowedTools", "Bash", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_tool_filters(
            cmd, allowed=["Read"], disallowed=[]
        )
        assert result.count("--allowedTools") == 1


# ---------------------------------------------------------------------------
# Session continue / --continue support
# ---------------------------------------------------------------------------


class TestSessionContinue:
    def test_session_continue_enabled_default(self, claude_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", raising=False)
        assert claude_hand._session_continue_enabled() is True

    def test_session_continue_disabled(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_SESSION_CONTINUE", "0")
        assert claude_hand._session_continue_enabled() is False

    def test_inject_continue_session_replaces_p_flag(self) -> None:
        cmd = ["claude", "--output-format", "stream-json", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_continue_session(cmd, "sess-abc123")
        assert "--continue" in result
        assert "-p" not in result
        assert "--session-id" in result
        assert "sess-abc123" in result

    def test_inject_continue_session_skips_empty_id(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_continue_session(cmd, "")
        assert result == cmd

    def test_inject_continue_session_skips_if_continue_present(self) -> None:
        cmd = ["claude", "--continue", "do stuff"]
        result = ClaudeCodeHand._inject_continue_session(cmd, "sess-abc123")
        assert result.count("--continue") == 1

    def test_inject_continue_session_skips_if_resume_present(self) -> None:
        cmd = ["claude", "--resume", "sess-xyz"]
        result = ClaudeCodeHand._inject_continue_session(cmd, "sess-abc123")
        # Should not modify
        assert "--session-id" not in result


# ---------------------------------------------------------------------------
# _StreamJsonEmitter session_id and cost_metadata
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterMetadata:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_session_id_captured(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "session_id": "sess-12345678",
                "total_cost_usd": 0.05,
            }
        )
        self._run(parser(event + "\n"))
        assert parser.session_id == "sess-12345678"

    def test_session_id_empty_when_not_present(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "result", "result": "done"})
        self._run(parser(event + "\n"))
        assert parser.session_id == ""

    def test_cost_metadata_captured(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "total_cost_usd": 0.1234,
                "duration_ms": 5000,
                "usage": {"input_tokens": 100, "output_tokens": 200},
            }
        )
        self._run(parser(event + "\n"))
        meta = parser.cost_metadata
        assert meta["total_cost_usd"] == pytest.approx(0.1234)
        assert meta["duration_ms"] == pytest.approx(5000.0)
        assert meta["usage"]["input_tokens"] == 100
        assert meta["usage"]["output_tokens"] == 200

    def test_cost_metadata_empty_when_no_result(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        assert parser.cost_metadata == {}


# ---------------------------------------------------------------------------
# Cost accumulation
# ---------------------------------------------------------------------------


class TestCostAccumulation:
    def test_accumulates_across_invocations(self, claude_hand, monkeypatch) -> None:
        call_count = 0

        async def fake_invoke_cli_with_cmd(cmd, *, emit):
            nonlocal call_count
            call_count += 1
            event = json.dumps(
                {
                    "type": "result",
                    "result": f"result-{call_count}",
                    "total_cost_usd": 0.01 * call_count,
                    "usage": {
                        "input_tokens": 100 * call_count,
                        "output_tokens": 50 * call_count,
                    },
                    "session_id": f"sess-{call_count}",
                }
            )
            await emit(event + "\n")
            return ""

        monkeypatch.setattr(
            claude_hand, "_invoke_cli_with_cmd", fake_invoke_cli_with_cmd
        )
        monkeypatch.setattr(
            claude_hand,
            "_render_command",
            lambda prompt: ["claude", "-p", prompt],
        )
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MAX_TURNS", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_SYSTEM_PROMPT", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_ALLOWED_TOOLS", raising=False)
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_DISALLOWED_TOOLS", raising=False)

        async def emit(text: str) -> None:
            pass

        asyncio.run(claude_hand._invoke_claude("first", emit=emit))
        asyncio.run(claude_hand._invoke_claude("second", emit=emit))

        assert claude_hand._cumulative_cost_usd == pytest.approx(0.03)
        assert claude_hand._cumulative_input_tokens == 300
        assert claude_hand._cumulative_output_tokens == 150
        assert claude_hand._last_session_id == "sess-2"


# ---------------------------------------------------------------------------
# _resolve_mcp_config / _inject_mcp_config
# ---------------------------------------------------------------------------


class TestMcpConfig:
    def test_empty_when_no_env(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MCP_CONFIG", raising=False)
        assert ClaudeCodeHand._resolve_mcp_config() == ""

    def test_returns_path_when_file_exists(self, monkeypatch, tmp_path) -> None:
        config_file = tmp_path / "mcp.json"
        config_file.write_text('{"mcpServers": {}}')
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MCP_CONFIG", str(config_file))
        result = ClaudeCodeHand._resolve_mcp_config()
        assert result == str(config_file.resolve())

    def test_empty_when_file_missing(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv(
            "HELPING_HANDS_CLAUDE_MCP_CONFIG", str(tmp_path / "nonexistent.json")
        )
        assert ClaudeCodeHand._resolve_mcp_config() == ""

    def test_empty_when_file_too_large(self, monkeypatch, tmp_path) -> None:
        config_file = tmp_path / "huge.json"
        config_file.write_text("x" * (64 * 1024 + 1))
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MCP_CONFIG", str(config_file))
        assert ClaudeCodeHand._resolve_mcp_config() == ""

    def test_inject_mcp_config_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "/path/to/mcp.json")
        assert "--mcp-config" in result
        assert "/path/to/mcp.json" in result
        assert result.index("--mcp-config") < result.index("-p")

    def test_inject_mcp_config_skips_empty(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "")
        assert "--mcp-config" not in result

    def test_inject_mcp_config_skips_if_already_present(self) -> None:
        cmd = ["claude", "--mcp-config", "/existing.json", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "/new.json")
        assert result.count("--mcp-config") == 1

    def test_inject_mcp_config_no_p_flag(self) -> None:
        cmd = ["claude", "do stuff"]
        result = ClaudeCodeHand._inject_mcp_config(cmd, "/path/to/mcp.json")
        assert "--mcp-config" in result
        assert "/path/to/mcp.json" in result


# ---------------------------------------------------------------------------
# _resolve_thinking_budget / _inject_thinking_budget
# ---------------------------------------------------------------------------


class TestThinkingBudget:
    def test_default_omit(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", raising=False)
        assert ClaudeCodeHand._resolve_thinking_budget() == 0

    def test_valid_positive_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "10000")
        assert ClaudeCodeHand._resolve_thinking_budget() == 10000

    def test_zero_returns_omit(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "0")
        assert ClaudeCodeHand._resolve_thinking_budget() == 0

    def test_negative_returns_omit(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "-100")
        assert ClaudeCodeHand._resolve_thinking_budget() == 0

    def test_non_integer_returns_omit(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "abc")
        assert ClaudeCodeHand._resolve_thinking_budget() == 0

    def test_whitespace_only_returns_omit(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_THINKING_BUDGET", "   ")
        assert ClaudeCodeHand._resolve_thinking_budget() == 0

    def test_inject_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_thinking_budget(cmd, 8000)
        assert "--thinking-budget-tokens" in result
        assert result[result.index("--thinking-budget-tokens") + 1] == "8000"
        assert result.index("--thinking-budget-tokens") < result.index("-p")

    def test_zero_budget_skips(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_thinking_budget(cmd, 0)
        assert "--thinking-budget-tokens" not in result

    def test_already_present_skips(self) -> None:
        cmd = ["claude", "--thinking-budget-tokens", "5000", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_thinking_budget(cmd, 10000)
        assert result.count("--thinking-budget-tokens") == 1
        assert result[result.index("--thinking-budget-tokens") + 1] == "5000"


# ---------------------------------------------------------------------------
# _resolve_permission_mode / _inject_permission_mode
# ---------------------------------------------------------------------------


class TestPermissionMode:
    def test_empty_when_no_env(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_PERMISSION_MODE", raising=False)
        assert ClaudeCodeHand._resolve_permission_mode() == ""

    def test_reads_env_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_PERMISSION_MODE", "plan")
        assert ClaudeCodeHand._resolve_permission_mode() == "plan"

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_PERMISSION_MODE", "  default  ")
        assert ClaudeCodeHand._resolve_permission_mode() == "default"

    def test_inject_before_p_flag(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "plan")
        assert "--permission-mode" in result
        assert "plan" in result
        assert result.index("--permission-mode") < result.index("-p")

    def test_inject_skips_empty(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "")
        assert "--permission-mode" not in result

    def test_inject_skips_if_already_present(self) -> None:
        cmd = ["claude", "--permission-mode", "default", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_permission_mode(cmd, "plan")
        assert result.count("--permission-mode") == 1


# ---------------------------------------------------------------------------
# _inject_resume_session
# ---------------------------------------------------------------------------


class TestResumeSession:
    def test_replaces_p_with_resume_and_removes_prompt(self) -> None:
        cmd = ["claude", "--output-format", "stream-json", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_resume_session(cmd, "sess-abc123")
        assert "--resume" in result
        assert "-p" not in result
        assert "do stuff" not in result
        assert "--session-id" in result
        assert "sess-abc123" in result

    def test_skips_empty_session_id(self) -> None:
        cmd = ["claude", "-p", "do stuff"]
        result = ClaudeCodeHand._inject_resume_session(cmd, "")
        assert result == cmd

    def test_skips_if_resume_already_present(self) -> None:
        cmd = ["claude", "--resume"]
        result = ClaudeCodeHand._inject_resume_session(cmd, "sess-abc123")
        assert result.count("--resume") == 1

    def test_skips_if_continue_present(self) -> None:
        cmd = ["claude", "--continue", "do more stuff"]
        result = ClaudeCodeHand._inject_resume_session(cmd, "sess-abc123")
        assert "--resume" not in result

    def test_no_p_flag_returns_unchanged(self) -> None:
        cmd = ["claude", "do stuff"]
        result = ClaudeCodeHand._inject_resume_session(cmd, "sess-abc123")
        assert result == cmd


# ---------------------------------------------------------------------------
# _StreamJsonEmitter system event and subagent tracking
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterNewFeatures:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_system_event_captures_model(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "system", "model": "claude-opus-4-6"})
        self._run(parser(event + "\n"))
        assert parser.model == "claude-opus-4-6"

    def test_system_event_empty_model_ignored(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "system", "model": ""})
        self._run(parser(event + "\n"))
        assert parser.model == ""

    def test_system_event_non_string_model_ignored(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "system", "model": 42})
        self._run(parser(event + "\n"))
        assert parser.model == ""

    def test_result_event_captures_is_error(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {"type": "result", "result": "error occurred", "is_error": True}
        )
        self._run(parser(event + "\n"))
        assert parser.is_error is True

    def test_result_event_is_error_defaults_false(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps({"type": "result", "result": "done"})
        self._run(parser(event + "\n"))
        assert parser.is_error is False

    def test_subagent_count_tracks_agent_tool(self) -> None:
        emitted: list[str] = []

        async def emit(text: str) -> None:
            emitted.append(text)

        parser = _StreamJsonEmitter(emit, "test")
        for i in range(3):
            event = json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Agent",
                                "input": {"description": f"task {i}"},
                            }
                        ]
                    },
                }
            )
            self._run(parser(event + "\n"))
        assert parser.total_subagents == 3

    def test_non_agent_tool_does_not_count(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/a.py"},
                        }
                    ]
                },
            }
        )
        self._run(parser(event + "\n"))
        assert parser.total_subagents == 0


# ---------------------------------------------------------------------------
# New tool summary entries (ToolSearch, SendMessage, TaskOutput, TaskStop)
# ---------------------------------------------------------------------------


class TestSummarizeToolNew:
    def test_tool_search(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("ToolSearch", {"query": "select:Read"})
            == "ToolSearch 'select:Read'"
        )

    def test_tool_search_no_query(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("ToolSearch", {}) == "ToolSearch"

    def test_send_message(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("SendMessage", {"to": "agent-123"})
            == "SendMessage -> agent-123"
        )

    def test_send_message_no_to(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("SendMessage", {}) == "SendMessage"

    def test_task_output(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("TaskOutput", {"id": "task-456"})
            == "TaskOutput task-456"
        )

    def test_task_output_no_id(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("TaskOutput", {}) == "TaskOutput"

    def test_task_stop(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("TaskStop", {"id": "task-789"})
            == "TaskStop task-789"
        )

    def test_task_stop_no_id(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("TaskStop", {}) == "TaskStop"

    def test_ask_user_question(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool(
                "AskUserQuestion", {"question": "What should I do?"}
            )
            == "AskUserQuestion What should I do?"
        )

    def test_enter_plan_mode(self) -> None:
        assert (
            _StreamJsonEmitter._summarize_tool("EnterPlanMode", {}) == "EnterPlanMode"
        )

    def test_exit_plan_mode(self) -> None:
        assert _StreamJsonEmitter._summarize_tool("ExitPlanMode", {}) == "ExitPlanMode"


# ---------------------------------------------------------------------------
# _resolve_cli_model — bedrock/vertex provider prefixes
# ---------------------------------------------------------------------------


class TestResolveCliModelProviderPrefixes:
    def test_bedrock_prefix_passes_through(self, make_cli_hand) -> None:
        hand = make_cli_hand(
            ClaudeCodeHand, model="bedrock:us.anthropic.claude-sonnet-4-5"
        )
        assert hand._resolve_cli_model() == "bedrock:us.anthropic.claude-sonnet-4-5"

    def test_vertex_prefix_passes_through(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="vertex:claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "vertex:claude-sonnet-4-5"

    def test_gemini_model_filtered(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="gemini-2.5-pro")
        assert hand._resolve_cli_model() == ""

    def test_google_prefix_filtered(self, make_cli_hand) -> None:
        hand = make_cli_hand(ClaudeCodeHand, model="google/gemini-2.5-pro")
        assert hand._resolve_cli_model() == ""


# ---------------------------------------------------------------------------
# --add-dir support
# ---------------------------------------------------------------------------


class TestInjectAddDirs:
    def test_no_dirs_returns_unchanged(self) -> None:
        cmd = ["claude", "-p", "hello"]
        assert ClaudeCodeHand._inject_add_dirs(cmd, []) == cmd

    def test_single_dir_injected(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_add_dirs(cmd, ["/tmp/ref"])
        assert result == ["claude", "--add-dir", "/tmp/ref", "-p", "hello"]

    def test_multiple_dirs_injected(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_add_dirs(cmd, ["/tmp/a", "/tmp/b"])
        assert result == [
            "claude",
            "--add-dir",
            "/tmp/a",
            "--add-dir",
            "/tmp/b",
            "-p",
            "hello",
        ]

    def test_no_p_flag_appends_at_end(self) -> None:
        cmd = ["claude", "hello"]
        result = ClaudeCodeHand._inject_add_dirs(cmd, ["/tmp/ref"])
        assert result == ["claude", "hello", "--add-dir", "/tmp/ref"]


# ---------------------------------------------------------------------------
# --prefill support
# ---------------------------------------------------------------------------


class TestResolvePrefill:
    def test_empty_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_PREFILL", raising=False)
        assert ClaudeCodeHand._resolve_prefill() == ""

    def test_returns_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_PREFILL", "I'll start by")
        assert ClaudeCodeHand._resolve_prefill() == "I'll start by"

    def test_truncates_long_prefill(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_PREFILL", "x" * 3000)
        result = ClaudeCodeHand._resolve_prefill()
        assert len(result) == 2000


class TestInjectPrefill:
    def test_empty_prefill_unchanged(self) -> None:
        cmd = ["claude", "-p", "hello"]
        assert ClaudeCodeHand._inject_prefill(cmd, "") == cmd

    def test_prefill_injected(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_prefill(cmd, "Sure, I'll")
        assert result == ["claude", "--prefill", "Sure, I'll", "-p", "hello"]

    def test_skips_if_already_present(self) -> None:
        cmd = ["claude", "--prefill", "existing", "-p", "hello"]
        result = ClaudeCodeHand._inject_prefill(cmd, "other")
        assert result == cmd


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — thinking block visibility
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterThinking:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_thinking_block_emitted(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "Let me analyze this code..."}
                    ]
                },
            }
        )
        self._run(emitter(event + "\n"))
        assert any("thinking:" in c for c in collected)
        assert any("analyze" in c for c in collected)


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — cache token tracking
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterCacheTokens:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_cache_tokens_captured(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "total_cost_usd": 0.05,
                "duration_ms": 5000,
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cache_creation_input_tokens": 200,
                    "cache_read_input_tokens": 800,
                },
            }
        )
        self._run(emitter(event + "\n"))
        meta = emitter.cost_metadata
        assert meta["usage"]["cache_creation_input_tokens"] == 200
        assert meta["usage"]["cache_read_input_tokens"] == 800
        # Verify cache info in emitted output
        assert any("cache_write=200" in c for c in collected)
        assert any("cache_read=800" in c for c in collected)

    def test_no_cache_tokens_when_absent(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "total_cost_usd": 0.01,
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
        )
        self._run(emitter(event + "\n"))
        meta = emitter.cost_metadata
        assert "cache_creation_input_tokens" not in meta.get("usage", {})
        assert "cache_read_input_tokens" not in meta.get("usage", {})


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — is_error handling
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterIsError:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_is_error_captured(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "Error: something went wrong",
                "is_error": True,
                "total_cost_usd": 0.01,
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.is_error is True
        assert "something went wrong" in emitter.result_text()


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — num_turns tracking
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterNumTurns:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_counts_assistant_events_as_turns(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        for i in range(5):
            event = json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": f"turn {i}"}]},
                }
            )
            self._run(parser(event + "\n"))
        assert parser.num_turns == 5

    def test_zero_turns_initially(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        assert parser.num_turns == 0

    def test_non_assistant_events_not_counted(self) -> None:
        async def emit(text: str) -> None:
            pass

        parser = _StreamJsonEmitter(emit, "test")
        for event_type in ("user", "result", "system"):
            event = json.dumps({"type": event_type, "result": "x"})
            self._run(parser(event + "\n"))
        assert parser.num_turns == 0


# ---------------------------------------------------------------------------
# Per-backend model override (HELPING_HANDS_CLAUDE_MODEL)
# ---------------------------------------------------------------------------


class TestModelEnvVarOverride:
    def test_env_var_takes_precedence(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MODEL", "claude-haiku-4-5")
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-haiku-4-5"

    def test_env_var_empty_falls_through(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MODEL", "")
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_env_var_default_marker_falls_through(
        self, make_cli_hand, monkeypatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MODEL", "default")
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"

    def test_env_var_gpt_model_rejected(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MODEL", "gpt-5.2")
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == ""

    def test_env_var_bedrock_prefix_passes(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.setenv(
            "HELPING_HANDS_CLAUDE_MODEL", "bedrock:us.anthropic.claude-sonnet-4-5"
        )
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "bedrock:us.anthropic.claude-sonnet-4-5"

    def test_env_var_not_set_uses_config(self, make_cli_hand, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MODEL", raising=False)
        hand = make_cli_hand(ClaudeCodeHand, model="claude-sonnet-4-5")
        assert hand._resolve_cli_model() == "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# Cost budget
# ---------------------------------------------------------------------------


class TestCostBudget:
    def test_default_unlimited(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_COST_BUDGET", raising=False)
        assert ClaudeCodeHand._resolve_cost_budget() == 0.0

    def test_valid_positive_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "5.50")
        assert ClaudeCodeHand._resolve_cost_budget() == 5.50

    def test_zero_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "0")
        assert ClaudeCodeHand._resolve_cost_budget() == 0.0

    def test_negative_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "-1.5")
        assert ClaudeCodeHand._resolve_cost_budget() == 0.0

    def test_non_numeric_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "abc")
        assert ClaudeCodeHand._resolve_cost_budget() == 0.0

    def test_whitespace_only_returns_unlimited(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "   ")
        assert ClaudeCodeHand._resolve_cost_budget() == 0.0

    def test_cost_budget_exceeded_when_over(self, claude_hand, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "1.00")
        claude_hand._cumulative_cost_usd = 1.50
        assert claude_hand._cost_budget_exceeded() is True

    def test_cost_budget_not_exceeded_when_under(
        self, claude_hand, monkeypatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_COST_BUDGET", "5.00")
        claude_hand._cumulative_cost_usd = 2.00
        assert claude_hand._cost_budget_exceeded() is False

    def test_cost_budget_not_exceeded_when_unlimited(
        self, claude_hand, monkeypatch
    ) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_COST_BUDGET", raising=False)
        claude_hand._cumulative_cost_usd = 100.0
        assert claude_hand._cost_budget_exceeded() is False


# ---------------------------------------------------------------------------
# Max-turns auto-resume
# ---------------------------------------------------------------------------


class TestMaxTurnsResume:
    def test_default_resume_limit(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_MAX_TURNS_RESUME", raising=False)
        assert (
            ClaudeCodeHand._resolve_max_turns_resume_limit()
            == _DEFAULT_MAX_TURNS_RESUME_LIMIT
        )

    def test_valid_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS_RESUME", "5")
        assert ClaudeCodeHand._resolve_max_turns_resume_limit() == 5

    def test_zero_disables(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS_RESUME", "0")
        assert ClaudeCodeHand._resolve_max_turns_resume_limit() == 0

    def test_negative_clamped_to_zero(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS_RESUME", "-2")
        assert ClaudeCodeHand._resolve_max_turns_resume_limit() == 0

    def test_non_integer_uses_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_MAX_TURNS_RESUME", "abc")
        assert (
            ClaudeCodeHand._resolve_max_turns_resume_limit()
            == _DEFAULT_MAX_TURNS_RESUME_LIMIT
        )

    def test_max_turns_exhausted_true(self, claude_hand) -> None:
        claude_hand._last_num_turns = 10
        assert claude_hand._max_turns_exhausted(10) is True

    def test_max_turns_exhausted_false_under(self, claude_hand) -> None:
        claude_hand._last_num_turns = 5
        assert claude_hand._max_turns_exhausted(10) is False

    def test_max_turns_exhausted_false_unlimited(self, claude_hand) -> None:
        claude_hand._last_num_turns = 100
        assert claude_hand._max_turns_exhausted(0) is False


# ---------------------------------------------------------------------------
# --budget-tokens
# ---------------------------------------------------------------------------


class TestBudgetTokens:
    def test_default_omit(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", raising=False)
        assert ClaudeCodeHand._resolve_budget_tokens() == _DEFAULT_BUDGET_TOKENS

    def test_valid_positive_value(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", "50000")
        assert ClaudeCodeHand._resolve_budget_tokens() == 50000

    def test_zero_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", "0")
        assert ClaudeCodeHand._resolve_budget_tokens() == 0

    def test_negative_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", "-100")
        assert ClaudeCodeHand._resolve_budget_tokens() == 0

    def test_non_integer_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", "abc")
        assert ClaudeCodeHand._resolve_budget_tokens() == 0

    def test_whitespace_only_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_BUDGET_TOKENS", "   ")
        assert ClaudeCodeHand._resolve_budget_tokens() == 0


class TestInjectBudgetTokens:
    def test_zero_budget_skips(self) -> None:
        cmd = ["claude", "-p", "hello"]
        assert ClaudeCodeHand._inject_budget_tokens(cmd, 0) == cmd

    def test_injects_before_p(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_budget_tokens(cmd, 50000)
        assert result == ["claude", "--budget-tokens", "50000", "-p", "hello"]

    def test_skips_if_already_present(self) -> None:
        cmd = ["claude", "--budget-tokens", "10000", "-p", "hello"]
        result = ClaudeCodeHand._inject_budget_tokens(cmd, 50000)
        assert result == cmd

    def test_appends_when_no_p_flag(self) -> None:
        cmd = ["claude"]
        result = ClaudeCodeHand._inject_budget_tokens(cmd, 50000)
        assert result == ["claude", "--budget-tokens", "50000"]


# ---------------------------------------------------------------------------
# --cwd working directory
# ---------------------------------------------------------------------------


class TestCwd:
    def test_default_empty(self, monkeypatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_CLAUDE_CWD", raising=False)
        assert ClaudeCodeHand._resolve_cwd() == ""

    def test_valid_directory(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CWD", str(tmp_path))
        assert ClaudeCodeHand._resolve_cwd() == str(tmp_path)

    def test_nonexistent_directory_skipped(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CWD", str(tmp_path / "nonexistent"))
        assert ClaudeCodeHand._resolve_cwd() == ""

    def test_whitespace_only_returns_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_CLAUDE_CWD", "   ")
        assert ClaudeCodeHand._resolve_cwd() == ""


class TestInjectCwd:
    def test_empty_cwd_unchanged(self) -> None:
        cmd = ["claude", "-p", "hello"]
        assert ClaudeCodeHand._inject_cwd(cmd, "") == cmd

    def test_cwd_injected(self) -> None:
        cmd = ["claude", "-p", "hello"]
        result = ClaudeCodeHand._inject_cwd(cmd, "/tmp/myrepo")
        assert result == ["claude", "--cwd", "/tmp/myrepo", "-p", "hello"]

    def test_skips_if_already_present(self) -> None:
        cmd = ["claude", "--cwd", "/other", "-p", "hello"]
        result = ClaudeCodeHand._inject_cwd(cmd, "/tmp/myrepo")
        assert result == cmd


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — error subtype and retryable classification
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterErrorClassification:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_error_subtype_captured(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "Rate limit exceeded",
                "is_error": True,
                "subtype": "rate_limit",
                "total_cost_usd": 0.01,
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.error_subtype == "rate_limit"
        assert emitter.is_retryable_error is True

    def test_non_retryable_error(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "Authentication failed",
                "is_error": True,
                "subtype": "auth_error",
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.error_subtype == "auth_error"
        assert emitter.is_retryable_error is False

    def test_retryable_by_result_text_pattern(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "Error: overloaded, please try again",
                "is_error": True,
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.error_subtype == ""
        assert emitter.is_retryable_error is True

    def test_not_retryable_when_no_error(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "Success",
                "is_error": False,
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.is_retryable_error is False

    def test_no_subtype_when_absent(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.error_subtype == ""


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — thinking token tracking
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterThinkingTokens:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_thinking_tokens_accumulated(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        # Two thinking blocks with token counts.
        for tokens in (500, 300):
            event = json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "thinking",
                                "thinking": "analyzing...",
                                "tokens": tokens,
                            }
                        ]
                    },
                }
            )
            self._run(emitter(event + "\n"))
        assert emitter.thinking_tokens == 800

    def test_thinking_tokens_zero_when_absent(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        event = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "thinking", "thinking": "no tokens field"}]
                },
            }
        )
        self._run(emitter(event + "\n"))
        assert emitter.thinking_tokens == 0


# ---------------------------------------------------------------------------
# _StreamJsonEmitter — subagent lifecycle tracking
# ---------------------------------------------------------------------------


class TestStreamJsonEmitterSubagentLifecycle:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_active_subagents_increments_and_decrements(self) -> None:
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        emitter = _StreamJsonEmitter(emit, "test")
        # Launch two subagents.
        for desc in ("research", "implement"):
            event = json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Agent",
                                "input": {"description": desc},
                            }
                        ]
                    },
                }
            )
            self._run(emitter(event + "\n"))
        assert emitter.total_subagents == 2
        assert emitter.active_subagents == 2

        # One subagent completes.
        result_event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "name": "Agent",
                            "content": "done",
                        }
                    ]
                },
            }
        )
        self._run(emitter(result_event + "\n"))
        assert emitter.active_subagents == 1
        assert emitter.total_subagents == 2

    def test_active_subagents_does_not_go_negative(self) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        # Tool result without a preceding tool_use — should not go negative.
        result_event = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "name": "Agent",
                            "content": "done",
                        }
                    ]
                },
            }
        )
        self._run(emitter(result_event + "\n"))
        assert emitter.active_subagents == 0


# ---------------------------------------------------------------------------
# Cumulative thinking token tracking in ClaudeCodeHand
# ---------------------------------------------------------------------------


class TestCumulativeThinkingTokens:
    def test_accumulate_includes_thinking(self, claude_hand) -> None:
        async def emit(chunk: str) -> None:
            pass

        emitter = _StreamJsonEmitter(emit, "test")
        # Simulate thinking tokens via the internal field.
        emitter._thinking_tokens = 1200
        # Simulate a result event for cost metadata.
        event = json.dumps(
            {
                "type": "result",
                "result": "done",
                "total_cost_usd": 0.05,
                "usage": {"input_tokens": 1000, "output_tokens": 500},
            }
        )
        asyncio.run(emitter(event + "\n"))
        claude_hand._accumulate_cost(emitter)
        assert claude_hand._cumulative_thinking_tokens == 1200
