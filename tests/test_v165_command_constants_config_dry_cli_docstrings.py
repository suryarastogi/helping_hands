"""Tests for v165: Unix exit code constants, shared truthy-env parsing, and CLI docstrings.

Exit codes 124 (timeout), 126 (cannot execute), and 127 (not found) are standard
Unix conventions used by bash wrappers.  If command.py reports the wrong code,
calling code that branches on exit status (e.g. detecting "command not found" vs
"permission denied") will silently mis-classify failures.  The "distinct values"
test ensures no two codes were accidentally set to the same number.

_TRUTHY_VALUES and _is_truthy_env centralise boolean environment variable parsing;
without a shared definition, individual helpers could accept "1" but not "yes", or
accept "TRUE" but not "true".  The e2e.py reuse test verifies the module imports the
shared definition rather than rolling its own.

Docstring presence tests on _TwoPhaseCLIHand methods enforce the project's
Google-style documentation requirement for public helpers consumed by subclasses.
"""

from __future__ import annotations

import inspect

import pytest

from helping_hands.lib.config import _TRUTHY_VALUES, _is_truthy_env
from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand
from helping_hands.lib.meta.tools.command import (
    _EXIT_CODE_CANNOT_EXECUTE,
    _EXIT_CODE_NOT_FOUND,
    _EXIT_CODE_TIMEOUT,
)

# ---------------------------------------------------------------------------
# command.py — exit code constants
# ---------------------------------------------------------------------------


class TestCommandExitCodeConstants:
    """Verify exit code constants match standard Unix conventions."""

    def test_timeout_is_124(self):
        assert _EXIT_CODE_TIMEOUT == 124

    def test_not_found_is_127(self):
        assert _EXIT_CODE_NOT_FOUND == 127

    def test_cannot_execute_is_126(self):
        assert _EXIT_CODE_CANNOT_EXECUTE == 126

    def test_constants_are_int(self):
        assert isinstance(_EXIT_CODE_TIMEOUT, int)
        assert isinstance(_EXIT_CODE_NOT_FOUND, int)
        assert isinstance(_EXIT_CODE_CANNOT_EXECUTE, int)

    def test_constants_are_distinct(self):
        values = {_EXIT_CODE_TIMEOUT, _EXIT_CODE_NOT_FOUND, _EXIT_CODE_CANNOT_EXECUTE}
        assert len(values) == 3


# ---------------------------------------------------------------------------
# config.py — _TRUTHY_VALUES and _is_truthy_env
# ---------------------------------------------------------------------------


class TestTruthyValues:
    """Verify the truthy values constant and helper."""

    def test_truthy_values_contains_expected(self):
        assert "1" in _TRUTHY_VALUES
        assert "true" in _TRUTHY_VALUES
        assert "yes" in _TRUTHY_VALUES

    def test_truthy_values_is_frozenset(self):
        assert isinstance(_TRUTHY_VALUES, frozenset)

    def test_truthy_values_length(self):
        assert len(_TRUTHY_VALUES) == 4

    def test_false_values_not_in_truthy(self):
        for val in ("0", "false", "no", "", "maybe"):
            assert val not in _TRUTHY_VALUES


class TestIsTruthyEnv:
    """Verify _is_truthy_env helper."""

    def test_truthy_env_true(self, monkeypatch):
        monkeypatch.setenv("TEST_TRUTHY", "true")
        assert _is_truthy_env("TEST_TRUTHY") is True

    def test_truthy_env_yes(self, monkeypatch):
        monkeypatch.setenv("TEST_TRUTHY", "YES")
        assert _is_truthy_env("TEST_TRUTHY") is True

    def test_truthy_env_one(self, monkeypatch):
        monkeypatch.setenv("TEST_TRUTHY", "1")
        assert _is_truthy_env("TEST_TRUTHY") is True

    def test_truthy_env_false(self, monkeypatch):
        monkeypatch.setenv("TEST_TRUTHY", "false")
        assert _is_truthy_env("TEST_TRUTHY") is False

    def test_truthy_env_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_TRUTHY", raising=False)
        assert _is_truthy_env("TEST_TRUTHY") is False

    def test_truthy_env_default_override(self, monkeypatch):
        monkeypatch.delenv("TEST_TRUTHY", raising=False)
        assert _is_truthy_env("TEST_TRUTHY", default="true") is True

    def test_truthy_env_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("TEST_TRUTHY", "True")
        assert _is_truthy_env("TEST_TRUTHY") is True


# ---------------------------------------------------------------------------
# e2e.py — _TRUTHY_VALUES import
# ---------------------------------------------------------------------------


class TestE2ETruthyImport:
    """Verify e2e.py uses _is_truthy_env from config."""

    def test_e2e_imports_is_truthy_env(self):
        from helping_hands.lib.config import _is_truthy_env
        from helping_hands.lib.hands.v1.hand import e2e

        # The module should reference the same _is_truthy_env function
        assert hasattr(e2e, "_is_truthy_env")
        assert e2e._is_truthy_env is _is_truthy_env


# ---------------------------------------------------------------------------
# cli/base.py — docstring presence on public and template methods
# ---------------------------------------------------------------------------

_PUBLIC_METHODS_WITH_DOCSTRINGS = [
    "interrupt",
    "run",
    "stream",
]

_TEMPLATE_METHODS_WITH_DOCSTRINGS = [
    "_command_not_found_message",
    "_fallback_command_when_not_found",
    "_retry_command_after_failure",
    "_no_change_error_after_retries",
]


class TestCLIHandDocstrings:
    """Verify that public and template methods have Google-style docstrings."""

    @pytest.mark.parametrize("method_name", _PUBLIC_METHODS_WITH_DOCSTRINGS)
    def test_public_method_has_docstring(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, f"{method_name} is missing a docstring"

    @pytest.mark.parametrize("method_name", _TEMPLATE_METHODS_WITH_DOCSTRINGS)
    def test_template_method_has_docstring(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert doc and len(doc.strip()) >= 10, f"{method_name} is missing a docstring"

    @pytest.mark.parametrize("method_name", _TEMPLATE_METHODS_WITH_DOCSTRINGS)
    def test_template_method_docstring_has_args(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert "Args:" in doc, f"{method_name} docstring missing Args section"

    @pytest.mark.parametrize("method_name", _TEMPLATE_METHODS_WITH_DOCSTRINGS)
    def test_template_method_docstring_has_returns(self, method_name):
        method = getattr(_TwoPhaseCLIHand, method_name)
        doc = inspect.getdoc(method)
        assert "Returns:" in doc or "Return" in doc, (
            f"{method_name} docstring missing Returns section"
        )

    def test_run_docstring_has_args(self):
        doc = inspect.getdoc(_TwoPhaseCLIHand.run)
        assert "Args:" in doc

    def test_stream_docstring_has_yields(self):
        doc = inspect.getdoc(_TwoPhaseCLIHand.stream)
        assert "Yields:" in doc
