"""Tests for v271: the shared _format_cli_failure() helper.

Before this helper, each CLI hand constructed its own failure message by
inlining auth detection and formatting. If an auth-detection token (e.g.
"401 Unauthorized") was added or changed, every hand's _handle_cli_failure
override needed updating.

_format_cli_failure() centralises the auth-vs-generic branching and the Docker
env hint. The auth-detection tests ensure the function correctly classifies
"401", "unauthorized", etc. as auth failures (→ API key advice) rather than
generic failures (→ bare exit code). Regressions would cause users to see a
confusing generic exit-code message instead of "check your API key".
"""

from __future__ import annotations

import ast

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import (
    _format_cli_failure,
)

# ---------------------------------------------------------------------------
# _format_cli_failure — basic behaviour
# ---------------------------------------------------------------------------


class TestFormatCliFailure:
    """Unit tests for the _format_cli_failure() helper."""

    def test_generic_failure_includes_exit_code(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=42,
            output="something broke",
            env_var_hint="TEST_KEY",
        )
        assert "TestCLI failed (exit=42)" in msg

    def test_generic_failure_includes_output(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="some error text",
            env_var_hint="TEST_KEY",
        )
        assert "some error text" in msg

    def test_auth_failure_detected_from_shared_token(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="Error: 401 Unauthorized",
            env_var_hint="TEST_KEY",
        )
        assert "authentication failed" in msg

    def test_auth_failure_includes_env_var_hint(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="unauthorized access",
            env_var_hint="MY_API_KEY",
        )
        assert "MY_API_KEY" in msg

    def test_auth_failure_includes_docker_hint(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="unauthorized",
            env_var_hint="MY_API_KEY",
        )
        assert "Docker" in msg
        assert "MY_API_KEY" in msg

    def test_auth_failure_default_guidance(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="unauthorized",
            env_var_hint="MY_API_KEY",
        )
        assert "Ensure MY_API_KEY is set in this runtime." in msg

    def test_auth_failure_custom_guidance(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="unauthorized",
            env_var_hint="MY_API_KEY",
            auth_guidance="Run 'test auth login' to authenticate.",
        )
        assert "Run 'test auth login' to authenticate." in msg
        assert "Ensure MY_API_KEY is set" not in msg

    def test_extra_tokens_trigger_auth_detection(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="Missing Bearer authentication header",
            env_var_hint="TEST_KEY",
            extra_tokens=("missing bearer",),
        )
        assert "authentication failed" in msg

    def test_no_auth_without_matching_tokens(self) -> None:
        msg = _format_cli_failure(
            backend_name="TestCLI",
            return_code=1,
            output="timeout after 30s",
            env_var_hint="TEST_KEY",
        )
        assert "authentication failed" not in msg
        assert "TestCLI failed (exit=1)" in msg

    def test_backend_name_in_auth_message(self) -> None:
        msg = _format_cli_failure(
            backend_name="FooCLI",
            return_code=1,
            output="unauthorized",
            env_var_hint="FOO_KEY",
        )
        assert msg.startswith("FooCLI authentication failed.")

    def test_backend_name_in_generic_message(self) -> None:
        msg = _format_cli_failure(
            backend_name="FooCLI",
            return_code=2,
            output="crash",
            env_var_hint="FOO_KEY",
        )
        assert "FooCLI failed (exit=2)" in msg

    def test_return_type_is_str(self) -> None:
        result = _format_cli_failure(
            backend_name="X",
            return_code=1,
            output="err",
            env_var_hint="K",
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _format_cli_failure — __all__ export
# ---------------------------------------------------------------------------


class TestFormatCliFailureExport:
    """Verify _format_cli_failure is exported in cli/base.py __all__."""

    def test_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base as mod

        assert "_format_cli_failure" in mod.__all__

    def test_has_docstring(self) -> None:
        assert _format_cli_failure.__doc__ is not None
        assert "auth" in _format_cli_failure.__doc__.lower()


# ---------------------------------------------------------------------------
# Consistency: static methods delegate to _format_cli_failure
# ---------------------------------------------------------------------------


class TestStaticMethodDelegation:
    """Verify that the per-backend static methods produce identical output
    to calling _format_cli_failure directly."""

    def test_codex_auth_consistent(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        output = "Error: 401 Unauthorized"
        static = CodexCLIHand._build_codex_failure_message(return_code=1, output=output)
        direct = _format_cli_failure(
            backend_name="Codex CLI",
            return_code=1,
            output=output,
            env_var_hint="OPENAI_API_KEY",
            extra_tokens=("missing bearer or basic authentication",),
        )
        assert static == direct

    def test_codex_generic_consistent(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand

        output = "some timeout error"
        static = CodexCLIHand._build_codex_failure_message(return_code=2, output=output)
        direct = _format_cli_failure(
            backend_name="Codex CLI",
            return_code=2,
            output=output,
            env_var_hint="OPENAI_API_KEY",
            extra_tokens=("missing bearer or basic authentication",),
        )
        assert static == direct

    def test_claude_auth_consistent(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import ClaudeCodeHand

        output = "unauthorized"
        static = ClaudeCodeHand._build_claude_failure_message(
            return_code=1, output=output
        )
        direct = _format_cli_failure(
            backend_name="Claude Code CLI",
            return_code=1,
            output=output,
            env_var_hint="ANTHROPIC_API_KEY",
            extra_tokens=ClaudeCodeHand._EXTRA_AUTH_TOKENS,
        )
        assert static == direct

    def test_opencode_auth_consistent(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        output = "unauthorized"
        static = OpenCodeCLIHand._build_opencode_failure_message(
            return_code=1, output=output
        )
        direct = _format_cli_failure(
            backend_name="OpenCode CLI",
            return_code=1,
            output=output,
            env_var_hint="the appropriate API key",
            auth_guidance=(
                "Ensure your provider API key is set or run 'opencode auth login'."
            ),
        )
        assert static == direct


# ---------------------------------------------------------------------------
# AST: verify static methods delegate (no inline _detect_auth_failure calls)
# ---------------------------------------------------------------------------


class TestNoDuplicatedAuthDetection:
    """Verify that the refactored static methods no longer call
    _detect_auth_failure directly — they should delegate to
    _format_cli_failure instead."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "src/helping_hands/lib/hands/v1/hand/cli/codex.py",
            "src/helping_hands/lib/hands/v1/hand/cli/claude.py",
            "src/helping_hands/lib/hands/v1/hand/cli/opencode.py",
        ],
    )
    def test_no_direct_detect_auth_failure_call(self, module_path: str) -> None:
        with open(module_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                assert name != "_detect_auth_failure", (
                    f"{module_path} still calls _detect_auth_failure directly"
                )

    @pytest.mark.parametrize(
        "module_path",
        [
            "src/helping_hands/lib/hands/v1/hand/cli/codex.py",
            "src/helping_hands/lib/hands/v1/hand/cli/claude.py",
            "src/helping_hands/lib/hands/v1/hand/cli/opencode.py",
        ],
    )
    def test_no_docker_env_hint_template_import(self, module_path: str) -> None:
        with open(module_path) as f:
            source = f.read()
        assert "_DOCKER_ENV_HINT_TEMPLATE" not in source, (
            f"{module_path} still imports _DOCKER_ENV_HINT_TEMPLATE"
        )
