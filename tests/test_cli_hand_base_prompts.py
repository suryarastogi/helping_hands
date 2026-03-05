"""Tests for _TwoPhaseCLIHand prompt builders and container/verbose helpers.

Covers: _execution_mode, _container_enabled, _container_image,
_apply_verbose_flags, _build_init_prompt, _build_task_prompt,
_build_apply_changes_prompt.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# Minimal stub that skips the full __init__ chain
# ---------------------------------------------------------------------------


class _Stub(_TwoPhaseCLIHand):
    _CLI_LABEL = "stub"
    _CLI_DISPLAY_NAME = "Stub CLI"
    _COMMAND_ENV_VAR = "STUB_CMD"
    _DEFAULT_CLI_CMD = "stub-cli"
    _DEFAULT_MODEL = "stub-model-1"
    _DEFAULT_APPEND_ARGS: tuple[str, ...] = ("--json",)
    _CONTAINER_ENABLED_ENV_VAR = "STUB_CONTAINER"
    _CONTAINER_IMAGE_ENV_VAR = "STUB_CONTAINER_IMAGE"
    _VERBOSE_CLI_FLAGS = ("--verbose", "--debug")

    def __init__(
        self,
        *,
        model: str = "default",
        verbose: bool = False,
        use_native_cli_auth: bool = False,
        repo_root: Path | None = None,
        files: list[str] | None = None,
        tools: tuple[str, ...] = (),
        skills: tuple = (),
    ) -> None:
        self.config = SimpleNamespace(
            model=model,
            verbose=verbose,
            use_native_cli_auth=use_native_cli_auth,
        )
        root = repo_root or Path("/tmp/fake-repo")
        self.repo_index = SimpleNamespace(root=root, files=files or [])
        self.auto_pr = True
        self._active_process = None
        self._skill_catalog_dir = None
        self._selected_tool_categories = tools
        self._selected_skills = skills


# ---------------------------------------------------------------------------
# _execution_mode
# ---------------------------------------------------------------------------


class TestExecutionMode:
    def test_workspace_write_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STUB_CONTAINER", raising=False)
        stub = _Stub()
        assert stub._execution_mode() == "workspace-write"

    def test_container_mode_when_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER", "1")
        monkeypatch.setenv("STUB_CONTAINER_IMAGE", "my-image:latest")
        stub = _Stub()
        assert stub._execution_mode() == "container+workspace-write"


# ---------------------------------------------------------------------------
# _container_enabled
# ---------------------------------------------------------------------------


class TestContainerEnabled:
    def test_false_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STUB_CONTAINER", raising=False)
        stub = _Stub()
        assert stub._container_enabled() is False

    def test_false_when_env_var_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER", "")
        stub = _Stub()
        assert stub._container_enabled() is False

    def test_true_when_env_var_is_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER", "1")
        stub = _Stub()
        assert stub._container_enabled() is True

    def test_false_when_env_var_is_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER", "0")
        stub = _Stub()
        assert stub._container_enabled() is False

    def test_false_when_no_env_var_name_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stub = _Stub()
        stub._CONTAINER_ENABLED_ENV_VAR = ""
        assert stub._container_enabled() is False


# ---------------------------------------------------------------------------
# _container_image
# ---------------------------------------------------------------------------


class TestContainerImage:
    def test_returns_image_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER_IMAGE", "my-org/my-image:v1")
        stub = _Stub()
        assert stub._container_image() == "my-org/my-image:v1"

    def test_raises_when_env_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER_IMAGE", "")
        monkeypatch.setenv("STUB_CONTAINER", "1")
        stub = _Stub()
        with pytest.raises(RuntimeError, match="STUB_CONTAINER_IMAGE must be set"):
            stub._container_image()

    def test_raises_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STUB_CONTAINER_IMAGE", raising=False)
        stub = _Stub()
        with pytest.raises(RuntimeError, match="STUB_CONTAINER_IMAGE must be set"):
            stub._container_image()

    def test_raises_when_no_image_env_var_configured(self) -> None:
        stub = _Stub()
        stub._CONTAINER_IMAGE_ENV_VAR = ""
        with pytest.raises(RuntimeError, match="not configured"):
            stub._container_image()

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STUB_CONTAINER_IMAGE", "  img:latest  ")
        stub = _Stub()
        assert stub._container_image() == "img:latest"


# ---------------------------------------------------------------------------
# _apply_verbose_flags
# ---------------------------------------------------------------------------


class TestApplyVerboseFlags:
    def test_no_flags_when_not_verbose(self) -> None:
        stub = _Stub(verbose=False)
        cmd = ["stub-cli", "--json", "-p", "hello"]
        result = stub._apply_verbose_flags(cmd)
        assert "--verbose" not in result
        assert "--debug" not in result

    def test_injects_flags_when_verbose(self) -> None:
        stub = _Stub(verbose=True)
        cmd = ["stub-cli", "--json", "-p", "hello"]
        result = stub._apply_verbose_flags(cmd)
        assert "--verbose" in result
        assert "--debug" in result
        # Flags should be inserted after the binary name
        assert result[0] == "stub-cli"

    def test_no_duplicate_flags(self) -> None:
        stub = _Stub(verbose=True)
        cmd = ["stub-cli", "--verbose", "--json", "-p", "hello"]
        result = stub._apply_verbose_flags(cmd)
        assert result.count("--verbose") == 1
        assert "--debug" in result

    def test_no_injection_when_no_verbose_flags_defined(self) -> None:
        stub = _Stub(verbose=True)
        stub._VERBOSE_CLI_FLAGS = ()
        cmd = ["stub-cli", "-p", "hello"]
        result = stub._apply_verbose_flags(cmd)
        assert result == cmd


# ---------------------------------------------------------------------------
# _build_init_prompt
# ---------------------------------------------------------------------------


class TestBuildInitPrompt:
    def test_includes_repo_root(self, tmp_path: Path) -> None:
        stub = _Stub(repo_root=tmp_path, files=["README.md"])
        prompt = stub._build_init_prompt()
        assert str(tmp_path) in prompt

    def test_includes_file_list(self) -> None:
        stub = _Stub(files=["src/main.py", "README.md", "tests/test_app.py"])
        prompt = stub._build_init_prompt()
        assert "src/main.py" in prompt
        assert "README.md" in prompt
        assert "tests/test_app.py" in prompt

    def test_caps_file_list_at_200(self) -> None:
        files = [f"file_{i}.py" for i in range(300)]
        stub = _Stub(files=files)
        prompt = stub._build_init_prompt()
        assert "file_199.py" in prompt
        assert "file_200.py" not in prompt

    def test_empty_file_list_shows_placeholder(self) -> None:
        stub = _Stub(files=[])
        prompt = stub._build_init_prompt()
        assert "(no indexed files)" in prompt

    def test_includes_key_instructions(self) -> None:
        stub = _Stub(files=["main.py"])
        prompt = stub._build_init_prompt()
        assert "Initialization phase" in prompt
        assert "README.md" in prompt
        assert "AGENT.md" in prompt
        assert "Do not perform edits" in prompt


# ---------------------------------------------------------------------------
# _build_task_prompt
# ---------------------------------------------------------------------------


class TestBuildTaskPrompt:
    def test_includes_user_prompt(self) -> None:
        stub = _Stub()
        result = stub._build_task_prompt(
            prompt="Add authentication", learned_summary="repo overview"
        )
        assert "Add authentication" in result

    def test_includes_learned_summary(self) -> None:
        stub = _Stub()
        result = stub._build_task_prompt(
            prompt="task", learned_summary="This is a Python project."
        )
        assert "This is a Python project." in result

    def test_empty_summary_shows_placeholder(self) -> None:
        stub = _Stub()
        result = stub._build_task_prompt(prompt="task", learned_summary="")
        assert "(no summary produced)" in result

    def test_truncates_long_summary(self) -> None:
        stub = _Stub()
        long_summary = "x" * 10000
        result = stub._build_task_prompt(prompt="task", learned_summary=long_summary)
        # Summary should be truncated to _SUMMARY_CHAR_LIMIT (6000)
        assert "...[truncated]" in result

    def test_includes_execution_context(self) -> None:
        stub = _Stub()
        result = stub._build_task_prompt(prompt="task", learned_summary="summary")
        assert "non-interactive" in result
        assert "Do not ask the user" in result


# ---------------------------------------------------------------------------
# _build_apply_changes_prompt
# ---------------------------------------------------------------------------


class TestBuildApplyChangesPrompt:
    def test_includes_original_prompt(self) -> None:
        stub = _Stub()
        result = stub._build_apply_changes_prompt(
            prompt="Fix the login bug", task_output="analysis of the bug"
        )
        assert "Fix the login bug" in result

    def test_includes_task_output(self) -> None:
        stub = _Stub()
        result = stub._build_apply_changes_prompt(
            prompt="task", task_output="Found issue in auth.py"
        )
        assert "Found issue in auth.py" in result

    def test_truncates_long_output(self) -> None:
        stub = _Stub()
        long_output = "y" * 5000
        result = stub._build_apply_changes_prompt(
            prompt="task", task_output=long_output
        )
        assert "...[truncated]" in result

    def test_empty_output_shows_placeholder(self) -> None:
        stub = _Stub()
        result = stub._build_apply_changes_prompt(prompt="task", task_output="")
        assert "(none)" in result

    def test_includes_enforcement_instructions(self) -> None:
        stub = _Stub()
        result = stub._build_apply_changes_prompt(prompt="task", task_output="output")
        assert "Follow-up enforcement" in result
        assert "apply the required edits" in result
