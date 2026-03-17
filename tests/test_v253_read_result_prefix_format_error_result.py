"""Tests for v253 — ``_READ_RESULT_PREFIX`` constant and ``_format_error_result`` refactor.

Covers:
- ``_READ_RESULT_PREFIX`` constant in ``iterative.py`` — value, type, docstring,
  and no bare ``"@@READ_RESULT"`` string literals remain in f-strings.
- ``_format_error_result`` refactored to accept a prefix constant instead of
  a tag string — both ``_READ_RESULT_PREFIX`` and ``_TOOL_RESULT_PREFIX`` paths.
- No bare ``"READ"`` or ``"TOOL"`` tag strings remain in ``_format_error_result``
  call sites.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _hand_root() -> Path:
    """Return path to src/helping_hands/lib/hands/v1/hand/."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "helping_hands"
        / "lib"
        / "hands"
        / "v1"
        / "hand"
    )


def _parse_file(path: Path) -> ast.Module:
    """Parse a Python source file into an AST."""
    return ast.parse(path.read_text(), filename=str(path))


# ---------------------------------------------------------------------------
# _READ_RESULT_PREFIX constant
# ---------------------------------------------------------------------------


class TestReadResultPrefix:
    """Verify ``_READ_RESULT_PREFIX`` constant in iterative.py."""

    def test_constant_exists(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _READ_RESULT_PREFIX

        assert isinstance(_READ_RESULT_PREFIX, str)

    def test_constant_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _READ_RESULT_PREFIX

        assert _READ_RESULT_PREFIX == "@@READ_RESULT"

    def test_constant_not_empty(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import _READ_RESULT_PREFIX

        assert len(_READ_RESULT_PREFIX) > 0

    def test_has_docstring(self) -> None:
        """The constant should have a docstring (string literal after assignment)."""
        tree = _parse_file(_hand_root() / "iterative.py")
        for i, node in enumerate(tree.body):
            is_target = False
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                is_target = node.target.id == "_READ_RESULT_PREFIX"
            elif isinstance(node, ast.Assign):
                is_target = any(
                    isinstance(t, ast.Name) and t.id == "_READ_RESULT_PREFIX"
                    for t in node.targets
                )
            if is_target and i + 1 < len(tree.body):
                nxt = tree.body[i + 1]
                assert isinstance(nxt, ast.Expr)
                assert isinstance(nxt.value, ast.Constant)
                assert isinstance(nxt.value.value, str)
                return
        raise AssertionError("_READ_RESULT_PREFIX assignment not found at module level")

    def test_no_bare_read_result_in_fstrings(self) -> None:
        """No f-string outside prompt templates should contain a bare ``@@READ_RESULT``."""
        tree = _parse_file(_hand_root() / "iterative.py")
        # Prompt-builder methods contain user-facing instructions that
        # legitimately reference @@READ_RESULT as protocol documentation.
        prompt_methods = {"_build_iteration_prompt", "_tool_instructions"}

        # Collect line ranges of prompt-builder methods to exclude.
        excluded_ranges: list[tuple[int, int]] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in prompt_methods
            ):
                excluded_ranges.append((node.lineno, node.end_lineno or node.lineno))

        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                if any(start <= node.lineno <= end for start, end in excluded_ranges):
                    continue
                for part in node.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        assert "@@READ_RESULT" not in part.value, (
                            f"Bare '@@READ_RESULT' found in f-string at line {node.lineno}"
                        )

    def test_parallel_to_tool_result_prefix(self) -> None:
        """``_READ_RESULT_PREFIX`` should follow the same pattern as ``_TOOL_RESULT_PREFIX``."""
        from helping_hands.lib.hands.v1.hand.iterative import (
            _READ_RESULT_PREFIX,
            _TOOL_RESULT_PREFIX,
        )

        assert _READ_RESULT_PREFIX.startswith("@@")
        assert _TOOL_RESULT_PREFIX.startswith("@@")
        assert _READ_RESULT_PREFIX != _TOOL_RESULT_PREFIX

    def test_distinct_from_tool_result_prefix(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _READ_RESULT_PREFIX,
            _TOOL_RESULT_PREFIX,
        )

        assert _READ_RESULT_PREFIX != _TOOL_RESULT_PREFIX


# ---------------------------------------------------------------------------
# _format_error_result refactor
# ---------------------------------------------------------------------------


class TestFormatErrorResult:
    """Verify ``_format_error_result`` accepts prefix constants."""

    def test_read_prefix(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _READ_RESULT_PREFIX,
            _BasicIterativeHand,
        )

        result = _BasicIterativeHand._format_error_result(
            _READ_RESULT_PREFIX, "foo.py", "file not found"
        )
        assert result == "@@READ_RESULT: foo.py\nERROR: file not found"

    def test_tool_prefix(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _TOOL_RESULT_PREFIX,
            _BasicIterativeHand,
        )

        result = _BasicIterativeHand._format_error_result(
            _TOOL_RESULT_PREFIX, "bash", "command failed"
        )
        assert result == "@@TOOL_RESULT: bash\nERROR: command failed"

    def test_output_starts_with_prefix(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _READ_RESULT_PREFIX,
            _BasicIterativeHand,
        )

        result = _BasicIterativeHand._format_error_result(
            _READ_RESULT_PREFIX, "test.txt", "some error"
        )
        assert result.startswith(_READ_RESULT_PREFIX)

    def test_output_contains_error_line(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _TOOL_RESULT_PREFIX,
            _BasicIterativeHand,
        )

        result = _BasicIterativeHand._format_error_result(
            _TOOL_RESULT_PREFIX, "tool", "boom"
        )
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[1] == "ERROR: boom"

    def test_name_in_first_line(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            _READ_RESULT_PREFIX,
            _BasicIterativeHand,
        )

        result = _BasicIterativeHand._format_error_result(
            _READ_RESULT_PREFIX, "my/path.py", "error"
        )
        first_line = result.split("\n")[0]
        assert "my/path.py" in first_line

    def test_first_param_is_prefix_not_tag(self) -> None:
        """The first parameter should be named ``prefix``, not ``tag``."""
        import inspect

        from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

        sig = inspect.signature(_BasicIterativeHand._format_error_result)
        params = list(sig.parameters.keys())
        assert params[0] == "prefix"

    def test_no_bare_read_or_tool_tag_in_call_sites(self) -> None:
        """No call to ``_format_error_result`` should pass bare ``"READ"`` or ``"TOOL"``."""
        tree = _parse_file(_hand_root() / "iterative.py")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = None
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name != "_format_error_result":
                continue
            # First positional arg should not be a bare "READ" or "TOOL" string
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(
                    first_arg.value, str
                ):
                    assert first_arg.value not in ("READ", "TOOL"), (
                        f"Bare tag string {first_arg.value!r} found at line {node.lineno}"
                    )

    def test_no_dynamic_tag_construction_in_method(self) -> None:
        """The method body should not contain ``@@{{tag}}_RESULT`` dynamic construction."""
        tree = _parse_file(_hand_root() / "iterative.py")
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_format_error_result"
            ):
                # Check there are no f-strings with "@@" and "_RESULT" parts
                for child in ast.walk(node):
                    if isinstance(child, ast.JoinedStr):
                        parts = []
                        for v in child.values:
                            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                                parts.append(v.value)
                        combined = "".join(parts)
                        assert "@@" not in combined, (
                            "Dynamic @@tag_RESULT construction found in _format_error_result"
                        )
                return
        raise AssertionError("_format_error_result method not found")
