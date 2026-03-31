"""Enforce Google-style docstrings on ClaudeCodeHand and _StreamJsonEmitter.

_StreamJsonEmitter is the JSON-line parser that converts raw `claude --output-format
stream-json` output into streaming text chunks. Its _process_line method handles
multiple event types (assistant, result) with different extraction paths. Without
documented Args: and the list of recognised event types, contributors risk adding
new event types in the wrong branch. ClaudeCodeHand._resolve_cli_model guards the
GPT → Claude model-name translation that prevents non-Claude models from being
passed to the Claude CLI. _skip_permissions_enabled documents the dangerous
HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS env var that must stay under
controlled conditions (root user only).
"""

from __future__ import annotations

import pytest

from helping_hands.lib.hands.v1.hand.cli.claude import (
    ClaudeCodeHand,
    _StreamJsonEmitter,
)

# ---------------------------------------------------------------------------
# _StreamJsonEmitter docstring tests
# ---------------------------------------------------------------------------


# TODO: CLEANUP CANDIDATE — docstring-presence tests below; no runtime behavior.
class TestStreamJsonEmitterDocstrings:
    """Verify Google-style docstrings on _StreamJsonEmitter methods."""

    def test_call_has_docstring(self) -> None:
        assert _StreamJsonEmitter.__call__.__doc__ is not None

    def test_call_docstring_mentions_args(self) -> None:
        doc = _StreamJsonEmitter.__call__.__doc__
        assert "Args:" in doc

    def test_call_docstring_mentions_chunk(self) -> None:
        doc = _StreamJsonEmitter.__call__.__doc__
        assert "chunk" in doc

    def test_process_line_has_docstring(self) -> None:
        assert _StreamJsonEmitter._process_line.__doc__ is not None

    def test_process_line_docstring_mentions_args(self) -> None:
        doc = _StreamJsonEmitter._process_line.__doc__
        assert "Args:" in doc

    def test_process_line_docstring_mentions_event_types(self) -> None:
        doc = _StreamJsonEmitter._process_line.__doc__
        assert "assistant" in doc
        assert "result" in doc

    def test_result_text_has_docstring(self) -> None:
        assert _StreamJsonEmitter.result_text.__doc__ is not None

    def test_result_text_docstring_mentions_returns(self) -> None:
        doc = _StreamJsonEmitter.result_text.__doc__
        assert "Returns:" in doc


# ---------------------------------------------------------------------------
# ClaudeCodeHand docstring tests
# ---------------------------------------------------------------------------


# TODO: CLEANUP CANDIDATE — docstring-presence tests below; no runtime behavior.
class TestClaudeCodeHandDocstrings:
    """Verify Google-style docstrings on ClaudeCodeHand overrides."""

    def test_resolve_cli_model_has_docstring(self) -> None:
        assert ClaudeCodeHand._resolve_cli_model.__doc__ is not None

    def test_resolve_cli_model_docstring_mentions_gpt(self) -> None:
        doc = ClaudeCodeHand._resolve_cli_model.__doc__
        assert "GPT" in doc

    def test_resolve_cli_model_docstring_mentions_returns(self) -> None:
        doc = ClaudeCodeHand._resolve_cli_model.__doc__
        assert "Returns:" in doc

    def test_skip_permissions_has_docstring(self) -> None:
        assert ClaudeCodeHand._skip_permissions_enabled.__doc__ is not None

    def test_skip_permissions_docstring_mentions_env_var(self) -> None:
        doc = ClaudeCodeHand._skip_permissions_enabled.__doc__
        assert "HELPING_HANDS_CLAUDE_DANGEROUS_SKIP_PERMISSIONS" in doc

    def test_skip_permissions_docstring_mentions_root(self) -> None:
        doc = ClaudeCodeHand._skip_permissions_enabled.__doc__
        assert "root" in doc

    def test_skip_permissions_docstring_mentions_returns(self) -> None:
        doc = ClaudeCodeHand._skip_permissions_enabled.__doc__
        assert "Returns:" in doc


