"""Tests for v228: DRY _format_error_result, _pr_status_line dict access, skip logging.

Covers:
- ``_format_error_result()`` static method on ``_BasicIterativeHand``
- ``_pr_status_line()`` consistent ``.get()`` usage (no bracket access)
- Debug logging when ``_build_tree_snapshot`` skips invalid paths
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest

from helping_hands.lib.config import Config
from helping_hands.lib.hands.v1.hand.base import (
    _META_PR_STATUS,
    _META_PR_URL,
    HandResponse,
)
from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand
from helping_hands.lib.repo import RepoIndex


class _StubIterativeHand(_BasicIterativeHand):
    """Concrete stub so we can instantiate _BasicIterativeHand for testing."""

    def run(self, prompt: str) -> HandResponse:
        return HandResponse(message=prompt)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield prompt


# ---------------------------------------------------------------------------
# _format_error_result
# ---------------------------------------------------------------------------


class TestFormatErrorResult:
    """Verify _format_error_result produces correct error blocks."""

    def test_read_tag(self) -> None:
        result = _BasicIterativeHand._format_error_result(
            "READ", "src/main.py", "file not found"
        )
        assert result == "@@READ_RESULT: src/main.py\nERROR: file not found"

    def test_tool_tag(self) -> None:
        result = _BasicIterativeHand._format_error_result(
            "TOOL", "bash", "command failed"
        )
        assert result == "@@TOOL_RESULT: bash\nERROR: command failed"

    def test_custom_tag(self) -> None:
        result = _BasicIterativeHand._format_error_result(
            "CUSTOM", "op", "something broke"
        )
        assert result == "@@CUSTOM_RESULT: op\nERROR: something broke"

    def test_empty_message(self) -> None:
        result = _BasicIterativeHand._format_error_result("READ", "f.py", "")
        assert result == "@@READ_RESULT: f.py\nERROR: "

    def test_multiline_message(self) -> None:
        result = _BasicIterativeHand._format_error_result(
            "TOOL", "bash", "line1\nline2"
        )
        assert result == "@@TOOL_RESULT: bash\nERROR: line1\nline2"

    def test_is_static_method(self) -> None:
        attr = inspect.getattr_static(_BasicIterativeHand, "_format_error_result")
        assert isinstance(attr, staticmethod)

    def test_has_docstring(self) -> None:
        doc = _BasicIterativeHand._format_error_result.__doc__
        assert doc is not None and "error" in doc.lower()

    def test_used_in_execute_read_requests(self) -> None:
        """Verify _execute_read_requests uses _format_error_result, not inline."""
        source = inspect.getsource(_BasicIterativeHand._execute_read_requests)
        assert "_format_error_result" in source
        # Should not have raw f-string error formatting
        assert '@@READ_RESULT: {rel_path}\\nERROR' not in source

    def test_used_in_execute_tool_requests(self) -> None:
        """Verify _execute_tool_requests uses _format_error_result, not inline."""
        source = inspect.getsource(_BasicIterativeHand._execute_tool_requests)
        assert "_format_error_result" in source
        assert '@@TOOL_RESULT: {tool_name}\\nERROR' not in source


# ---------------------------------------------------------------------------
# _pr_status_line — consistent .get() access
# ---------------------------------------------------------------------------


class TestPrStatusLineConsistentAccess:
    """Verify _pr_status_line uses .get() consistently, not bracket access."""

    def test_source_uses_get_not_bracket(self) -> None:
        """The method should not use pr_metadata[_META_PR_URL] bracket access."""
        source = inspect.getsource(_BasicIterativeHand._pr_status_line)
        assert "pr_metadata[_META_PR_URL]" not in source, (
            "_pr_status_line should use .get() value, not bracket access"
        )

    def test_pr_url_returned_correctly(self) -> None:
        """Ensure PR URL is still returned correctly with .get() approach."""
        meta = {_META_PR_URL: "https://github.com/org/repo/pull/42"}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert result == "\nPR created: https://github.com/org/repo/pull/42\n"

    def test_pr_url_empty_string(self) -> None:
        """Empty URL should not produce a PR created line."""
        meta = {_META_PR_URL: ""}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert "PR created" not in result

    def test_pr_url_none(self) -> None:
        """None URL should not produce a PR created line."""
        meta = {_META_PR_URL: None}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert "PR created" not in result

    def test_missing_pr_url_key(self) -> None:
        """Missing key should not raise KeyError."""
        meta = {_META_PR_STATUS: "merged"}
        result = _BasicIterativeHand._pr_status_line(meta)
        assert "PR status: merged" in result


# ---------------------------------------------------------------------------
# _build_tree_snapshot — debug logging for skipped paths
# ---------------------------------------------------------------------------


def _make_hand(
    tmp_path: Path, files: dict[str, str] | None = None
) -> _StubIterativeHand:
    """Create a _StubIterativeHand backed by a real tmp_path repo."""
    if files:
        for rel_path, content in files.items():
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
    repo_index = RepoIndex.from_path(tmp_path)
    config = Config(repo=str(tmp_path), model="test-model")
    with patch(
        "helping_hands.lib.meta.tools.registry.build_tool_runner_map",
        return_value={},
    ):
        hand = _StubIterativeHand(config, repo_index)
    return hand


class TestBuildTreeSnapshotLogging:
    """Verify _build_tree_snapshot logs skipped paths at DEBUG level."""

    def test_logs_invalid_path(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        """When normalize_relative_path raises, a debug log is emitted."""
        hand = _make_hand(tmp_path, {"good.py": ""})
        # Inject an invalid (empty) path into the repo index files
        hand.repo_index.files.append("   ")

        with caplog.at_level(logging.DEBUG):
            hand._build_tree_snapshot()

        assert any("skipping invalid path" in r.message for r in caplog.records), (
            "Expected debug log about skipping invalid path"
        )

    def test_valid_paths_no_skip_log(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ):
        """Valid paths should not produce skip logs."""
        hand = _make_hand(tmp_path, {"src/main.py": "", "README.md": ""})

        with caplog.at_level(logging.DEBUG):
            hand._build_tree_snapshot()

        skip_logs = [r for r in caplog.records if "skipping invalid path" in r.message]
        assert len(skip_logs) == 0

    def test_source_has_logger_debug(self) -> None:
        """The method source should contain a logger.debug call for skipped paths."""
        source = inspect.getsource(_BasicIterativeHand._build_tree_snapshot)
        assert "logger.debug" in source
        assert "skipping invalid path" in source
