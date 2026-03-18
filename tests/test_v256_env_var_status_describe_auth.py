"""Tests for v256: DRY _env_var_status() helper for CLI auth descriptions.

- _env_var_status returns "set" or "not set" correctly
- All _describe_auth overrides use _env_var_status (no inline os.environ.get)
- No stale `import os` in gemini.py, goose.py, opencode.py _describe_auth
"""

from __future__ import annotations

import ast
import inspect

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

# ---------------------------------------------------------------------------
# _env_var_status unit tests
# ---------------------------------------------------------------------------


class TestEnvVarStatus:
    """Unit tests for _TwoPhaseCLIHand._env_var_status."""

    def test_set_when_populated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_V256_KEY", "secret123")
        assert _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY") == "set"

    def test_not_set_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_V256_KEY", raising=False)
        assert _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY") == "not set"

    def test_not_set_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_V256_KEY", "")
        assert _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY") == "not set"

    def test_not_set_when_whitespace_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_V256_KEY", "   \t  ")
        assert _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY") == "not set"

    def test_set_with_leading_trailing_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_V256_KEY", "  val  ")
        assert _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY") == "set"

    def test_return_type_is_str(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_V256_KEY", raising=False)
        result = _TwoPhaseCLIHand._env_var_status("TEST_V256_KEY")
        assert isinstance(result, str)

    def test_is_static_method(self) -> None:
        """_env_var_status should be a staticmethod on the class."""
        assert isinstance(
            inspect.getattr_static(_TwoPhaseCLIHand, "_env_var_status"),
            staticmethod,
        )

    def test_has_docstring(self) -> None:
        assert _TwoPhaseCLIHand._env_var_status.__doc__
        assert "set" in _TwoPhaseCLIHand._env_var_status.__doc__


# ---------------------------------------------------------------------------
# AST source consistency: _describe_auth must NOT use os.environ.get inline
# ---------------------------------------------------------------------------

_CLI_HAND_MODULES = (
    "helping_hands.lib.hands.v1.hand.cli.claude",
    "helping_hands.lib.hands.v1.hand.cli.gemini",
    "helping_hands.lib.hands.v1.hand.cli.goose",
    "helping_hands.lib.hands.v1.hand.cli.opencode",
    "helping_hands.lib.hands.v1.hand.cli.base",
)


class TestDescribeAuthConsistency:
    """Verify all _describe_auth overrides use _env_var_status."""

    @pytest.mark.parametrize("module_name", _CLI_HAND_MODULES)
    def test_no_inline_environ_get_in_describe_auth(self, module_name: str) -> None:
        """_describe_auth methods must not call os.environ.get directly."""
        import importlib

        mod = importlib.import_module(module_name)
        src = inspect.getsource(mod)
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != "_describe_auth":
                continue
            # Get the source of just this method
            method_src = ast.get_source_segment(src, node)
            if method_src is None:
                continue
            assert "os.environ.get" not in method_src, (
                f"{module_name}._describe_auth still contains inline "
                f"os.environ.get — should use _env_var_status instead"
            )

    def test_env_var_status_on_two_phase_class(self) -> None:
        """_env_var_status should be accessible on _TwoPhaseCLIHand."""
        assert hasattr(_TwoPhaseCLIHand, "_env_var_status")
        assert callable(_TwoPhaseCLIHand._env_var_status)


# ---------------------------------------------------------------------------
# No stale `import os` in subclass modules that no longer need it
# ---------------------------------------------------------------------------


class TestNoStaleOsImport:
    """Verify modules that used `import os` only for _describe_auth removed it."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "helping_hands.lib.hands.v1.hand.cli.gemini",
            "helping_hands.lib.hands.v1.hand.cli.opencode",
        ],
    )
    def test_no_top_level_os_import(self, module_name: str) -> None:
        """Module should not have a bare `import os` at the top level."""
        import importlib

        mod = importlib.import_module(module_name)
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "os", (
                        f"{module_name} has stale top-level `import os`"
                    )
