"""Tests for v257 — centralize DEFAULT_MAX_ITERATIONS constant.

Verifies that:
1. The canonical definition lives in ``iterative.py``.
2. ``server/constants.py`` re-exports the same object (identity check).
3. No bare ``6`` remains as a ``max_iterations`` default in any source file.
4. The constant has the expected value and type.
5. All iterative hand ``__init__`` signatures reference the constant.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "helping_hands"
_ITERATIVE_PY = _SRC / "lib" / "hands" / "v1" / "hand" / "iterative.py"
_CONSTANTS_PY = _SRC / "server" / "constants.py"
_MCP_SERVER_PY = _SRC / "server" / "mcp_server.py"
_CELERY_APP_PY = _SRC / "server" / "celery_app.py"


# ---------------------------------------------------------------------------
# Value / type tests
# ---------------------------------------------------------------------------
class TestDefaultMaxIterationsValue:
    """Verify the constant value and type."""

    def test_value_is_six(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import DEFAULT_MAX_ITERATIONS

        assert DEFAULT_MAX_ITERATIONS == 6

    def test_type_is_int(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import DEFAULT_MAX_ITERATIONS

        assert isinstance(DEFAULT_MAX_ITERATIONS, int)

    def test_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import DEFAULT_MAX_ITERATIONS

        assert DEFAULT_MAX_ITERATIONS > 0

    def test_has_docstring(self) -> None:
        """The constant should have a module-level docstring below it."""
        source = _ITERATIVE_PY.read_text()
        tree = ast.parse(source)
        for i, node in enumerate(tree.body):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "DEFAULT_MAX_ITERATIONS"
            ):
                # Next statement should be an Expr(Constant(str))
                nxt = tree.body[i + 1]
                assert isinstance(nxt, ast.Expr) and isinstance(
                    nxt.value, ast.Constant
                ), "Expected a docstring after DEFAULT_MAX_ITERATIONS"
                assert isinstance(nxt.value.value, str)
                break
        else:
            pytest.fail("DEFAULT_MAX_ITERATIONS not found in iterative.py")


# ---------------------------------------------------------------------------
# Identity / re-export tests
# ---------------------------------------------------------------------------
class TestReExportIdentity:
    """server/constants.py must re-export the same object, not redefine."""

    def test_constants_reexports_same_object(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            DEFAULT_MAX_ITERATIONS as LIB_VAL,
        )
        from helping_hands.server.constants import (
            DEFAULT_MAX_ITERATIONS as SRV_VAL,
        )

        assert LIB_VAL is SRV_VAL

    def test_constants_py_has_no_local_assignment(self) -> None:
        """server/constants.py must not define DEFAULT_MAX_ITERATIONS locally."""
        source = _CONSTANTS_PY.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "DEFAULT_MAX_ITERATIONS"
                    ):
                        pytest.fail(
                            "server/constants.py still has a local assignment "
                            "for DEFAULT_MAX_ITERATIONS"
                        )

    def test_in_constants_all(self) -> None:
        from helping_hands.server.constants import __all__

        assert "DEFAULT_MAX_ITERATIONS" in __all__

    def test_in_iterative_all(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import __all__

        assert "DEFAULT_MAX_ITERATIONS" in __all__


# ---------------------------------------------------------------------------
# AST-based no-bare-6 tests
# ---------------------------------------------------------------------------
def _find_bare_max_iterations_defaults(filepath: Path) -> list[str]:
    """Return function names where ``max_iterations`` defaults to a bare ``6``."""
    source = filepath.read_text()
    tree = ast.parse(source)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg, default in zip(
                reversed(node.args.args + node.args.kwonlyargs),
                reversed(node.args.defaults + node.args.kw_defaults),
                strict=False,
            ):
                if (
                    arg.arg == "max_iterations"
                    and isinstance(default, ast.Constant)
                    and default.value == 6
                ):
                    violations.append(
                        f"{filepath.name}:{node.name}() still uses bare 6"
                    )
    return violations


class TestNoBareMaxIterationsDefault:
    """No source file should use ``max_iterations: int = 6`` (bare literal)."""

    def test_iterative_py(self) -> None:
        assert _find_bare_max_iterations_defaults(_ITERATIVE_PY) == []

    def test_mcp_server_py(self) -> None:
        assert _find_bare_max_iterations_defaults(_MCP_SERVER_PY) == []

    def test_celery_app_py(self) -> None:
        assert _find_bare_max_iterations_defaults(_CELERY_APP_PY) == []


# ---------------------------------------------------------------------------
# Behavioral tests: hand __init__ signatures
# ---------------------------------------------------------------------------
class TestHandInitSignatures:
    """Verify that iterative hand constructors accept max_iterations."""

    def test_basic_iterative_hand_default(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            DEFAULT_MAX_ITERATIONS,
            _BasicIterativeHand,
        )

        sig = inspect.signature(_BasicIterativeHand.__init__)
        param = sig.parameters["max_iterations"]
        assert param.default == DEFAULT_MAX_ITERATIONS

    def test_basic_langgraph_hand_default(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            DEFAULT_MAX_ITERATIONS,
            BasicLangGraphHand,
        )

        sig = inspect.signature(BasicLangGraphHand.__init__)
        param = sig.parameters["max_iterations"]
        assert param.default == DEFAULT_MAX_ITERATIONS

    def test_basic_atomic_hand_default(self) -> None:
        from helping_hands.lib.hands.v1.hand.iterative import (
            DEFAULT_MAX_ITERATIONS,
            BasicAtomicHand,
        )

        sig = inspect.signature(BasicAtomicHand.__init__)
        param = sig.parameters["max_iterations"]
        assert param.default == DEFAULT_MAX_ITERATIONS
