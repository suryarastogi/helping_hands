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
