"""Tests for v220: DRY _pr_status_line helper & CLI validation cleanup.

Validates:
- ``_pr_status_line()`` static method on ``_BasicIterativeHand``
- CLI ``--pr-number`` and ``--max-iterations`` validation via ``require_positive_int``
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest

from helping_hands.cli.main import main
from helping_hands.lib.hands.v1.hand.base import (
    _META_PR_STATUS,
    _META_PR_URL,
    _PR_STATUS_CREATED,
    _PR_STATUS_DISABLED,
    _PR_STATUS_NO_CHANGES,
    _PR_STATUSES_SKIPPED,
)
from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

# ---------------------------------------------------------------------------
# _pr_status_line — basic behaviour
# ---------------------------------------------------------------------------


class TestPrStatusLine:
    """Verify _pr_status_line returns the correct status string."""

    def test_returns_pr_created_when_url_present(self) -> None:
        meta: dict[str, Any] = {_META_PR_URL: "https://github.com/o/r/pull/1"}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == "\nPR created: https://github.com/o/r/pull/1\n"

    def test_returns_pr_status_when_url_absent_and_status_not_skipped(self) -> None:
        meta: dict[str, Any] = {_META_PR_STATUS: _PR_STATUS_CREATED}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == f"\nPR status: {_PR_STATUS_CREATED}\n"

    def test_returns_empty_when_status_is_skipped_disabled(self) -> None:
        meta: dict[str, Any] = {_META_PR_STATUS: _PR_STATUS_DISABLED}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == ""

    def test_returns_empty_when_status_is_skipped_no_changes(self) -> None:
        meta: dict[str, Any] = {_META_PR_STATUS: _PR_STATUS_NO_CHANGES}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == ""

    def test_returns_empty_when_metadata_empty(self) -> None:
        result = _BasicIterativeHand._pr_status_line({})
        assert result == ""

    def test_url_takes_precedence_over_status(self) -> None:
        """When both URL and status are present, URL wins."""
        meta: dict[str, Any] = {
            _META_PR_URL: "https://github.com/o/r/pull/42",
            _META_PR_STATUS: _PR_STATUS_CREATED,
        }
        result = _BasicIterativeHand._pr_status_line(meta)
        assert "PR created:" in result
        assert "PR status:" not in result

    def test_all_skipped_statuses_return_empty(self) -> None:
        """Every member of _PR_STATUSES_SKIPPED produces empty string."""
        for status in _PR_STATUSES_SKIPPED:
            meta: dict[str, Any] = {_META_PR_STATUS: status}
            result = _BasicIterativeHand._pr_status_line(meta)
            assert result == "", f"Expected empty for skipped status {status!r}"

    def test_non_skipped_status_returns_status_line(self) -> None:
        """A non-skipped status (e.g. 'updated') produces a status line."""
        meta: dict[str, Any] = {_META_PR_STATUS: "updated"}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == "\nPR status: updated\n"

    def test_is_static_method(self) -> None:
        assert isinstance(
            inspect.getattr_static(_BasicIterativeHand, "_pr_status_line"),
            staticmethod,
        )

    def test_has_docstring(self) -> None:
        doc = _BasicIterativeHand._pr_status_line.__doc__
        assert doc is not None
        assert "Args:" in doc
        assert "Returns:" in doc


# ---------------------------------------------------------------------------
# Source-level checks: bare key patterns should not appear in stream()
# ---------------------------------------------------------------------------


class TestPrStatusLineSourceConsistency:
    """Verify iterative.py stream methods use _pr_status_line, not inline checks."""

    def test_no_bare_pr_url_check_in_langgraph_stream(self) -> None:
        src_path = Path(inspect.getfile(_BasicIterativeHand))
        tree = ast.parse(src_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "stream":
                # Find the parent class
                for parent in ast.walk(tree):
                    if (
                        isinstance(parent, ast.ClassDef)
                        and node in ast.walk(parent)
                        and parent.name
                        in (
                            "BasicLangGraphHand",
                            "BasicAtomicHand",
                        )
                    ):
                        source = ast.get_source_segment(src_path.read_text(), node)
                        assert source is not None
                        # Should use _pr_status_line, not inline check
                        assert "_pr_status_line" in source
                        assert source.count("_META_PR_URL") == 0, (
                            f"{parent.name}.stream() should use _pr_status_line"
                        )

    def test_iterative_stream_methods_call_pr_status_line(self) -> None:
        """Both stream() methods in iterative.py reference _pr_status_line."""
        src = Path(inspect.getfile(_BasicIterativeHand)).read_text()
        tree = ast.parse(src)
        found = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "stream":
                segment = ast.get_source_segment(src, node)
                if segment and "_pr_status_line" in segment:
                    found += 1
        assert found == 2, (
            f"Expected 2 stream() methods using _pr_status_line, got {found}"
        )


# ---------------------------------------------------------------------------
# CLI validation: --pr-number and --max-iterations
# ---------------------------------------------------------------------------


class TestCliPositiveIntValidation:
    """Verify CLI uses require_positive_int for --pr-number and --max-iterations."""

    def test_pr_number_zero_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--pr-number", "0", "--prompt", "test"])
        captured = capsys.readouterr()
        assert "positive" in captured.err.lower() or "--pr-number" in captured.err

    def test_pr_number_negative_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--pr-number", "-1", "--prompt", "test"])
        captured = capsys.readouterr()
        assert "--pr-number" in captured.err or "positive" in captured.err.lower()

    def test_max_iterations_zero_exits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--max-iterations", "0", "--prompt", "test"])
        captured = capsys.readouterr()
        assert "positive" in captured.err.lower() or "--max-iterations" in captured.err

    def test_max_iterations_negative_exits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--max-iterations", "-5", "--prompt", "test"])
        captured = capsys.readouterr()
        assert "--max-iterations" in captured.err or "positive" in captured.err.lower()

    def test_cli_imports_require_positive_int(self) -> None:
        """Verify cli/main.py imports require_positive_int from validation."""
        import helping_hands.cli.main as cli_mod

        assert hasattr(cli_mod, "require_positive_int")

    def test_main_py_source_uses_require_positive_int(self) -> None:
        """Verify that main.py no longer has inline <= 0 checks for these args."""
        import helping_hands.cli.main as cli_mod

        src = Path(inspect.getfile(cli_mod)).read_text()
        # The old pattern was: `if args.pr_number is not None and args.pr_number <= 0:`
        assert "args.pr_number <= 0" not in src
        assert "args.max_iterations <= 0" not in src
        # The new pattern uses require_positive_int
        assert "require_positive_int" in src
