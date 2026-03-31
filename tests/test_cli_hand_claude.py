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
