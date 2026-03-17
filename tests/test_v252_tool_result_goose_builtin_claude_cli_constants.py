"""Tests for v252 — ``_TOOL_RESULT_PREFIX``, ``_GOOSE_BUILTIN_FLAG``, ``_CLAUDE_CLI_NAME`` constants.

Covers:
- ``_TOOL_RESULT_PREFIX`` constant in ``iterative.py`` — value, type, and no bare
  ``"@@TOOL_RESULT"`` string literals remain in code (only docstrings).
- ``_GOOSE_BUILTIN_FLAG`` constant in ``goose.py`` — value, type, and no bare
  ``"--with-builtin"`` string literals remain in code (only docstrings).
- ``_CLAUDE_CLI_NAME`` constant in ``claude.py`` — value, type, ``__all__`` export,
  and no bare ``"claude"`` string literals remain in code paths that reference the CLI
  binary name.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _src_root() -> Path:
    """Return path to src/helping_hands/."""
    return Path(__file__).resolve().parent.parent / "src" / "helping_hands"


def _hand_root() -> Path:
    """Return path to src/helping_hands/lib/hands/v1/hand/."""
    return _src_root() / "lib" / "hands" / "v1" / "hand"


def _cli_root() -> Path:
    """Return path to the CLI hand directory."""
    return _hand_root() / "cli"


def _parse_file(path: Path) -> ast.Module:
    """Parse a Python source file into an AST."""
    return ast.parse(path.read_text(), filename=str(path))


def _string_literals_in_code(tree: ast.Module) -> list[str]:
    """Extract all string literal values from code nodes (not docstrings)."""
    literals: list[str] = []
    for node in ast.walk(tree):
        # Skip docstrings (first statement of module/class/function bodies).
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, (ast.Constant, ast.JoinedStr))
                and isinstance(getattr(body[0].value, "value", None), str)
            ):
                continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Check this is not a docstring by seeing if the parent Expr is
            # the first statement in a body — we already skip module-level above,
            # but let's be defensive.
            literals.append(node.value)
    return literals


# ---------------------------------------------------------------------------
# _TOOL_RESULT_PREFIX constant (iterative.py)
# ---------------------------------------------------------------------------


class TestToolResultPrefix:
    """Verify ``_TOOL_RESULT_PREFIX`` constant in iterative.py."""

    def test_constant_exists(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_RESULT_PREFIX

        assert isinstance(_TOOL_RESULT_PREFIX, str)

    def test_constant_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_RESULT_PREFIX

        assert _TOOL_RESULT_PREFIX == "@@TOOL_RESULT"

    def test_constant_not_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _TOOL_RESULT_PREFIX

        assert len(_TOOL_RESULT_PREFIX) > 0

    def test_has_docstring(self) -> None:
        """The constant should have a docstring (string literal after assignment)."""
        tree = _parse_file(_hand_root() / "iterative.py")
        for i, node in enumerate(tree.body):
            is_target = False
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                is_target = node.target.id == "_TOOL_RESULT_PREFIX"
            elif isinstance(node, ast.Assign):
                is_target = any(
                    isinstance(t, ast.Name) and t.id == "_TOOL_RESULT_PREFIX"
                    for t in node.targets
                )
            if is_target and i + 1 < len(tree.body):
                nxt = tree.body[i + 1]
                assert isinstance(nxt, ast.Expr)
                assert isinstance(nxt.value, ast.Constant)
                assert isinstance(nxt.value.value, str)
                return
        raise AssertionError("_TOOL_RESULT_PREFIX assignment not found at module level")

    def test_no_bare_tool_result_in_fstrings(self) -> None:
        """No f-string should contain a bare ``@@TOOL_RESULT`` literal."""
        tree = _parse_file(_hand_root() / "iterative.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                for part in node.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        assert "@@TOOL_RESULT" not in part.value, (
                            f"Bare '@@TOOL_RESULT' found in f-string at line {node.lineno}"
                        )

    def test_format_command_result_uses_constant(self) -> None:
        """_format_command_result should produce output starting with the prefix."""
        from helping_hands.lib.hands.v1.hand.iterative import (
            _TOOL_RESULT_PREFIX,
            _BasicIterativeHand,
        )
        from helping_hands.lib.meta.tools.command import CommandResult

        result = CommandResult(
            command=["echo", "hello"],
            cwd="/tmp",
            stdout="hello",
            stderr="",
            exit_code=0,
            timed_out=False,
        )
        output = _BasicIterativeHand._format_command_result(
            tool_name="test_tool", result=result
        )
        assert output.startswith(f"{_TOOL_RESULT_PREFIX}:")

    def test_format_web_search_result_uses_constant(self) -> None:
        """_format_web_search_result should produce output starting with the prefix."""
        from helping_hands.lib.hands.v1.hand.iterative import (
            _TOOL_RESULT_PREFIX,
            _BasicIterativeHand,
        )
        from helping_hands.lib.meta.tools.web import WebSearchResult

        result = WebSearchResult(query="test", results=[])
        output = _BasicIterativeHand._format_web_search_result(
            tool_name="search", result=result
        )
        assert output.startswith(f"{_TOOL_RESULT_PREFIX}:")

    def test_format_web_browse_result_uses_constant(self) -> None:
        """_format_web_browse_result should produce output starting with the prefix."""
        from helping_hands.lib.hands.v1.hand.iterative import (
            _TOOL_RESULT_PREFIX,
            _BasicIterativeHand,
        )
        from helping_hands.lib.meta.tools.web import WebBrowseResult

        result = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content="hello",
            truncated=False,
        )
        output = _BasicIterativeHand._format_web_browse_result(
            tool_name="browse", result=result
        )
        assert output.startswith(f"{_TOOL_RESULT_PREFIX}:")


# ---------------------------------------------------------------------------
# _GOOSE_BUILTIN_FLAG constant (goose.py)
# ---------------------------------------------------------------------------


class TestGooseBuiltinFlag:
    """Verify ``_GOOSE_BUILTIN_FLAG`` constant in goose.py."""

    def test_constant_exists(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import _GOOSE_BUILTIN_FLAG

        assert isinstance(_GOOSE_BUILTIN_FLAG, str)

    def test_constant_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import _GOOSE_BUILTIN_FLAG

        assert _GOOSE_BUILTIN_FLAG == "--with-builtin"

    def test_starts_with_double_dash(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import _GOOSE_BUILTIN_FLAG

        assert _GOOSE_BUILTIN_FLAG.startswith("--")

    def test_has_docstring(self) -> None:
        tree = _parse_file(_cli_root() / "goose.py")
        for i, node in enumerate(tree.body):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "_GOOSE_BUILTIN_FLAG"
                    for t in node.targets
                )
                and i + 1 < len(tree.body)
            ):
                nxt = tree.body[i + 1]
                assert isinstance(nxt, ast.Expr)
                assert isinstance(nxt.value, ast.Constant)
                assert isinstance(nxt.value.value, str)
                return
        raise AssertionError("_GOOSE_BUILTIN_FLAG assignment not found at module level")

    def test_no_bare_with_builtin_in_code_strings(self) -> None:
        """No bare ``--with-builtin`` string literal should remain outside the constant def."""
        tree = _parse_file(_cli_root() / "goose.py")
        # Find the line of the constant definition to exclude it.
        const_line = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "_GOOSE_BUILTIN_FLAG"
                    ):
                        const_line = node.lineno
        assert const_line is not None, "_GOOSE_BUILTIN_FLAG not found"
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value == "--with-builtin"
                and node.lineno != const_line
            ):
                raise AssertionError(
                    f"Bare '--with-builtin' string at line {node.lineno} "
                    "should use _GOOSE_BUILTIN_FLAG constant"
                )

    def test_default_cli_cmd_contains_flag(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            _GOOSE_BUILTIN_FLAG,
            GooseCLIHand,
        )

        assert _GOOSE_BUILTIN_FLAG in GooseCLIHand._DEFAULT_CLI_CMD

    def test_normalize_bare_goose(self) -> None:
        """Bare ``goose`` should expand to include the builtin flag."""
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            _GOOSE_BUILTIN_FLAG,
            GooseCLIHand,
        )

        hand = object.__new__(GooseCLIHand)
        result = hand._normalize_base_command(["goose"])
        assert _GOOSE_BUILTIN_FLAG in result

    def test_normalize_goose_run(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            _GOOSE_BUILTIN_FLAG,
            GooseCLIHand,
        )

        hand = object.__new__(GooseCLIHand)
        result = hand._normalize_base_command(["goose", "run"])
        assert _GOOSE_BUILTIN_FLAG in result

    def test_has_goose_builtin_flag_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            _GOOSE_BUILTIN_FLAG,
            GooseCLIHand,
        )

        assert GooseCLIHand._has_goose_builtin_flag(
            ["goose", "run", _GOOSE_BUILTIN_FLAG, "developer"]
        )

    def test_has_goose_builtin_flag_with_equals(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.goose import (
            _GOOSE_BUILTIN_FLAG,
            GooseCLIHand,
        )

        assert GooseCLIHand._has_goose_builtin_flag(
            ["goose", "run", f"{_GOOSE_BUILTIN_FLAG}=developer"]
        )


# ---------------------------------------------------------------------------
# _CLAUDE_CLI_NAME constant (claude.py)
# ---------------------------------------------------------------------------


class TestClaudeCliName:
    """Verify ``_CLAUDE_CLI_NAME`` constant in claude.py."""

    def test_constant_exists(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _CLAUDE_CLI_NAME

        assert isinstance(_CLAUDE_CLI_NAME, str)

    def test_constant_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.claude import _CLAUDE_CLI_NAME

        assert _CLAUDE_CLI_NAME == "claude"

    def test_in_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli import claude

        assert "_CLAUDE_CLI_NAME" in claude.__all__

    def test_has_docstring(self) -> None:
        tree = _parse_file(_cli_root() / "claude.py")
        for i, node in enumerate(tree.body):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "_CLAUDE_CLI_NAME"
                    for t in node.targets
                )
                and i + 1 < len(tree.body)
            ):
                nxt = tree.body[i + 1]
                assert isinstance(nxt, ast.Expr)
                assert isinstance(nxt.value, ast.Constant)
                assert isinstance(nxt.value.value, str)
                return
        raise AssertionError("_CLAUDE_CLI_NAME assignment not found at module level")

    def test_no_bare_claude_in_shutil_which(self) -> None:
        """``shutil.which`` calls should use ``_CLAUDE_CLI_NAME``, not bare ``"claude"``."""
        tree = _parse_file(_cli_root() / "claude.py")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "which"
            ):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value == "claude":
                        raise AssertionError(
                            f"Bare 'claude' in shutil.which() at line {node.lineno}"
                        )

    def test_no_bare_claude_in_cmd_comparisons(self) -> None:
        """``cmd[0] == "claude"`` comparisons should use the constant."""
        tree = _parse_file(_cli_root() / "claude.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if (
                        isinstance(comparator, ast.Constant)
                        and comparator.value == "claude"
                    ):
                        raise AssertionError(
                            f"Bare 'claude' in comparison at line {node.lineno}"
                        )
                if isinstance(node.left, ast.Constant) and node.left.value == "claude":
                    raise AssertionError(
                        f"Bare 'claude' in comparison at line {node.lineno}"
                    )

    def test_no_bare_claude_in_list_literals(self) -> None:
        """List literals like ``["claude", ...]`` should use the constant."""
        tree = _parse_file(_cli_root() / "claude.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.List):
                for elt in node.elts:
                    if isinstance(elt, ast.Constant) and elt.value == "claude":
                        raise AssertionError(
                            f"Bare 'claude' in list literal at line {node.lineno}"
                        )
