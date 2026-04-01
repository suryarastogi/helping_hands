"""Protect centralized env-var parsing for PR-description timeout and diff-char-limit settings.

_timeout_seconds and _diff_char_limit previously duplicated try/except,
non-positive guards, and logger.warning calls. If the duplication returns,
a fix to one function's fallback logic can miss the other, causing silent
misconfiguration (e.g. negative timeout accepted, or wrong warning text).

The AST one-liner checks are the key invariant: they ensure both functions
remain single-return delegations to _parse_positive_env_var, so CI catches
any re-introduced branching before duplication re-establishes itself.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

from helping_hands.lib.hands.v1.hand.pr_description import (
    _DEFAULT_DIFF_CHAR_LIMIT,
    _DEFAULT_TIMEOUT_SECONDS,
    _DIFF_LIMIT_ENV_VAR,
    _TIMEOUT_ENV_VAR,
    _diff_char_limit,
    _parse_positive_env_var,
    _timeout_seconds,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "helping_hands"
_PR_DESCRIPTION_PATH = _SRC_ROOT / "lib" / "hands" / "v1" / "hand" / "pr_description.py"


# ===================================================================
# _parse_positive_env_var — unit tests
# ===================================================================


class TestParsePositiveEnvVar:
    """Direct tests for the ``_parse_positive_env_var`` helper."""

    def test_returns_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_PARSE_VAR", raising=False)
        result = _parse_positive_env_var("TEST_PARSE_VAR", 42, int)
        assert result == 42

    def test_parses_valid_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "100")
        result = _parse_positive_env_var("TEST_PARSE_VAR", 42, int)
        assert result == 100
        assert isinstance(result, int)

    def test_parses_valid_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "3.14")
        result = _parse_positive_env_var("TEST_PARSE_VAR", 1.0, float)
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "  50  ")
        result = _parse_positive_env_var("TEST_PARSE_VAR", 10, int)
        assert result == 50

    def test_non_numeric_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "abc")
        with caplog.at_level(logging.WARNING):
            result = _parse_positive_env_var("TEST_PARSE_VAR", 42, int)
        assert result == 42
        assert "non-numeric" in caplog.text

    def test_zero_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "0")
        with caplog.at_level(logging.WARNING):
            result = _parse_positive_env_var("TEST_PARSE_VAR", 42, int)
        assert result == 42
        assert "non-positive" in caplog.text

    def test_negative_returns_default(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "-5")
        with caplog.at_level(logging.WARNING):
            result = _parse_positive_env_var("TEST_PARSE_VAR", 42, int)
        assert result == 42
        assert "non-positive" in caplog.text

    # TODO: CLEANUP CANDIDATE — stylistic docstring-presence check; better
    # enforced by a linter rule than a runtime test.
    def test_has_docstring(self) -> None:
        assert _parse_positive_env_var.__doc__ is not None
        assert "positive" in _parse_positive_env_var.__doc__.lower()

    def test_preserves_int_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "7")
        result = _parse_positive_env_var("TEST_PARSE_VAR", 10, int)
        assert type(result) is int

    def test_preserves_float_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_PARSE_VAR", "7")
        result = _parse_positive_env_var("TEST_PARSE_VAR", 10.0, float)
        assert type(result) is float


# ===================================================================
# _timeout_seconds / _diff_char_limit — delegation tests
# ===================================================================


class TestTimeoutSecondsDelegation:
    """Verify _timeout_seconds delegates to _parse_positive_env_var."""

    def test_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_TIMEOUT_ENV_VAR, raising=False)
        assert _timeout_seconds() == _DEFAULT_TIMEOUT_SECONDS

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_TIMEOUT_ENV_VAR, "120.5")
        assert _timeout_seconds() == pytest.approx(120.5)

    def test_non_numeric_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_TIMEOUT_ENV_VAR, "not-a-number")
        assert _timeout_seconds() == _DEFAULT_TIMEOUT_SECONDS

    def test_returns_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_TIMEOUT_ENV_VAR, raising=False)
        assert isinstance(_timeout_seconds(), float)


class TestDiffCharLimitDelegation:
    """Verify _diff_char_limit delegates to _parse_positive_env_var."""

    def test_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_DIFF_LIMIT_ENV_VAR, raising=False)
        assert _diff_char_limit() == _DEFAULT_DIFF_CHAR_LIMIT

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DIFF_LIMIT_ENV_VAR, "5000")
        assert _diff_char_limit() == 5000

    def test_non_numeric_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(_DIFF_LIMIT_ENV_VAR, "xyz")
        assert _diff_char_limit() == _DEFAULT_DIFF_CHAR_LIMIT

    def test_returns_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(_DIFF_LIMIT_ENV_VAR, raising=False)
        assert isinstance(_diff_char_limit(), int)


# ===================================================================
# AST source consistency
# ===================================================================


class TestASTNoDuplicateWarnings:
    """Verify the old duplicated warning patterns are gone from source."""

    def test_timeout_seconds_is_one_liner(self) -> None:
        """_timeout_seconds body should be a single return statement."""
        source = _PR_DESCRIPTION_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_timeout_seconds":
                # Filter out docstring (Expr with Constant)
                body = [
                    stmt
                    for stmt in node.body
                    if not (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                    )
                ]
                assert len(body) == 1, (
                    f"_timeout_seconds should be a single-statement delegation, "
                    f"got {len(body)} statements"
                )
                assert isinstance(body[0], ast.Return)
                break
        else:
            pytest.fail("_timeout_seconds not found in source")

    def test_diff_char_limit_is_one_liner(self) -> None:
        """_diff_char_limit body should be a single return statement."""
        source = _PR_DESCRIPTION_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_diff_char_limit":
                body = [
                    stmt
                    for stmt in node.body
                    if not (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                    )
                ]
                assert len(body) == 1, (
                    f"_diff_char_limit should be a single-statement delegation, "
                    f"got {len(body)} statements"
                )
                assert isinstance(body[0], ast.Return)
                break
        else:
            pytest.fail("_diff_char_limit not found in source")

    def test_no_inline_logger_warning_in_timeout_or_diff(self) -> None:
        """Neither _timeout_seconds nor _diff_char_limit should contain
        direct logger.warning calls — those live in the helper now."""
        source = _PR_DESCRIPTION_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in {
                "_timeout_seconds",
                "_diff_char_limit",
            }:
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute) and child.attr == "warning":
                        pytest.fail(f"{node.name} still contains a logger.warning call")
