"""Tests for v247: provider name constants extracted in model_provider.py.

resolve_hand_model() returns a (provider, model) tuple that is written into
result metadata and used to select the correct AI client. If provider name
strings ("openai", "anthropic", etc.) are scattered as bare literals across
model_provider.py and goose.py, a renaming (e.g. "google" → "google-genai")
requires hunting down every occurrence; missed occurrences silently route to
the wrong provider.

The AST checks enforce that the bare strings exist only at the constant
definition sites, preventing future duplication.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.model_provider import (
    _PROVIDER_ANTHROPIC,
    _PROVIDER_GOOGLE,
    _PROVIDER_LITELLM,
    _PROVIDER_OLLAMA,
    _PROVIDER_OPENAI,
    __all__ as mp_all,
    resolve_hand_model,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MODEL_PROVIDER_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "helping_hands"
    / "lib"
    / "hands"
    / "v1"
    / "hand"
    / "model_provider.py"
)

_GOOSE_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "helping_hands"
    / "lib"
    / "hands"
    / "v1"
    / "hand"
    / "cli"
    / "goose.py"
)

_ALL_CONSTANTS = {
    _PROVIDER_OPENAI,
    _PROVIDER_ANTHROPIC,
    _PROVIDER_GOOGLE,
    _PROVIDER_OLLAMA,
    _PROVIDER_LITELLM,
}

# ===========================================================================
# Constant value and type tests
# ===========================================================================


class TestProviderNameConstantValues:
    """Verify constant string values and types."""

    def test_openai_value(self) -> None:
        assert _PROVIDER_OPENAI == "openai"

    def test_anthropic_value(self) -> None:
        assert _PROVIDER_ANTHROPIC == "anthropic"

    def test_google_value(self) -> None:
        assert _PROVIDER_GOOGLE == "google"

    def test_ollama_value(self) -> None:
        assert _PROVIDER_OLLAMA == "ollama"

    def test_litellm_value(self) -> None:
        assert _PROVIDER_LITELLM == "litellm"

    def test_all_are_strings(self) -> None:
        for const in _ALL_CONSTANTS:
            assert isinstance(const, str), f"{const!r} is not a string"

    def test_all_distinct(self) -> None:
        assert len(_ALL_CONSTANTS) == 5

    def test_all_lowercase(self) -> None:
        for const in _ALL_CONSTANTS:
            assert const == const.lower(), f"{const!r} is not lowercase"

    def test_no_empty(self) -> None:
        for const in _ALL_CONSTANTS:
            assert const.strip(), f"{const!r} is empty or whitespace"


# ===========================================================================
# __all__ exports
# ===========================================================================


class TestProviderNameExports:
    """Verify constants are exported in __all__."""

    @pytest.mark.parametrize(
        "name",
        [
            "_PROVIDER_OPENAI",
            "_PROVIDER_ANTHROPIC",
            "_PROVIDER_GOOGLE",
            "_PROVIDER_OLLAMA",
            "_PROVIDER_LITELLM",
        ],
    )
    def test_exported_in_all(self, name: str) -> None:
        assert name in mp_all, f"{name} not in model_provider.__all__"


# ===========================================================================
# AST: No bare provider name strings in source (excluding constants + docs)
# ===========================================================================


class _BareProviderStringVisitor(ast.NodeVisitor):
    """Find bare provider name string literals used in comparisons or dict keys."""

    _PROVIDER_NAMES: frozenset[str] = frozenset(
        {"openai", "anthropic", "google", "ollama", "litellm"}
    )

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []
        self._in_assign = False
        self._assign_target: str = ""

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.startswith("_PROVIDER_"):
                self._in_assign = True
                self._assign_target = target.id
                self.generic_visit(node)
                self._in_assign = False
                self._assign_target = ""
                return
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        for comparator in node.comparators:
            self._check_node(comparator)
        self._check_node(node.left)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        self._check_node(node.slice)
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        for key in node.keys:
            if key is not None:
                self._check_node(key)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self._check_node(node.value)
        self.generic_visit(node)

    def _check_node(self, node: ast.AST) -> None:
        if self._in_assign:
            return
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in self._PROVIDER_NAMES
        ):
            self.hits.append((node.lineno, node.value))


class TestNoBarProviderStringsModelProvider:
    """AST check: model_provider.py uses constants, not bare strings."""

    def test_no_bare_provider_strings(self) -> None:
        source = _MODEL_PROVIDER_PATH.read_text()
        tree = ast.parse(source, filename=str(_MODEL_PROVIDER_PATH))
        visitor = _BareProviderStringVisitor()
        visitor.visit(tree)
        # Filter out the constant definitions themselves and _DEFAULT_OLLAMA_API_KEY
        real_hits = [
            (line, val)
            for line, val in visitor.hits
            if not any(
                line == node.lineno
                for node in ast.walk(tree)
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name)
                    and (
                        t.id.startswith("_PROVIDER_")
                        or t.id == "_DEFAULT_OLLAMA_API_KEY"
                    )
                    for t in node.targets
                )
            )
        ]
        assert real_hits == [], (
            f"Bare provider name strings found in model_provider.py: {real_hits}"
        )


class TestNoBarProviderStringsGoose:
    """AST check: goose.py uses constants, not bare strings."""

    def test_no_bare_provider_strings_in_non_docstring_code(self) -> None:
        source = _GOOSE_PATH.read_text()
        tree = ast.parse(source, filename=str(_GOOSE_PATH))
        visitor = _BareProviderStringVisitor()
        visitor.visit(tree)
        assert visitor.hits == [], (
            f"Bare provider name strings found in goose.py: {visitor.hits}"
        )


# ===========================================================================
# Behavioral: provider resolution returns correct constants
# ===========================================================================


class TestProviderResolutionUsesConstants:
    """Verify resolve_hand_model maps to correct provider names."""

    def test_default_resolves_to_ollama(self) -> None:
        result = resolve_hand_model(None)
        assert result.provider.name == _PROVIDER_OLLAMA

    def test_bare_claude_infers_anthropic(self) -> None:
        result = resolve_hand_model("claude-sonnet-4-5")
        assert result.provider.name == _PROVIDER_ANTHROPIC

    def test_bare_gemini_infers_google(self) -> None:
        result = resolve_hand_model("gemini-2.5-pro")
        assert result.provider.name == _PROVIDER_GOOGLE

    def test_bare_llama_infers_ollama(self) -> None:
        result = resolve_hand_model("llama3.2:latest")
        assert result.provider.name == _PROVIDER_OLLAMA

    def test_bare_gpt_infers_openai(self) -> None:
        result = resolve_hand_model("gpt-5.2")
        assert result.provider.name == _PROVIDER_OPENAI

    def test_explicit_provider_slash_model(self) -> None:
        result = resolve_hand_model("anthropic/claude-sonnet-4-5")
        assert result.provider.name == _PROVIDER_ANTHROPIC

    def test_provider_name_as_model_string(self) -> None:
        result = resolve_hand_model("openai")
        assert result.provider.name == _PROVIDER_OPENAI

    def test_constants_match_provider_registry(self) -> None:
        from helping_hands.lib.ai_providers import PROVIDERS

        for const in _ALL_CONSTANTS:
            assert const in PROVIDERS, f"{const!r} not in PROVIDERS registry"
            assert PROVIDERS[const].name == const
