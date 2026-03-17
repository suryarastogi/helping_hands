"""Tests for v249 — deduplicate env var constants between github_url.py and base.py.

Validates that _ENV_GIT_TERMINAL_PROMPT and _ENV_GCM_INTERACTIVE are defined
only in github_url.py (the canonical location) and imported by base.py.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from helping_hands.lib.github_url import (
    ENV_GCM_INTERACTIVE,
    ENV_GIT_TERMINAL_PROMPT,
)
from helping_hands.lib.hands.v1.hand.base import (
    _ENV_GCM_INTERACTIVE,
    _ENV_GIT_TERMINAL_PROMPT,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_PY = Path(
    inspect.getfile(
        __import__(
            "helping_hands.lib.hands.v1.hand.base",
            fromlist=["Hand"],
        )
    )
)

_GITHUB_URL_PY = Path(
    inspect.getfile(
        __import__(
            "helping_hands.lib.github_url",
            fromlist=["ENV_GIT_TERMINAL_PROMPT"],
        )
    )
)


# ---------------------------------------------------------------------------
# Identity tests — base.py re-exports the same objects
# ---------------------------------------------------------------------------


class TestConstantIdentity:
    """Constants imported by base.py must be the same objects as github_url.py."""

    def test_git_terminal_prompt_identity(self) -> None:
        assert _ENV_GIT_TERMINAL_PROMPT is ENV_GIT_TERMINAL_PROMPT

    def test_gcm_interactive_identity(self) -> None:
        assert _ENV_GCM_INTERACTIVE is ENV_GCM_INTERACTIVE

    def test_git_terminal_prompt_value(self) -> None:
        assert _ENV_GIT_TERMINAL_PROMPT == "GIT_TERMINAL_PROMPT"

    def test_gcm_interactive_value(self) -> None:
        assert _ENV_GCM_INTERACTIVE == "GCM_INTERACTIVE"


# ---------------------------------------------------------------------------
# AST tests — no assignment of these constants in base.py
# ---------------------------------------------------------------------------


def _find_assignments(source: str, target_name: str) -> list[int]:
    """Return line numbers where *target_name* is assigned (not imported)."""
    tree = ast.parse(source)
    lines: list[int] = []
    for node in ast.walk(tree):
        # Simple assignment: _ENV_GIT_TERMINAL_PROMPT = "..."
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    lines.append(node.lineno)
        # Annotated assignment: _ENV_GIT_TERMINAL_PROMPT: str = "..."
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == target_name
        ):
            lines.append(node.lineno)
    return lines


class TestNoDuplicateAssignmentsInBase:
    """base.py must not define _ENV_* constants — only import them."""

    def test_no_git_terminal_prompt_assignment(self) -> None:
        source = _BASE_PY.read_text()
        lines = _find_assignments(source, "_ENV_GIT_TERMINAL_PROMPT")
        assert lines == [], (
            f"base.py assigns _ENV_GIT_TERMINAL_PROMPT at line(s) {lines}; "
            "should import from github_url instead"
        )

    def test_no_gcm_interactive_assignment(self) -> None:
        source = _BASE_PY.read_text()
        lines = _find_assignments(source, "_ENV_GCM_INTERACTIVE")
        assert lines == [], (
            f"base.py assigns _ENV_GCM_INTERACTIVE at line(s) {lines}; "
            "should import from github_url instead"
        )


class TestCanonicalDefinitionInGithubUrl:
    """github_url.py must define the canonical constants."""

    def test_git_terminal_prompt_defined(self) -> None:
        source = _GITHUB_URL_PY.read_text()
        lines = _find_assignments(source, "ENV_GIT_TERMINAL_PROMPT")
        assert len(lines) == 1, (
            f"Expected exactly 1 assignment of ENV_GIT_TERMINAL_PROMPT "
            f"in github_url.py, found {len(lines)}"
        )

    def test_gcm_interactive_defined(self) -> None:
        source = _GITHUB_URL_PY.read_text()
        lines = _find_assignments(source, "ENV_GCM_INTERACTIVE")
        assert len(lines) == 1, (
            f"Expected exactly 1 assignment of ENV_GCM_INTERACTIVE "
            f"in github_url.py, found {len(lines)}"
        )


# ---------------------------------------------------------------------------
# __all__ export tests
# ---------------------------------------------------------------------------


class TestGithubUrlExports:
    """github_url.py __all__ must include the env var constants."""

    def test_git_terminal_prompt_in_all(self) -> None:
        import helping_hands.lib.github_url as mod

        assert "ENV_GIT_TERMINAL_PROMPT" in mod.__all__

    def test_gcm_interactive_in_all(self) -> None:
        import helping_hands.lib.github_url as mod

        assert "ENV_GCM_INTERACTIVE" in mod.__all__


# ---------------------------------------------------------------------------
# Import presence tests — base.py imports from github_url
# ---------------------------------------------------------------------------


class TestBaseImportsFromGithubUrl:
    """base.py must import _ENV_* from github_url, not define locally."""

    def _find_import_sources(self, source: str, name: str) -> list[str]:
        """Return module paths from which *name* is imported."""
        tree = ast.parse(source)
        sources: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    actual = alias.asname or alias.name
                    if actual == name or alias.name == name:
                        sources.append(node.module)
        return sources

    def test_git_terminal_prompt_imported_from_github_url(self) -> None:
        source = _BASE_PY.read_text()
        sources = self._find_import_sources(source, "_ENV_GIT_TERMINAL_PROMPT")
        assert any("github_url" in s for s in sources), (
            f"_ENV_GIT_TERMINAL_PROMPT not imported from github_url; sources: {sources}"
        )

    def test_gcm_interactive_imported_from_github_url(self) -> None:
        source = _BASE_PY.read_text()
        sources = self._find_import_sources(source, "_ENV_GCM_INTERACTIVE")
        assert any("github_url" in s for s in sources), (
            f"_ENV_GCM_INTERACTIVE not imported from github_url; sources: {sources}"
        )


# ---------------------------------------------------------------------------
# Behavioral tests — _push_noninteractive still uses the constants
# ---------------------------------------------------------------------------


class TestPushBranchUsesConstants:
    """The _push_noninteractive method in base.py must reference the imported constants."""

    def test_push_noninteractive_references_env_constants(self) -> None:
        source = _BASE_PY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_push_noninteractive"
            ):
                method_src = ast.get_source_segment(source, node)
                assert method_src is not None
                assert "_ENV_GIT_TERMINAL_PROMPT" in method_src
                assert "_ENV_GCM_INTERACTIVE" in method_src
                return
        pytest.fail("Could not find _push_noninteractive method in base.py")

    def test_push_noninteractive_no_bare_env_strings(self) -> None:
        """_push_noninteractive must not contain bare 'GIT_TERMINAL_PROMPT' strings."""
        source = _BASE_PY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_push_noninteractive"
            ):
                method_src = ast.get_source_segment(source, node)
                assert method_src is not None
                method_tree = ast.parse(method_src)
                for sub in ast.walk(method_tree):
                    if isinstance(sub, ast.Constant) and sub.value in (
                        "GIT_TERMINAL_PROMPT",
                        "GCM_INTERACTIVE",
                    ):
                        pytest.fail(
                            f"_push_noninteractive has bare env var string {sub.value!r}"
                        )
                return
        pytest.fail("Could not find _push_noninteractive method in base.py")


# ---------------------------------------------------------------------------
# Docstring tests — canonical constants have docstrings
# ---------------------------------------------------------------------------


class TestDocstringsInGithubUrl:
    """Canonical constants in github_url.py must have docstrings."""

    def test_git_terminal_prompt_docstring(self) -> None:
        source = _GITHUB_URL_PY.read_text()
        assert "suppress" in source.lower()
        assert "ENV_GIT_TERMINAL_PROMPT" in source

    def test_gcm_interactive_docstring(self) -> None:
        source = _GITHUB_URL_PY.read_text()
        assert "GCM_INTERACTIVE" in source
        assert "suppress" in source.lower()
