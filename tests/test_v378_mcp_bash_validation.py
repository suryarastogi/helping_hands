"""Tests for MCP run_bash_script input validation branches.

Protects the mutual-exclusion contract in the ``run_bash_script`` MCP tool:
callers must provide exactly one of ``script_path`` or ``inline_script``.
Providing neither or both raises ``ValueError`` before any subprocess is
spawned, preventing accidental no-ops or ambiguous execution.

If these guards regress, an MCP agent could invoke ``run_bash_script`` with
contradictory arguments and either silently do nothing or execute an
unexpected script.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from helping_hands.server.mcp_server import run_bash_script


class TestRunBashScriptValidation:
    """Validate run_bash_script mutual-exclusion guards."""

    def test_raises_when_neither_provided(self, tmp_path: Path) -> None:
        """Neither script_path nor inline_script → ValueError."""
        with pytest.raises(ValueError, match="Either script_path or inline_script"):
            run_bash_script(str(tmp_path))

    def test_raises_when_both_provided(self, tmp_path: Path) -> None:
        """Both script_path and inline_script → ValueError."""
        with pytest.raises(ValueError, match="Cannot provide both"):
            run_bash_script(
                str(tmp_path),
                script_path="run.sh",
                inline_script="echo hi",
            )
