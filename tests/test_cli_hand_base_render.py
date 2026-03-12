"""Tests for _TwoPhaseCLIHand._render_command base-level logic.

Covers placeholder substitution, model flag auto-injection, prompt fallback,
and interaction between _apply_backend_defaults, _apply_verbose_flags, and
_wrap_container_if_enabled hooks during command rendering.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Minimal stub that bypasses the full __init__ chain
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _COMMAND_ENV_VAR = "STUB_CLI_CMD"
    _DEFAULT_CLI_CMD = "stub-cli -p"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ()
    _CONTAINER_ENABLED_ENV_VAR = ""
    _CONTAINER_IMAGE_ENV_VAR = ""
    _VERBOSE_CLI_FLAGS: tuple[str, ...] = ("--verbose",)

    def __init__(
        self,
        *,
        model: str = "default",
        verbose: bool = False,
        cmd: str = "stub-cli -p",
        default_model: str = "stub-model-1",
    ) -> None:
        self.config = SimpleNamespace(
            model=model,
            verbose=verbose,
            use_native_cli_auth=False,
        )
        self.repo_index = MagicMock()
        self.repo_index.root.resolve.return_value = Path("/fake/repo")
        self.auto_pr = True
        self._DEFAULT_CLI_CMD = cmd
        self._DEFAULT_MODEL = default_model


# ---------------------------------------------------------------------------
# Prompt placement
# ---------------------------------------------------------------------------


class TestRenderCommandPromptPlacement:
    """The prompt is placed via {prompt} placeholder, -p flag, or as trailing arg."""

    def test_prompt_via_placeholder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CLI_CMD", 'stub-cli --prompt "{prompt}"')
        stub = _Stub(cmd='stub-cli --prompt "{prompt}"')
        monkeypatch.setenv("STUB_CLI_CMD", 'stub-cli --prompt "{prompt}"')
        cmd = stub._render_command("do stuff")
        assert "do stuff" in cmd
        # Prompt should not be appended again as trailing arg
        assert cmd.count("do stuff") == 1

    def test_prompt_via_p_flag(self) -> None:
        stub = _Stub(cmd="stub-cli -p")
        cmd = stub._render_command("hello world")
        # -p flag should be followed by the prompt
        idx = cmd.index("-p")
        assert cmd[idx + 1] == "hello world"

    def test_prompt_appended_when_no_flag_or_placeholder(self) -> None:
        stub = _Stub(cmd="stub-cli --json")
        cmd = stub._render_command("do stuff")
        # No -p flag, no {prompt} placeholder — prompt appended as trailing arg
        assert cmd[-1] == "do stuff"

    def test_prompt_not_duplicated_when_p_flag_has_value(self) -> None:
        stub = _Stub(cmd="stub-cli -p existing")
        cmd = stub._render_command("replaced")
        assert cmd.count("replaced") == 1
        assert "existing" not in cmd


# ---------------------------------------------------------------------------
# Model injection
# ---------------------------------------------------------------------------


class TestRenderCommandModelInjection:
    """Model is auto-injected via --model unless placeholder or flag exists."""

    def test_model_auto_injected_when_no_placeholder_or_flag(self) -> None:
        stub = _Stub(model="my-model", cmd="stub-cli -p")
        cmd = stub._render_command("hi")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "my-model"

    def test_model_not_injected_when_placeholder_used(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STUB_CLI_CMD", "stub-cli --model {model} -p")
        stub = _Stub(model="my-model", cmd="stub-cli --model {model} -p")
        monkeypatch.setenv("STUB_CLI_CMD", "stub-cli --model {model} -p")
        cmd = stub._render_command("hi")
        # {model} placeholder was expanded — --model should appear once, not twice
        model_count = sum(1 for t in cmd if t == "--model")
        assert model_count == 1
        assert "my-model" in cmd

    def test_model_not_injected_when_model_flag_present(self) -> None:
        stub = _Stub(model="override", cmd="stub-cli --model existing -p")
        cmd = stub._render_command("hi")
        # --model already present in base command — should not be doubled
        model_count = sum(1 for t in cmd if t == "--model")
        assert model_count == 1

    def test_model_not_injected_when_model_equals_syntax(self) -> None:
        stub = _Stub(model="override", cmd="stub-cli --model=existing -p")
        cmd = stub._render_command("hi")
        # --model=existing counts as explicit model flag
        assert "--model" not in cmd  # no separate --model token
        assert any(t.startswith("--model=") for t in cmd)

    def test_model_not_injected_when_resolved_empty(self) -> None:
        stub = _Stub(model="default", cmd="stub-cli -p", default_model="")
        cmd = stub._render_command("hi")
        assert "--model" not in cmd

    def test_provider_prefix_stripped_in_model_injection(self) -> None:
        stub = _Stub(model="anthropic/claude-sonnet-4-5", cmd="stub-cli -p")
        cmd = stub._render_command("hi")
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# Repo placeholder
# ---------------------------------------------------------------------------


class TestRenderCommandRepoPlaceholder:
    """The {repo} placeholder expands to the resolved repo root."""

    def test_repo_placeholder_expanded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CLI_CMD", "stub-cli --repo {repo} -p")
        stub = _Stub(cmd="stub-cli --repo {repo} -p")
        monkeypatch.setenv("STUB_CLI_CMD", "stub-cli --repo {repo} -p")
        cmd = stub._render_command("hi")
        assert str(Path("/fake/repo")) in cmd


# ---------------------------------------------------------------------------
# Verbose flag injection
# ---------------------------------------------------------------------------


class TestRenderCommandVerboseFlags:
    """Verbose flags are injected when config.verbose is True."""

    def test_verbose_flag_injected_when_verbose(self) -> None:
        stub = _Stub(verbose=True, cmd="stub-cli -p")
        cmd = stub._render_command("hi")
        assert "--verbose" in cmd

    def test_verbose_flag_not_injected_when_not_verbose(self) -> None:
        stub = _Stub(verbose=False, cmd="stub-cli -p")
        cmd = stub._render_command("hi")
        assert "--verbose" not in cmd

    def test_verbose_flag_not_duplicated(self) -> None:
        stub = _Stub(verbose=True, cmd="stub-cli --verbose -p")
        cmd = stub._render_command("hi")
        assert cmd.count("--verbose") == 1


# ---------------------------------------------------------------------------
# Multiple placeholders in a single token
# ---------------------------------------------------------------------------


class TestRenderCommandMultiplePlaceholders:
    """Multiple placeholders can appear in a single token."""

    def test_multiple_placeholders_in_one_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "STUB_CLI_CMD",
            'stub-cli --config=model={model},repo={repo} --prompt "{prompt}"',
        )
        stub = _Stub(
            model="my-model",
            cmd='stub-cli --config=model={model},repo={repo} --prompt "{prompt}"',
        )
        monkeypatch.setenv(
            "STUB_CLI_CMD",
            'stub-cli --config=model={model},repo={repo} --prompt "{prompt}"',
        )
        cmd = stub._render_command("go")
        config_token = [t for t in cmd if t.startswith("--config=")]
        assert len(config_token) == 1
        assert "my-model" in config_token[0]
        assert str(Path("/fake/repo")) in config_token[0]
