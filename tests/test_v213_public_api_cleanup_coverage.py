"""Tests for v213: public API cleanup, __all__ hygiene, coverage gaps.

Verifies:
- registry.py payload validators are public (no underscore prefix)
- registry.py __all__ includes the promoted helpers
- cli/__init__.py __all__ excludes _TwoPhaseCLIHand
- goose.py _apply_backend_defaults guard clause for non-goose-run commands
- codex.py _build_codex_failure_message Docker env hint in auth failure
"""

from __future__ import annotations

from helping_hands.lib.hands.v1.hand.cli.codex import CodexCLIHand
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand
from helping_hands.lib.meta.tools import registry as registry_module
from helping_hands.lib.meta.tools.registry import (
    parse_optional_str,
    parse_positive_int,
    parse_str_list,
)

# ---------------------------------------------------------------------------
# 1. registry.py public API promotion
# ---------------------------------------------------------------------------


class TestRegistryPublicAPI:
    """Verify payload validators are public and in __all__."""

    def test_parse_str_list_is_public(self) -> None:
        assert not parse_str_list.__name__.startswith("_")

    def test_parse_positive_int_is_public(self) -> None:
        assert not parse_positive_int.__name__.startswith("_")

    def test_parse_optional_str_is_public(self) -> None:
        assert not parse_optional_str.__name__.startswith("_")

    def test_parse_str_list_in_all(self) -> None:
        assert "parse_str_list" in registry_module.__all__

    def test_parse_positive_int_in_all(self) -> None:
        assert "parse_positive_int" in registry_module.__all__

    def test_parse_optional_str_in_all(self) -> None:
        assert "parse_optional_str" in registry_module.__all__

    def test_parse_str_list_callable(self) -> None:
        assert parse_str_list({"a": ["x"]}, key="a") == ["x"]

    def test_parse_positive_int_callable(self) -> None:
        assert parse_positive_int({"n": 7}, key="n", default=1) == 7

    def test_parse_optional_str_callable(self) -> None:
        assert parse_optional_str({"k": "val"}, key="k") == "val"


# ---------------------------------------------------------------------------
# 2. cli/__init__.py __all__ hygiene
# ---------------------------------------------------------------------------


class TestCLIInitAll:
    """Verify _TwoPhaseCLIHand is not in cli/__init__.py __all__."""

    def test_two_phase_cli_hand_not_in_init_all(self) -> None:
        from helping_hands.lib.hands.v1.hand import cli as cli_pkg

        assert "_TwoPhaseCLIHand" not in cli_pkg.__all__

    def test_public_hands_in_init_all(self) -> None:
        from helping_hands.lib.hands.v1.hand import cli as cli_pkg

        expected = [
            "ClaudeCodeHand",
            "CodexCLIHand",
            "DockerSandboxClaudeCodeHand",
            "GeminiCLIHand",
            "GooseCLIHand",
            "OpenCodeCLIHand",
        ]
        for name in expected:
            assert name in cli_pkg.__all__

    def test_two_phase_cli_hand_still_importable_from_base(self) -> None:
        """Removing from __init__ doesn't prevent import from base module."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        assert _TwoPhaseCLIHand is not None


# ---------------------------------------------------------------------------
# 3. goose.py _apply_backend_defaults guard clause coverage
# ---------------------------------------------------------------------------


class _GooseStub(GooseCLIHand):
    """Minimal stub bypassing __init__ for isolated method tests."""

    def __init__(self) -> None:
        pass


class TestGooseApplyBackendDefaultsGuard:
    """Cover the early-return guard in _apply_backend_defaults (line 134)."""

    def test_empty_cmd_returns_unchanged(self) -> None:
        stub = _GooseStub()
        cmd: list[str] = []
        assert stub._apply_backend_defaults(cmd) is cmd

    def test_single_element_cmd_returns_unchanged(self) -> None:
        stub = _GooseStub()
        cmd = ["goose"]
        assert stub._apply_backend_defaults(cmd) is cmd

    def test_non_goose_cmd_returns_unchanged(self) -> None:
        stub = _GooseStub()
        cmd = ["python", "run"]
        assert stub._apply_backend_defaults(cmd) is cmd

    def test_goose_non_run_subcommand_returns_unchanged(self) -> None:
        stub = _GooseStub()
        cmd = ["goose", "session"]
        assert stub._apply_backend_defaults(cmd) is cmd

    def test_goose_run_injects_developer_builtin(self) -> None:
        stub = _GooseStub()
        result = stub._apply_backend_defaults(["goose", "run", "--prompt", "hi"])
        assert result == [
            "goose",
            "run",
            "--with-builtin",
            "developer",
            "--prompt",
            "hi",
        ]

    def test_goose_run_with_existing_builtin_unchanged(self) -> None:
        stub = _GooseStub()
        cmd = ["goose", "run", "--with-builtin", "custom", "--prompt", "hi"]
        assert stub._apply_backend_defaults(cmd) is cmd


# ---------------------------------------------------------------------------
# 4. codex.py Docker env hint in auth failure message
# ---------------------------------------------------------------------------


class TestCodexDockerEnvHint:
    """Cover the Docker env hint line in _build_codex_failure_message."""

    def test_auth_failure_includes_docker_env_hint(self) -> None:
        """When auth failure is detected, message includes Docker env hint."""
        output = (
            "some output\n"
            "error: 401 Unauthorized\n"
            "missing bearer or basic authentication"
        )
        msg = CodexCLIHand._build_codex_failure_message(return_code=1, output=output)
        assert "401 Unauthorized" in msg
        assert "OPENAI_API_KEY" in msg
        # Docker env hint should be present
        assert "docker" in msg.lower() or "Docker" in msg

    def test_auth_failure_message_format(self) -> None:
        output = "missing bearer or basic authentication"
        msg = CodexCLIHand._build_codex_failure_message(return_code=1, output=output)
        assert msg.startswith("Codex CLI authentication failed")
        assert "Output:" in msg

    def test_non_auth_failure_no_docker_hint(self) -> None:
        output = "some other error\nprocess crashed"
        msg = CodexCLIHand._build_codex_failure_message(return_code=1, output=output)
        assert msg.startswith("Codex CLI failed (exit=1)")
        assert "OPENAI_API_KEY" not in msg
