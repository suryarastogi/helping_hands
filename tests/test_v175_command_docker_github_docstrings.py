"""Enforce Google-style docstring coverage on command.py helpers, DockerSandboxClaudeCodeHand, and github.py.

These tests protect the contract that every private helper in command.py carries
Args/Returns/Raises sections, and that DockerSandboxClaudeCodeHand's key methods
(including __init__ and sandbox-control hooks) have descriptive documentation.
If docstrings on _run_command or _resolve_cwd regress, the security boundary
around subprocess execution becomes opaque and reviewers lose the Raises: contract
that documents which errors propagate to callers. The github.py dunder checks
similarly ensure the GitHub client's identity comparison semantics are documented.
"""

from __future__ import annotations

import inspect

import pytest

# ---------------------------------------------------------------------------
# command.py private helper docstrings
# ---------------------------------------------------------------------------

_COMMAND_HELPERS = [
    "_normalize_args",
    "_resolve_cwd",
    "_resolve_python_command",
    "_run_command",
]


class TestCommandHelperDocstrings:
    """All command.py private helpers must have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _COMMAND_HELPERS)
    def test_has_docstring(self, func_name: str) -> None:
        from helping_hands.lib.meta.tools import command

        func = getattr(command, func_name)
        doc = inspect.getdoc(func)
        assert doc, f"command.{func_name} missing docstring"
        assert len(doc) > 20, f"command.{func_name} docstring too short"

    @pytest.mark.parametrize(
        ("func_name", "expected_sections"),
        [
            ("_normalize_args", ["Args:", "Returns:", "Raises:"]),
            ("_resolve_cwd", ["Args:", "Returns:", "Raises:"]),
            ("_resolve_python_command", ["Args:", "Returns:", "Raises:"]),
            ("_run_command", ["Args:", "Returns:", "Raises:"]),
        ],
    )
    def test_has_expected_sections(
        self, func_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.meta.tools import command

        func = getattr(command, func_name)
        doc = inspect.getdoc(func) or ""
        for section in expected_sections:
            assert section in doc, (
                f"command.{func_name} docstring missing {section} section"
            )


# ---------------------------------------------------------------------------
# docker_sandbox_claude.py method docstrings
# ---------------------------------------------------------------------------

_DOCKER_SANDBOX_METHODS = [
    "__init__",
    "_should_cleanup",
    "_execution_mode",
    "_fallback_command_when_not_found",
]


class TestDockerSandboxDocstrings:
    """DockerSandboxClaudeCodeHand new docstrings must be present."""

    @pytest.mark.parametrize("method_name", _DOCKER_SANDBOX_METHODS)
    def test_has_docstring(self, method_name: str) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        method = getattr(DockerSandboxClaudeCodeHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"DockerSandboxClaudeCodeHand.{method_name} missing docstring"
        assert len(doc) > 10, (
            f"DockerSandboxClaudeCodeHand.{method_name} docstring too short"
        )

    @pytest.mark.parametrize(
        ("method_name", "expected_sections"),
        [
            ("__init__", ["Args:"]),
            ("_should_cleanup", ["Returns:"]),
            ("_execution_mode", ["Returns:"]),
            ("_fallback_command_when_not_found", ["Args:", "Returns:"]),
        ],
    )
    def test_has_expected_sections(
        self, method_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        method = getattr(DockerSandboxClaudeCodeHand, method_name)
        doc = inspect.getdoc(method) or ""
        for section in expected_sections:
            assert section in doc, (
                f"DockerSandboxClaudeCodeHand.{method_name} "
                f"docstring missing {section} section"
            )


# ---------------------------------------------------------------------------
# github.py dunder method docstrings
# ---------------------------------------------------------------------------

_GITHUB_DUNDERS = [
    "__post_init__",
    "__enter__",
    "__exit__",
]


class TestGitHubClientDunderDocstrings:
    """GitHubClient dunder methods must have docstrings."""

    @pytest.mark.parametrize("method_name", _GITHUB_DUNDERS)
    def test_has_docstring(self, method_name: str) -> None:
        from helping_hands.lib.github import GitHubClient

        method = getattr(GitHubClient, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"GitHubClient.{method_name} missing docstring"
        assert len(doc) > 10, f"GitHubClient.{method_name} docstring too short"

    def test_post_init_has_raises_section(self) -> None:
        from helping_hands.lib.github import GitHubClient

        doc = inspect.getdoc(GitHubClient.__post_init__) or ""
        assert "Raises:" in doc, (
            "GitHubClient.__post_init__ docstring missing Raises: section"
        )
