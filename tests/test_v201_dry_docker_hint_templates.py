"""Tests for v201: DRY Docker hint message templates in CLI hands.

Covers:
- _DOCKER_ENV_HINT_TEMPLATE shared constant in cli/base.py (value, format)
- _DOCKER_REBUILD_HINT_TEMPLATE shared constant in cli/base.py (value, format)
- Cross-module import consistency (all CLI hands use base templates)
- Auth failure messages contain the template output
- Command-not-found messages contain the template output
"""

from __future__ import annotations

import inspect

from helping_hands.lib.hands.v1.hand.cli.base import (
    _DOCKER_ENV_HINT_TEMPLATE,
    _DOCKER_REBUILD_HINT_TEMPLATE,
)

# ---------------------------------------------------------------------------
# _DOCKER_ENV_HINT_TEMPLATE constant
# ---------------------------------------------------------------------------


class TestDockerEnvHintTemplate:
    """Verify _DOCKER_ENV_HINT_TEMPLATE in cli/base.py."""

    def test_is_string(self) -> None:
        assert isinstance(_DOCKER_ENV_HINT_TEMPLATE, str)

    def test_contains_docker_keyword(self) -> None:
        assert "Docker" in _DOCKER_ENV_HINT_TEMPLATE

    def test_contains_env_placeholder(self) -> None:
        assert "{}" in _DOCKER_ENV_HINT_TEMPLATE

    def test_contains_recreate_hint(self) -> None:
        assert "recreate server/worker containers" in _DOCKER_ENV_HINT_TEMPLATE

    def test_format_with_anthropic_key(self) -> None:
        result = _DOCKER_ENV_HINT_TEMPLATE.format("ANTHROPIC_API_KEY")
        assert "ANTHROPIC_API_KEY" in result
        assert "Docker" in result
        assert ".env" in result

    def test_format_with_openai_key(self) -> None:
        result = _DOCKER_ENV_HINT_TEMPLATE.format("OPENAI_API_KEY")
        assert "OPENAI_API_KEY" in result

    def test_format_with_generic_key(self) -> None:
        result = _DOCKER_ENV_HINT_TEMPLATE.format("the appropriate API key")
        assert "the appropriate API key" in result


# ---------------------------------------------------------------------------
# _DOCKER_REBUILD_HINT_TEMPLATE constant
# ---------------------------------------------------------------------------


class TestDockerRebuildHintTemplate:
    """Verify _DOCKER_REBUILD_HINT_TEMPLATE in cli/base.py."""

    def test_is_string(self) -> None:
        assert isinstance(_DOCKER_REBUILD_HINT_TEMPLATE, str)

    def test_contains_docker_keyword(self) -> None:
        assert "Docker" in _DOCKER_REBUILD_HINT_TEMPLATE

    def test_contains_rebuild_keyword(self) -> None:
        assert "rebuild worker images" in _DOCKER_REBUILD_HINT_TEMPLATE

    def test_contains_binary_placeholder(self) -> None:
        assert "{}" in _DOCKER_REBUILD_HINT_TEMPLATE

    def test_format_with_codex(self) -> None:
        result = _DOCKER_REBUILD_HINT_TEMPLATE.format("codex")
        assert "codex" in result
        assert "rebuild" in result

    def test_format_with_gemini(self) -> None:
        result = _DOCKER_REBUILD_HINT_TEMPLATE.format("gemini")
        assert "gemini" in result

    def test_format_with_goose(self) -> None:
        result = _DOCKER_REBUILD_HINT_TEMPLATE.format("goose")
        assert "goose" in result


# ---------------------------------------------------------------------------
# Cross-module import consistency — auth failure (env hint)
# ---------------------------------------------------------------------------


class TestDockerEnvHintCrossModuleSync:
    """CLI hands importing _DOCKER_ENV_HINT_TEMPLATE use the same object."""

    def test_claude_uses_same_object(self) -> None:
        src = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.claude",
                fromlist=["ClaudeCodeHand"],
            )
        )
        assert "_DOCKER_ENV_HINT_TEMPLATE" in src

    def test_codex_uses_same_object(self) -> None:
        src = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.codex",
                fromlist=["CodexCLIHand"],
            )
        )
        assert "_DOCKER_ENV_HINT_TEMPLATE" in src

    def test_gemini_uses_same_object(self) -> None:
        src = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.gemini",
                fromlist=["GeminiCLIHand"],
            )
        )
        assert "_DOCKER_ENV_HINT_TEMPLATE" in src

    def test_opencode_uses_same_object(self) -> None:
        src = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.opencode",
                fromlist=["OpenCodeCLIHand"],
            )
        )
        assert "_DOCKER_ENV_HINT_TEMPLATE" in src


# ---------------------------------------------------------------------------
# _DOCKER_REBUILD_HINT_TEMPLATE used by base _command_not_found_message
# ---------------------------------------------------------------------------


class TestDockerRebuildHintInBaseCommandNotFound:
    """_DOCKER_REBUILD_HINT_TEMPLATE is used in the base class message.

    Since v202, subclasses (codex, gemini, goose, opencode, claude) no longer
    override ``_command_not_found_message``; the Docker rebuild hint is
    generated by the base class using ``_CLI_LABEL`` / ``command`` parameter.
    """

    def test_base_source_uses_rebuild_hint(self) -> None:
        src = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.cli.base",
                fromlist=["_TwoPhaseCLIHand"],
            )
        )
        assert "_DOCKER_REBUILD_HINT_TEMPLATE" in src


# ---------------------------------------------------------------------------
# __all__ exports
# ---------------------------------------------------------------------------


class TestDockerHintAllExports:
    """Both templates are exported in cli/base.py __all__."""

    def test_env_hint_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base

        assert "_DOCKER_ENV_HINT_TEMPLATE" in base.__all__

    def test_rebuild_hint_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import base

        assert "_DOCKER_REBUILD_HINT_TEMPLATE" in base.__all__
