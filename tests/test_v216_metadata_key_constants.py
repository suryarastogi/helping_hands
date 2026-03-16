"""Tests for metadata key constants extracted in v216.

Validates that the _META_* constants in base.py hold the expected string
values and are consistently used across all hand modules that participate
in the PR/CI metadata protocol.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.base import (
    _META_CI_FIX_ATTEMPTS,
    _META_CI_FIX_ERROR,
    _META_CI_FIX_STATUS,
    _META_PR_BRANCH,
    _META_PR_COMMIT,
    _META_PR_NUMBER,
    _META_PR_STATUS,
    _META_PR_URL,
)

# ---------------------------------------------------------------------------
# Constant value tests
# ---------------------------------------------------------------------------


class TestMetadataKeyValues:
    """Each _META_* constant must equal its canonical string key name."""

    def test_meta_pr_status(self) -> None:
        assert _META_PR_STATUS == "pr_status"

    def test_meta_pr_url(self) -> None:
        assert _META_PR_URL == "pr_url"

    def test_meta_pr_number(self) -> None:
        assert _META_PR_NUMBER == "pr_number"

    def test_meta_pr_branch(self) -> None:
        assert _META_PR_BRANCH == "pr_branch"

    def test_meta_pr_commit(self) -> None:
        assert _META_PR_COMMIT == "pr_commit"

    def test_meta_ci_fix_status(self) -> None:
        assert _META_CI_FIX_STATUS == "ci_fix_status"

    def test_meta_ci_fix_attempts(self) -> None:
        assert _META_CI_FIX_ATTEMPTS == "ci_fix_attempts"

    def test_meta_ci_fix_error(self) -> None:
        assert _META_CI_FIX_ERROR == "ci_fix_error"


class TestMetadataKeyTypes:
    """All _META_* constants must be plain str instances."""

    @pytest.mark.parametrize(
        "const",
        [
            _META_PR_STATUS,
            _META_PR_URL,
            _META_PR_NUMBER,
            _META_PR_BRANCH,
            _META_PR_COMMIT,
            _META_CI_FIX_STATUS,
            _META_CI_FIX_ATTEMPTS,
            _META_CI_FIX_ERROR,
        ],
    )
    def test_is_str(self, const: str) -> None:
        assert isinstance(const, str)


class TestMetadataKeyUniqueness:
    """All _META_* constants must map to distinct string values."""

    def test_all_unique(self) -> None:
        all_keys = [
            _META_PR_STATUS,
            _META_PR_URL,
            _META_PR_NUMBER,
            _META_PR_BRANCH,
            _META_PR_COMMIT,
            _META_CI_FIX_STATUS,
            _META_CI_FIX_ATTEMPTS,
            _META_CI_FIX_ERROR,
        ]
        assert len(all_keys) == len(set(all_keys))


# ---------------------------------------------------------------------------
# Source-level consistency checks
# ---------------------------------------------------------------------------


_HAND_DIR = Path(
    inspect.getfile(
        __import__(
            "helping_hands.lib.hands.v1.hand.base",
            fromlist=["_META_PR_STATUS"],
        )
    )
).parent

# Modules that participate in the metadata dict protocol (excluding base.py
# where the constants are defined, and excluding server/ modules that use
# the same key strings for form fields / query params / dataclass fields).
_PROTOCOL_MODULES = [
    _HAND_DIR / "iterative.py",
    _HAND_DIR / "e2e.py",
    _HAND_DIR / "langgraph.py",
    _HAND_DIR / "atomic.py",
    _HAND_DIR / "cli" / "base.py",
]

_METADATA_KEY_STRINGS = frozenset(
    {
        "pr_status",
        "pr_url",
        "pr_number",
        "pr_branch",
        "pr_commit",
        "ci_fix_status",
        "ci_fix_attempts",
        "ci_fix_error",
    }
)


def _find_bare_metadata_keys(source: str) -> list[tuple[int, str]]:
    """Return (line, key) pairs for bare metadata key string literals.

    Walks the AST looking for ``ast.Constant`` nodes whose value is one of
    the metadata key strings.  Ignores constant *definitions* (assignments
    like ``_META_PR_STATUS = "pr_status"``).
    """
    tree = ast.parse(source)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in _METADATA_KEY_STRINGS:
            # Skip constant definitions in base.py
            hits.append((node.lineno, node.value))
    return hits


class TestNoBareMetadataKeysInProtocolModules:
    """Ensure no hand module uses bare metadata key strings."""

    @pytest.mark.parametrize(
        "module_path",
        _PROTOCOL_MODULES,
        ids=[p.name for p in _PROTOCOL_MODULES],
    )
    def test_no_bare_keys(self, module_path: Path) -> None:
        source = module_path.read_text()
        hits = _find_bare_metadata_keys(source)
        if hits:
            detail = "\n".join(f"  line {ln}: {key!r}" for ln, key in hits)
            pytest.fail(
                f"{module_path.name} contains bare metadata key strings "
                f"(use _META_* constants instead):\n{detail}"
            )


class TestBaseModuleDefinesAllKeys:
    """base.py must define all _META_* constants."""

    def test_all_constants_exported(self) -> None:
        source = (_HAND_DIR / "base.py").read_text()
        for key in sorted(_METADATA_KEY_STRINGS):
            const_name = f"_META_{key.upper()}"
            assert const_name in source, (
                f"base.py is missing constant {const_name} for key {key!r}"
            )


class TestProtocolModulesImportConstants:
    """Each protocol module must import the _META_* constants it uses."""

    @pytest.mark.parametrize(
        "module_path",
        _PROTOCOL_MODULES,
        ids=[p.name for p in _PROTOCOL_MODULES],
    )
    def test_imports_present(self, module_path: Path) -> None:
        source = module_path.read_text()
        # Check that the file imports at least one _META_ constant
        assert "_META_" in source, (
            f"{module_path.name} does not import any _META_* constants"
        )
