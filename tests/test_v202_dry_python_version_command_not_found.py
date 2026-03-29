"""Guard that mcp_server.py uses the shared Python version constant and CLI hands inherit the Docker rebuild hint.

If mcp_server.py re-hardcodes `python_version: str = "3.13"` in its tool function
signatures, AI-generated code invoked via MCP would run under a different Python
version than the same code invoked through the CLI, producing inconsistent results.
The is-same-object test is stronger than a value comparison — it catches a copy that
happens to have the right value today but could diverge later. The
_command_not_found_message tests confirm that the Docker rebuild hint flows from the
base class to all CLI hand subclasses without requiring each to duplicate the message,
so a change to the template automatically reaches every subclass.
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import (
    _DOCKER_REBUILD_HINT_TEMPLATE,
    _TwoPhaseCLIHand,
)
from helping_hands.lib.meta.tools.command import (
    _DEFAULT_PYTHON_VERSION,
)

# ---------------------------------------------------------------------------
# _DEFAULT_PYTHON_VERSION in mcp_server.py
# ---------------------------------------------------------------------------


class TestDefaultPythonVersionInMcpServer:
    """Verify mcp_server.py uses _DEFAULT_PYTHON_VERSION from command.py."""

    def test_mcp_server_imports_constant(self) -> None:
        """mcp_server.py source contains the import."""
        src = inspect.getsource(
            __import__(
                "helping_hands.server.mcp_server",
                fromlist=["mcp"],
            )
        )
        assert "_DEFAULT_PYTHON_VERSION" in src

    def test_mcp_server_no_hardcoded_python_version(self) -> None:
        """mcp_server.py no longer hardcodes '3.13' as function defaults."""
        src = inspect.getsource(
            __import__(
                "helping_hands.server.mcp_server",
                fromlist=["mcp"],
            )
        )
        # Should not have python_version: str = "3.13" anymore
        assert 'python_version: str = "3.13"' not in src

    def test_constant_is_same_object(self) -> None:
        """The imported constant is the exact same object from command.py."""
        from helping_hands.server import mcp_server

        assert mcp_server._DEFAULT_PYTHON_VERSION is _DEFAULT_PYTHON_VERSION

    def test_constant_value_is_string(self) -> None:
        assert isinstance(_DEFAULT_PYTHON_VERSION, str)

    def test_constant_value_is_nonempty(self) -> None:
        assert len(_DEFAULT_PYTHON_VERSION) > 0


# ---------------------------------------------------------------------------
# Base _command_not_found_message includes Docker rebuild hint
# ---------------------------------------------------------------------------


class TestBaseCommandNotFoundMessage:
    """Verify _TwoPhaseCLIHand._command_not_found_message includes Docker hint."""

    def test_method_exists_on_base(self) -> None:
        assert hasattr(_TwoPhaseCLIHand, "_command_not_found_message")

    def test_base_source_references_docker_rebuild_template(self) -> None:
        src = inspect.getsource(_TwoPhaseCLIHand._command_not_found_message)
        assert "_DOCKER_REBUILD_HINT_TEMPLATE" in src

    def test_base_source_uses_command_param_for_hint(self) -> None:
        """The Docker hint is formatted with the ``command`` parameter."""
        src = inspect.getsource(_TwoPhaseCLIHand._command_not_found_message)
        assert "_DOCKER_REBUILD_HINT_TEMPLATE.format(command)" in src

    def test_message_contains_display_name(self) -> None:
        """Message starts with the CLI display name."""
        msg = _TwoPhaseCLIHand._command_not_found_message(
            _TwoPhaseCLIHand.__new__(_TwoPhaseCLIHand), "testbin"
        )
        assert _TwoPhaseCLIHand._CLI_DISPLAY_NAME in msg

    def test_message_contains_command(self) -> None:
        msg = _TwoPhaseCLIHand._command_not_found_message(
            _TwoPhaseCLIHand.__new__(_TwoPhaseCLIHand), "testbin"
        )
        assert "'testbin'" in msg

    def test_message_contains_env_var(self) -> None:
        msg = _TwoPhaseCLIHand._command_not_found_message(
            _TwoPhaseCLIHand.__new__(_TwoPhaseCLIHand), "testbin"
        )
        assert _TwoPhaseCLIHand._COMMAND_ENV_VAR in msg

    def test_message_contains_docker_rebuild_hint(self) -> None:
        msg = _TwoPhaseCLIHand._command_not_found_message(
            _TwoPhaseCLIHand.__new__(_TwoPhaseCLIHand), "testbin"
        )
        expected = _DOCKER_REBUILD_HINT_TEMPLATE.format("testbin")
        assert expected in msg


# ---------------------------------------------------------------------------
# Subclasses inherit base _command_not_found_message (no override)
# ---------------------------------------------------------------------------


_SUBCLASS_MODULES = [
    ("helping_hands.lib.hands.v1.hand.cli.claude", "ClaudeCodeHand"),
    ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand"),
    ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand"),
    ("helping_hands.lib.hands.v1.hand.cli.goose", "GooseCLIHand"),
    ("helping_hands.lib.hands.v1.hand.cli.opencode", "OpenCodeCLIHand"),
]


class TestSubclassesInheritCommandNotFound:
    """CLI hand subclasses no longer override _command_not_found_message."""

    @pytest.mark.parametrize(
        "module_path,class_name",
        _SUBCLASS_MODULES,
        ids=["claude", "codex", "gemini", "goose", "opencode"],
    )
    def test_no_override(self, module_path: str, class_name: str) -> None:
        """Subclass does not define its own _command_not_found_message."""
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        # Method should be inherited from base, not overridden
        assert "_command_not_found_message" not in cls.__dict__

    @pytest.mark.parametrize(
        "module_path,class_name",
        _SUBCLASS_MODULES,
        ids=["claude", "codex", "gemini", "goose", "opencode"],
    )
    def test_inherits_base_method(self, module_path: str, class_name: str) -> None:
        """Subclass resolves to the base class method."""
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        assert (
            cls._command_not_found_message
            is _TwoPhaseCLIHand._command_not_found_message
        )


# ---------------------------------------------------------------------------
# Message content verification for each subclass
# ---------------------------------------------------------------------------


class TestSubclassCommandNotFoundContent:
    """Verify the inherited message content for each CLI hand subclass."""

    @pytest.mark.parametrize(
        "module_path,class_name,binary_name",
        [
            (
                "helping_hands.lib.hands.v1.hand.cli.claude",
                "ClaudeCodeHand",
                "claude",
            ),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand", "codex"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand", "gemini"),
            ("helping_hands.lib.hands.v1.hand.cli.goose", "GooseCLIHand", "goose"),
            (
                "helping_hands.lib.hands.v1.hand.cli.opencode",
                "OpenCodeCLIHand",
                "opencode",
            ),
        ],
        ids=["claude", "codex", "gemini", "goose", "opencode"],
    )
    def test_message_includes_display_name(
        self, module_path: str, class_name: str, binary_name: str
    ) -> None:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        instance = cls.__new__(cls)
        msg = instance._command_not_found_message(binary_name)
        assert cls._CLI_DISPLAY_NAME in msg

    @pytest.mark.parametrize(
        "module_path,class_name,binary_name",
        [
            (
                "helping_hands.lib.hands.v1.hand.cli.claude",
                "ClaudeCodeHand",
                "claude",
            ),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand", "codex"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand", "gemini"),
            ("helping_hands.lib.hands.v1.hand.cli.goose", "GooseCLIHand", "goose"),
            (
                "helping_hands.lib.hands.v1.hand.cli.opencode",
                "OpenCodeCLIHand",
                "opencode",
            ),
        ],
        ids=["claude", "codex", "gemini", "goose", "opencode"],
    )
    def test_message_includes_env_var(
        self, module_path: str, class_name: str, binary_name: str
    ) -> None:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        instance = cls.__new__(cls)
        msg = instance._command_not_found_message(binary_name)
        assert cls._COMMAND_ENV_VAR in msg

    @pytest.mark.parametrize(
        "module_path,class_name,binary_name",
        [
            (
                "helping_hands.lib.hands.v1.hand.cli.claude",
                "ClaudeCodeHand",
                "claude",
            ),
            ("helping_hands.lib.hands.v1.hand.cli.codex", "CodexCLIHand", "codex"),
            ("helping_hands.lib.hands.v1.hand.cli.gemini", "GeminiCLIHand", "gemini"),
            ("helping_hands.lib.hands.v1.hand.cli.goose", "GooseCLIHand", "goose"),
            (
                "helping_hands.lib.hands.v1.hand.cli.opencode",
                "OpenCodeCLIHand",
                "opencode",
            ),
        ],
        ids=["claude", "codex", "gemini", "goose", "opencode"],
    )
    def test_message_includes_docker_rebuild_hint(
        self, module_path: str, class_name: str, binary_name: str
    ) -> None:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        instance = cls.__new__(cls)
        msg = instance._command_not_found_message(binary_name)
        expected = _DOCKER_REBUILD_HINT_TEMPLATE.format(binary_name)
        assert expected in msg


# ---------------------------------------------------------------------------
# Docker sandbox claude still has its own override (not affected)
# ---------------------------------------------------------------------------


class TestDockerSandboxClaudeKeepsOverride:
    """docker_sandbox_claude keeps its own _command_not_found_message."""

    def test_has_own_override(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        assert "_command_not_found_message" in DockerSandboxClaudeCodeHand.__dict__

    def test_message_mentions_sandbox(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        instance = DockerSandboxClaudeCodeHand.__new__(DockerSandboxClaudeCodeHand)
        msg = instance._command_not_found_message("claude")
        assert "sandbox" in msg.lower()
