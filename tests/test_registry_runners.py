"""Tests for registry runner wrappers (payload validation + mocked dispatch)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools.registry import (
    _run_bash_script,
    _run_python_code,
    _run_python_script,
    _run_web_browse,
    _run_web_search,
)

# ---------------------------------------------------------------------------
# _run_python_code
# ---------------------------------------------------------------------------


class TestRunPythonCode:
    def test_rejects_missing_code(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_code(tmp_path, {})

    def test_rejects_empty_code(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_code(tmp_path, {"code": "   "})

    def test_rejects_non_string_code(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_code(tmp_path, {"code": 42})

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_python_code")
    def test_happy_path_defaults(self, mock_run: MagicMock, tmp_path: Path) -> None:
        sentinel = MagicMock()
        mock_run.return_value = sentinel

        result = _run_python_code(tmp_path, {"code": "print(1)"})

        assert result is sentinel
        mock_run.assert_called_once_with(
            tmp_path,
            code="print(1)",
            python_version="3.13",
            args=[],
            timeout_s=60,
            cwd=None,
        )

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_python_code")
    def test_custom_params(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock()

        _run_python_code(
            tmp_path,
            {
                "code": "x=1",
                "python_version": "3.12",
                "args": ["--flag"],
                "timeout_s": 30,
                "cwd": "subdir",
            },
        )

        mock_run.assert_called_once_with(
            tmp_path,
            code="x=1",
            python_version="3.12",
            args=["--flag"],
            timeout_s=30,
            cwd="subdir",
        )


# ---------------------------------------------------------------------------
# _run_python_script
# ---------------------------------------------------------------------------


class TestRunPythonScript:
    def test_rejects_missing_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_script(tmp_path, {})

    def test_rejects_empty_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_script(tmp_path, {"script_path": "  "})

    def test_rejects_non_string_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_python_script(tmp_path, {"script_path": 123})

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_python_script")
    def test_happy_path_defaults(self, mock_run: MagicMock, tmp_path: Path) -> None:
        sentinel = MagicMock()
        mock_run.return_value = sentinel

        result = _run_python_script(tmp_path, {"script_path": "run.py"})

        assert result is sentinel
        mock_run.assert_called_once_with(
            tmp_path,
            script_path="run.py",
            python_version="3.13",
            args=[],
            timeout_s=60,
            cwd=None,
        )


# ---------------------------------------------------------------------------
# _run_bash_script
# ---------------------------------------------------------------------------


class TestRunBashScript:
    def test_rejects_non_string_script_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="script_path must be a string"):
            _run_bash_script(tmp_path, {"script_path": 42})

    def test_rejects_non_string_inline_script(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="inline_script must be a string"):
            _run_bash_script(tmp_path, {"inline_script": 99})

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_bash_script")
    def test_happy_path_script_path(self, mock_run: MagicMock, tmp_path: Path) -> None:
        sentinel = MagicMock()
        mock_run.return_value = sentinel

        result = _run_bash_script(tmp_path, {"script_path": "run.sh"})

        assert result is sentinel
        mock_run.assert_called_once_with(
            tmp_path,
            script_path="run.sh",
            inline_script=None,
            args=[],
            timeout_s=60,
            cwd=None,
        )

    @patch("helping_hands.lib.meta.tools.registry.command_tools.run_bash_script")
    def test_happy_path_inline_script(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        mock_run.return_value = MagicMock()

        _run_bash_script(tmp_path, {"inline_script": "echo hi"})

        mock_run.assert_called_once_with(
            tmp_path,
            script_path=None,
            inline_script="echo hi",
            args=[],
            timeout_s=60,
            cwd=None,
        )


# ---------------------------------------------------------------------------
# _run_web_search
# ---------------------------------------------------------------------------


class TestRunWebSearch:
    def test_rejects_missing_query(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_search(tmp_path, {})

    def test_rejects_empty_query(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_search(tmp_path, {"query": "   "})

    def test_rejects_non_string_query(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_search(tmp_path, {"query": 42})

    @patch("helping_hands.lib.meta.tools.registry.web_tools.search_web")
    def test_happy_path_defaults(self, mock_search: MagicMock, tmp_path: Path) -> None:
        sentinel = MagicMock()
        mock_search.return_value = sentinel

        result = _run_web_search(tmp_path, {"query": "python docs"})

        assert result is sentinel
        mock_search.assert_called_once_with(
            "python docs",
            max_results=5,
            timeout_s=20,
        )

    @patch("helping_hands.lib.meta.tools.registry.web_tools.search_web")
    def test_custom_params(self, mock_search: MagicMock, tmp_path: Path) -> None:
        mock_search.return_value = MagicMock()

        _run_web_search(tmp_path, {"query": "test", "max_results": 10, "timeout_s": 30})

        mock_search.assert_called_once_with("test", max_results=10, timeout_s=30)


# ---------------------------------------------------------------------------
# _run_web_browse
# ---------------------------------------------------------------------------


class TestRunWebBrowse:
    def test_rejects_missing_url(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_browse(tmp_path, {})

    def test_rejects_empty_url(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_browse(tmp_path, {"url": "  "})

    def test_rejects_non_string_url(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            _run_web_browse(tmp_path, {"url": 42})

    @patch("helping_hands.lib.meta.tools.registry.web_tools.browse_url")
    def test_happy_path_defaults(self, mock_browse: MagicMock, tmp_path: Path) -> None:
        sentinel = MagicMock()
        mock_browse.return_value = sentinel

        result = _run_web_browse(tmp_path, {"url": "https://example.com"})

        assert result is sentinel
        mock_browse.assert_called_once_with(
            "https://example.com",
            max_chars=12000,
            timeout_s=20,
        )

    @patch("helping_hands.lib.meta.tools.registry.web_tools.browse_url")
    def test_custom_params(self, mock_browse: MagicMock, tmp_path: Path) -> None:
        mock_browse.return_value = MagicMock()

        _run_web_browse(
            tmp_path, {"url": "https://ex.com", "max_chars": 500, "timeout_s": 10}
        )

        mock_browse.assert_called_once_with(
            "https://ex.com", max_chars=500, timeout_s=10
        )
