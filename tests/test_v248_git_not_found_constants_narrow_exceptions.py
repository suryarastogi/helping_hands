"""Tests for v248: git-not-found constants and narrowed run_async exceptions.

Covers:
- Constant values and types in pr_description.py
- AST source consistency: no bare "git not found" / "CLI not found" strings
- Narrowed exception handling in atomic.py and iterative.py
"""

from __future__ import annotations

import ast
from pathlib import Path

from helping_hands.lib.hands.v1.hand.pr_description import (
    _CLI_NOT_FOUND_MSG,
    _GIT_NOT_FOUND_DIFF_MSG,
    _GIT_NOT_FOUND_UNCOMMITTED_MSG,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "helping_hands"

_PR_DESCRIPTION_PATH = _SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "pr_description.py"
_ATOMIC_PATH = _SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "atomic.py"
_ITERATIVE_PATH = _SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "iterative.py"


# ===================================================================
# Constant values and types
# ===================================================================


class TestConstantValues:
    """Verify constant values and types."""

    def test_git_not_found_diff_msg_is_str(self) -> None:
        assert isinstance(_GIT_NOT_FOUND_DIFF_MSG, str)

    def test_git_not_found_uncommitted_msg_is_str(self) -> None:
        assert isinstance(_GIT_NOT_FOUND_UNCOMMITTED_MSG, str)

    def test_cli_not_found_msg_is_str(self) -> None:
        assert isinstance(_CLI_NOT_FOUND_MSG, str)

    def test_git_not_found_diff_msg_value(self) -> None:
        assert _GIT_NOT_FOUND_DIFF_MSG == "git not found on PATH; cannot compute diff"

    def test_git_not_found_uncommitted_msg_value(self) -> None:
        assert (
            _GIT_NOT_FOUND_UNCOMMITTED_MSG
            == "git not found on PATH; cannot compute uncommitted diff"
        )

    def test_cli_not_found_msg_value(self) -> None:
        assert _CLI_NOT_FOUND_MSG == "%s CLI not found"

    def test_git_not_found_diff_msg_non_empty(self) -> None:
        assert len(_GIT_NOT_FOUND_DIFF_MSG) > 0

    def test_git_not_found_uncommitted_msg_non_empty(self) -> None:
        assert len(_GIT_NOT_FOUND_UNCOMMITTED_MSG) > 0

    def test_cli_not_found_msg_non_empty(self) -> None:
        assert len(_CLI_NOT_FOUND_MSG) > 0

    def test_constants_are_distinct(self) -> None:
        values = {
            _GIT_NOT_FOUND_DIFF_MSG,
            _GIT_NOT_FOUND_UNCOMMITTED_MSG,
            _CLI_NOT_FOUND_MSG,
        }
        assert len(values) == 3


# ===================================================================
# AST source consistency — pr_description.py
# ===================================================================


def _collect_string_literals(path: Path) -> list[str]:
    """Return all string literals from a Python source file."""
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return literals


class TestASTSourceConsistency:
    """Ensure bare 'git not found' / 'CLI not found' strings are gone."""

    def test_no_bare_git_not_found_diff(self) -> None:
        literals = _collect_string_literals(_PR_DESCRIPTION_PATH)
        # The constant definition itself is allowed; usage sites must use the constant.
        # We check that the string only appears once (the definition).
        matches = [s for s in literals if s == _GIT_NOT_FOUND_DIFF_MSG]
        assert len(matches) == 1, (
            f"Expected exactly 1 occurrence (constant definition) of "
            f"{_GIT_NOT_FOUND_DIFF_MSG!r}, found {len(matches)}"
        )

    def test_no_bare_git_not_found_uncommitted(self) -> None:
        literals = _collect_string_literals(_PR_DESCRIPTION_PATH)
        matches = [s for s in literals if s == _GIT_NOT_FOUND_UNCOMMITTED_MSG]
        assert len(matches) == 1, (
            f"Expected exactly 1 occurrence (constant definition) of "
            f"{_GIT_NOT_FOUND_UNCOMMITTED_MSG!r}, found {len(matches)}"
        )

    def test_no_bare_cli_not_found_full_messages(self) -> None:
        """No full 'CLI not found at/for' messages remain as bare strings."""
        literals = _collect_string_literals(_PR_DESCRIPTION_PATH)
        bad = [
            s for s in literals if "CLI not found at" in s or "CLI not found for" in s
        ]
        assert bad == [], f"Bare CLI-not-found messages remain: {bad}"

    def test_cli_not_found_constant_defined_once(self) -> None:
        literals = _collect_string_literals(_PR_DESCRIPTION_PATH)
        matches = [s for s in literals if s == _CLI_NOT_FOUND_MSG]
        assert len(matches) == 1, (
            f"Expected exactly 1 occurrence of {_CLI_NOT_FOUND_MSG!r}, "
            f"found {len(matches)}"
        )


# ===================================================================
# AST source consistency — exception narrowing
# ===================================================================


def _find_except_exception_handlers(path: Path) -> list[int]:
    """Return line numbers of ``except Exception:`` handlers in a file."""
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    lines: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ):
            lines.append(node.lineno)
    return lines


class TestExceptionNarrowing:
    """Verify run_async handlers no longer use bare ``except Exception``."""

    def test_atomic_no_except_exception(self) -> None:
        lines = _find_except_exception_handlers(_ATOMIC_PATH)
        assert lines == [], f"atomic.py still has 'except Exception' at lines {lines}"

    def test_iterative_no_except_exception(self) -> None:
        lines = _find_except_exception_handlers(_ITERATIVE_PATH)
        assert lines == [], (
            f"iterative.py still has 'except Exception' at lines {lines}"
        )

    def test_atomic_has_narrowed_handler(self) -> None:
        """Verify the narrowed constant is used in atomic.py source."""
        source = _ATOMIC_PATH.read_text()
        assert "_RUN_ASYNC_ERRORS" in source

    def test_iterative_has_narrowed_handler(self) -> None:
        """Verify the narrowed constant is defined in iterative.py source."""
        source = _ITERATIVE_PATH.read_text()
        assert "_RUN_ASYNC_ERRORS" in source


# ===================================================================
# Behavioral — constant usage in logging
# ===================================================================


class TestConstantUsage:
    """Verify constants are used in the expected way."""

    def test_cli_not_found_msg_has_format_placeholder(self) -> None:
        """The CLI constant must contain %s for the CLI label."""
        assert "%s" in _CLI_NOT_FOUND_MSG

    def test_cli_not_found_msg_formats_correctly(self) -> None:
        result = _CLI_NOT_FOUND_MSG % "claude"
        assert result == "claude CLI not found"

    def test_git_not_found_diff_contains_git(self) -> None:
        assert "git" in _GIT_NOT_FOUND_DIFF_MSG.lower()

    def test_git_not_found_uncommitted_contains_uncommitted(self) -> None:
        assert "uncommitted" in _GIT_NOT_FOUND_UNCOMMITTED_MSG.lower()
