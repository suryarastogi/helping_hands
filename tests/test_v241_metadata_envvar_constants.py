"""Tests for metadata key constants (backend/model/provider) and env var constants.

Validates that the new _META_BACKEND, _META_MODEL, _META_PROVIDER constants and
_ENV_GIT_TERMINAL_PROMPT, _ENV_GCM_INTERACTIVE constants hold expected values and
are consistently used across all hand modules.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    _ENV_GCM_INTERACTIVE,
    _ENV_GIT_TERMINAL_PROMPT,
    _META_BACKEND,
    _META_MODEL,
    _META_PROVIDER,
)

# ---------------------------------------------------------------------------
# Constant value tests
# ---------------------------------------------------------------------------


class TestMetadataKeyValues:
    """Each new _META_* constant must equal its canonical string key name."""

    def test_meta_backend(self) -> None:
        assert _META_BACKEND == "backend"

    def test_meta_model(self) -> None:
        assert _META_MODEL == "model"

    def test_meta_provider(self) -> None:
        assert _META_PROVIDER == "provider"


class TestEnvVarConstantValues:
    """Each _ENV_* constant must equal the actual env var name."""

    def test_env_git_terminal_prompt(self) -> None:
        assert _ENV_GIT_TERMINAL_PROMPT == "GIT_TERMINAL_PROMPT"

    def test_env_gcm_interactive(self) -> None:
        assert _ENV_GCM_INTERACTIVE == "GCM_INTERACTIVE"


class TestConstantTypes:
    """All new constants must be plain str instances."""

    @pytest.mark.parametrize(
        "const",
        [
            _META_BACKEND,
            _META_MODEL,
            _META_PROVIDER,
            _ENV_GIT_TERMINAL_PROMPT,
            _ENV_GCM_INTERACTIVE,
        ],
    )
    def test_is_str(self, const: str) -> None:
        assert isinstance(const, str)


class TestMetadataKeyUniqueness:
    """New _META_* constants must not collide with each other."""

    def test_all_unique(self) -> None:
        all_keys = [_META_BACKEND, _META_MODEL, _META_PROVIDER]
        assert len(all_keys) == len(set(all_keys))


class TestEnvVarUniqueness:
    """_ENV_* constants must not collide with each other."""

    def test_all_unique(self) -> None:
        all_keys = [_ENV_GIT_TERMINAL_PROMPT, _ENV_GCM_INTERACTIVE]
        assert len(all_keys) == len(set(all_keys))


# ---------------------------------------------------------------------------
# Docstring presence tests
# ---------------------------------------------------------------------------


class TestDocstrings:
    """All new constants must have docstrings."""

    def test_meta_backend_docstring(self) -> None:
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.base",
                fromlist=["_META_BACKEND"],
            )
        )
        assert '"""Metadata key for the execution backend name."""' in source

    def test_meta_model_docstring(self) -> None:
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.base",
                fromlist=["_META_MODEL"],
            )
        )
        assert '"""Metadata key for the AI model identifier."""' in source

    def test_meta_provider_docstring(self) -> None:
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.base",
                fromlist=["_META_PROVIDER"],
            )
        )
        assert '"""Metadata key for the AI provider name."""' in source

    def test_env_git_terminal_prompt_docstring(self) -> None:
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.base",
                fromlist=["_ENV_GIT_TERMINAL_PROMPT"],
            )
        )
        assert "suppress" in source.lower()
        assert "_ENV_GIT_TERMINAL_PROMPT" in source

    def test_env_gcm_interactive_docstring(self) -> None:
        source = inspect.getsource(
            __import__(
                "helping_hands.lib.hands.v1.hand.base",
                fromlist=["_ENV_GCM_INTERACTIVE"],
            )
        )
        assert "suppress" in source.lower()
        assert "_ENV_GCM_INTERACTIVE" in source


# ---------------------------------------------------------------------------
# Source-level consistency checks
# ---------------------------------------------------------------------------

_HAND_DIR = Path(
    inspect.getfile(
        __import__(
            "helping_hands.lib.hands.v1.hand.base",
            fromlist=["_META_BACKEND"],
        )
    )
).parent

_PROTOCOL_MODULES = [
    _HAND_DIR / "iterative.py",
    _HAND_DIR / "e2e.py",
    _HAND_DIR / "langgraph.py",
    _HAND_DIR / "atomic.py",
    _HAND_DIR / "cli" / "base.py",
]

# Bare strings that should now be replaced by constants in hand modules.
# We exclude strings that appear in non-metadata contexts (e.g. function
# parameter names, docstrings).
_METADATA_KEY_STRINGS = frozenset({"backend", "model", "provider"})


def _find_bare_metadata_keys_in_dict(source: str) -> list[tuple[int, str]]:
    """Return (line, key) for bare 'backend'/'model'/'provider' dict keys.

    Only flags string literals used as dictionary keys in dict literals
    (ast.Dict nodes), not in function calls, imports, or assignments.
    """
    tree = ast.parse(source)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key_node in node.keys:
                if (
                    isinstance(key_node, ast.Constant)
                    and key_node.value in _METADATA_KEY_STRINGS
                ):
                    hits.append((key_node.lineno, key_node.value))
    return hits


class TestNoBareMetadataKeysInDicts:
    """Ensure no hand module uses bare 'backend'/'model'/'provider' as dict keys."""

    @pytest.mark.parametrize(
        "module_path",
        _PROTOCOL_MODULES,
        ids=[p.name for p in _PROTOCOL_MODULES],
    )
    def test_no_bare_keys(self, module_path: Path) -> None:
        source = module_path.read_text()
        hits = _find_bare_metadata_keys_in_dict(source)
        if hits:
            detail = "\n".join(f"  line {ln}: {key!r}" for ln, key in hits)
            pytest.fail(
                f"{module_path.name} contains bare metadata key strings as dict keys "
                f"(use _META_* constants instead):\n{detail}"
            )


class TestBaseModuleDefinesNewConstants:
    """base.py must define all new constants."""

    @pytest.mark.parametrize(
        "const_name",
        [
            "_META_BACKEND",
            "_META_MODEL",
            "_META_PROVIDER",
            "_ENV_GIT_TERMINAL_PROMPT",
            "_ENV_GCM_INTERACTIVE",
        ],
    )
    def test_constant_defined(self, const_name: str) -> None:
        source = (_HAND_DIR / "base.py").read_text()
        assert const_name in source, f"base.py is missing constant {const_name}"


class TestNoBareEnvVarStringsInPushNoninteractive:
    """base.py _push_noninteractive should use _ENV_* constants, not bare strings."""

    def test_no_bare_env_strings(self) -> None:
        source = (_HAND_DIR / "base.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_push_noninteractive"
            ):
                method_source = ast.get_source_segment(source, node)
                assert method_source is not None
                method_tree = ast.parse(method_source)
                for sub_node in ast.walk(method_tree):
                    if isinstance(sub_node, ast.Constant) and sub_node.value in (
                        "GIT_TERMINAL_PROMPT",
                        "GCM_INTERACTIVE",
                    ):
                        pytest.fail(
                            f"_push_noninteractive contains bare env var string "
                            f"{sub_node.value!r} at line {sub_node.lineno} "
                            f"(use _ENV_* constants instead)"
                        )
                return
        pytest.fail("Could not find _push_noninteractive method in base.py")


class TestGithubUrlUsesEnvConstants:
    """github_url.py should use _ENV_* constants in noninteractive_env()."""

    def test_no_bare_env_strings(self) -> None:
        github_url_path = _HAND_DIR.parent.parent.parent / "github_url.py"
        source = github_url_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "noninteractive_env":
                method_source = ast.get_source_segment(source, node)
                assert method_source is not None
                method_tree = ast.parse(method_source)
                for sub_node in ast.walk(method_tree):
                    if isinstance(sub_node, ast.Constant) and sub_node.value in (
                        "GIT_TERMINAL_PROMPT",
                        "GCM_INTERACTIVE",
                    ):
                        pytest.fail(
                            f"noninteractive_env contains bare env var string "
                            f"{sub_node.value!r} (use _ENV_* constants instead)"
                        )
                return
        pytest.fail("Could not find noninteractive_env function")

    def test_defines_env_constants(self) -> None:
        github_url_path = _HAND_DIR.parent.parent.parent / "github_url.py"
        source = github_url_path.read_text()
        assert "_ENV_GIT_TERMINAL_PROMPT" in source
        assert "_ENV_GCM_INTERACTIVE" in source


class TestProtocolModulesImportNewConstants:
    """Modules that use metadata keys should import the new _META_* constants."""

    @pytest.mark.parametrize(
        ("module_path", "expected_imports"),
        [
            (
                _HAND_DIR / "atomic.py",
                ["_META_BACKEND", "_META_MODEL", "_META_PROVIDER"],
            ),
            (
                _HAND_DIR / "langgraph.py",
                ["_META_BACKEND", "_META_MODEL", "_META_PROVIDER"],
            ),
            (
                _HAND_DIR / "iterative.py",
                ["_META_BACKEND", "_META_MODEL", "_META_PROVIDER"],
            ),
            (_HAND_DIR / "e2e.py", ["_META_BACKEND", "_META_MODEL"]),
            (_HAND_DIR / "cli" / "base.py", ["_META_BACKEND", "_META_MODEL"]),
        ],
        ids=["atomic", "langgraph", "iterative", "e2e", "cli_base"],
    )
    def test_imports_present(
        self, module_path: Path, expected_imports: list[str]
    ) -> None:
        source = module_path.read_text()
        for imp in expected_imports:
            assert imp in source, f"{module_path.name} does not import {imp}"