# ---------------------------------------------------------------------------
# MCP path_exists validation
# ---------------------------------------------------------------------------


class TestMcpPathExistsValidation:
    """Verify that MCP path_exists rejects empty/whitespace path."""

    def test_rejects_empty_path(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import path_exists

        with pytest.raises(ValueError, match="path"):
            path_exists(repo_path=str(tmp_path), path="")

    def test_rejects_whitespace_path(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import path_exists

        with pytest.raises(ValueError, match="path"):
            path_exists(repo_path=str(tmp_path), path="   ")

    def test_accepts_valid_path(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import path_exists

        (tmp_path / "hello.txt").write_text("hi")
        result = path_exists(repo_path=str(tmp_path), path="hello.txt")
        assert result is True

    def test_returns_false_for_missing_path(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import path_exists

        result = path_exists(repo_path=str(tmp_path), path="nonexistent.txt")
        assert result is False


# ---------------------------------------------------------------------------
# MCP run_bash_script validation
# ---------------------------------------------------------------------------


class TestMcpRunBashScriptValidation:
    """Verify that MCP run_bash_script rejects invalid script inputs."""

    def test_rejects_both_none(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        with pytest.raises(ValueError, match="Either script_path or inline_script"):
            run_bash_script(repo_path=str(tmp_path))

    def test_rejects_both_empty_strings(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        with pytest.raises(ValueError, match="Either script_path or inline_script"):
            run_bash_script(repo_path=str(tmp_path), script_path="", inline_script="")

    def test_rejects_both_provided(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        with pytest.raises(ValueError, match="Cannot provide both"):
            run_bash_script(
                repo_path=str(tmp_path),
                script_path="run.sh",
                inline_script="echo hi",
            )

    def test_accepts_inline_script(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        result = run_bash_script(repo_path=str(tmp_path), inline_script="echo hello")
        assert result["success"] is True
        assert "hello" in result["stdout"]

    def test_accepts_script_path(self, tmp_path) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        script = tmp_path / "test.sh"
        script.write_text("#!/bin/bash\necho script_output")
        script.chmod(0o755)
        result = run_bash_script(repo_path=str(tmp_path), script_path="test.sh")
        assert result["success"] is True
        assert "script_output" in result["stdout"]


# ---------------------------------------------------------------------------
# MCP path_exists docstring test
# ---------------------------------------------------------------------------


# TODO: CLEANUP CANDIDATE — docstring-presence tests below; no runtime behavior.
class TestMcpPathExistsDocstring:
    """Verify that MCP path_exists has a proper docstring."""

    def test_path_exists_has_docstring(self) -> None:
        from helping_hands.server.mcp_server import path_exists

        assert path_exists.__doc__ is not None

    def test_path_exists_docstring_mentions_args(self) -> None:
        from helping_hands.server.mcp_server import path_exists

        assert "Args:" in path_exists.__doc__

    def test_path_exists_docstring_mentions_returns(self) -> None:
        from helping_hands.server.mcp_server import path_exists

        assert "Returns:" in path_exists.__doc__


# ---------------------------------------------------------------------------
# MCP run_bash_script docstring test
# ---------------------------------------------------------------------------


# TODO: CLEANUP CANDIDATE — docstring-presence tests below; no runtime behavior.
class TestMcpRunBashScriptDocstring:
    """Verify that MCP run_bash_script has a proper docstring."""

    def test_run_bash_script_has_docstring(self) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        assert run_bash_script.__doc__ is not None

    def test_run_bash_script_docstring_mentions_args(self) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        assert "Args:" in run_bash_script.__doc__

    def test_run_bash_script_docstring_mentions_raises(self) -> None:
        from helping_hands.server.mcp_server import run_bash_script

        assert "Raises:" in run_bash_script.__doc__
