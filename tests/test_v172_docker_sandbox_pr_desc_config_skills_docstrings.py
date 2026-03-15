"""Tests for v172: docstrings in docker_sandbox_claude, pr_description, config, skills."""

from __future__ import annotations

import inspect

import pytest

# ---------------------------------------------------------------------------
# docker_sandbox_claude.py method docstrings
# ---------------------------------------------------------------------------

_DSC_METHODS = [
    "__init__",
    "_should_cleanup",
    "_wrap_sandbox_exec",
    "_execution_mode",
    "_build_failure_message",
    "_command_not_found_message",
    "_fallback_command_when_not_found",
]


class TestDockerSandboxClaudeDocstrings:
    """All target docker_sandbox_claude.py methods must have Google-style docstrings."""

    @pytest.mark.parametrize("method_name", _DSC_METHODS)
    def test_has_docstring(self, method_name: str) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        method = getattr(DockerSandboxClaudeCodeHand, method_name)
        doc = inspect.getdoc(method)
        assert doc, f"DockerSandboxClaudeCodeHand.{method_name} missing docstring"
        assert len(doc) > 15, (
            f"DockerSandboxClaudeCodeHand.{method_name} docstring too short"
        )

    @pytest.mark.parametrize(
        ("method_name", "expected_sections"),
        [
            ("__init__", ["Args:"]),
            ("_should_cleanup", ["Returns:"]),
            ("_wrap_sandbox_exec", ["Args:", "Returns:"]),
            ("_execution_mode", ["Returns:"]),
            ("_build_failure_message", ["Args:", "Returns:"]),
            ("_command_not_found_message", ["Args:", "Returns:"]),
            ("_fallback_command_when_not_found", ["Args:", "Returns:"]),
        ],
    )
    def test_docstring_sections(
        self, method_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        method = getattr(DockerSandboxClaudeCodeHand, method_name)
        doc = inspect.getdoc(method) or ""
        for section in expected_sections:
            assert section in doc, (
                f"DockerSandboxClaudeCodeHand.{method_name} docstring "
                f"missing {section} section"
            )


# ---------------------------------------------------------------------------
# pr_description.py prompt builder docstrings
# ---------------------------------------------------------------------------

_PR_DESC_FUNCS = ["_build_prompt", "_build_commit_message_prompt"]


class TestPrDescriptionPromptBuilderDocstrings:
    """PR description prompt builders must have Google-style docstrings."""

    @pytest.mark.parametrize("func_name", _PR_DESC_FUNCS)
    def test_has_docstring(self, func_name: str) -> None:
        from helping_hands.lib.hands.v1.hand import pr_description

        func = getattr(pr_description, func_name)
        doc = inspect.getdoc(func)
        assert doc, f"pr_description.{func_name} missing docstring"
        assert len(doc) > 30, f"pr_description.{func_name} docstring too short"

    @pytest.mark.parametrize(
        ("func_name", "expected_sections"),
        [
            ("_build_prompt", ["Args:", "Returns:"]),
            ("_build_commit_message_prompt", ["Args:", "Returns:"]),
        ],
    )
    def test_docstring_sections(
        self, func_name: str, expected_sections: list[str]
    ) -> None:
        from helping_hands.lib.hands.v1.hand import pr_description

        func = getattr(pr_description, func_name)
        doc = inspect.getdoc(func) or ""
        for section in expected_sections:
            assert section in doc, (
                f"pr_description.{func_name} docstring missing {section} section"
            )

    @pytest.mark.parametrize("func_name", _PR_DESC_FUNCS)
    def test_docstring_mentions_diff(self, func_name: str) -> None:
        from helping_hands.lib.hands.v1.hand import pr_description

        func = getattr(pr_description, func_name)
        doc = inspect.getdoc(func) or ""
        assert "diff" in doc.lower(), (
            f"pr_description.{func_name} docstring should mention diff"
        )

    @pytest.mark.parametrize("func_name", _PR_DESC_FUNCS)
    def test_docstring_mentions_backend(self, func_name: str) -> None:
        from helping_hands.lib.hands.v1.hand import pr_description

        func = getattr(pr_description, func_name)
        doc = inspect.getdoc(func) or ""
        assert "backend" in doc.lower(), (
            f"pr_description.{func_name} docstring should mention backend"
        )


# ---------------------------------------------------------------------------
# config.py _load_env_files docstring
# ---------------------------------------------------------------------------


class TestConfigLoadEnvFilesDocstring:
    """config._load_env_files must have a Google-style docstring."""

    def test_has_docstring(self) -> None:
        from helping_hands.lib.config import _load_env_files

        doc = inspect.getdoc(_load_env_files)
        assert doc, "_load_env_files missing docstring"
        assert len(doc) > 30, "_load_env_files docstring too short"

    def test_docstring_has_args_section(self) -> None:
        from helping_hands.lib.config import _load_env_files

        doc = inspect.getdoc(_load_env_files) or ""
        assert "Args:" in doc, "_load_env_files docstring missing Args: section"

    def test_docstring_mentions_repo(self) -> None:
        from helping_hands.lib.config import _load_env_files

        doc = inspect.getdoc(_load_env_files) or ""
        assert "repo" in doc.lower(), "_load_env_files docstring should mention repo"

    def test_docstring_mentions_dotenv(self) -> None:
        from helping_hands.lib.config import _load_env_files

        doc = inspect.getdoc(_load_env_files) or ""
        assert "dotenv" in doc.lower(), (
            "_load_env_files docstring should mention dotenv"
        )


# ---------------------------------------------------------------------------
# skills/__init__.py _discover_catalog docstring
# ---------------------------------------------------------------------------


class TestDiscoverCatalogDocstring:
    """skills._discover_catalog must have a Google-style docstring."""

    def test_has_docstring(self) -> None:
        from helping_hands.lib.meta.skills import _discover_catalog

        doc = inspect.getdoc(_discover_catalog)
        assert doc, "_discover_catalog missing docstring"
        assert len(doc) > 30, "_discover_catalog docstring too short"

    def test_docstring_has_returns_section(self) -> None:
        from helping_hands.lib.meta.skills import _discover_catalog

        doc = inspect.getdoc(_discover_catalog) or ""
        assert "Returns:" in doc, "_discover_catalog docstring missing Returns: section"

    def test_docstring_mentions_catalog(self) -> None:
        from helping_hands.lib.meta.skills import _discover_catalog

        doc = inspect.getdoc(_discover_catalog) or ""
        assert "catalog" in doc.lower(), (
            "_discover_catalog docstring should mention catalog"
        )

    def test_docstring_mentions_skillspec(self) -> None:
        from helping_hands.lib.meta.skills import _discover_catalog

        doc = inspect.getdoc(_discover_catalog) or ""
        assert "SkillSpec" in doc, (
            "_discover_catalog docstring should mention SkillSpec"
        )
