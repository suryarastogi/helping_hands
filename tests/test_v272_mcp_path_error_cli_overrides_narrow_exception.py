"""Tests for v272 — MCP _reraise_path_error, CLI _build_config_overrides, narrowed exception."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import (
    _build_config_overrides,
    main,
)
from helping_hands.server.mcp_server import _reraise_path_error

# Suppress coroutine warnings from coverage.py tracer holding frame references.
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


# ---------------------------------------------------------------------------
# _reraise_path_error
# ---------------------------------------------------------------------------


class TestReraisePathError:
    """Tests for the ``_reraise_path_error`` MCP helper."""

    def test_raises_same_type_as_input(self) -> None:
        with pytest.raises(ValueError, match=r"Invalid file path: foo\.txt"):
            _reraise_path_error(ValueError("original"), "Invalid file path", "foo.txt")

    def test_chains_original_exception(self) -> None:
        original = FileNotFoundError("original")
        with pytest.raises(FileNotFoundError) as exc_info:
            _reraise_path_error(original, "File not found", "bar.py")
        assert exc_info.value.__cause__ is original

    def test_file_not_found_error(self) -> None:
        with pytest.raises(FileNotFoundError, match=r"File not found: x\.md"):
            _reraise_path_error(FileNotFoundError("inner"), "File not found", "x.md")

    def test_is_a_directory_error(self) -> None:
        with pytest.raises(IsADirectoryError, match=r"Path is a directory: src/"):
            _reraise_path_error(
                IsADirectoryError("inner"), "Path is a directory", "src/"
            )

    def test_unicode_error(self) -> None:
        # UnicodeError requires specific args for construction but our helper
        # uses type(exc)(msg) which works for the simple message form.
        original = UnicodeError("not utf-8")
        with pytest.raises(UnicodeError, match=r"File is not UTF-8 text: img\.bin"):
            _reraise_path_error(original, "File is not UTF-8 text", "img.bin")

    def test_value_error_for_invalid_dir(self) -> None:
        with pytest.raises(ValueError, match=r"Invalid directory path: \.\./escape"):
            _reraise_path_error(
                ValueError("traversal"), "Invalid directory path", "../escape"
            )

    def test_os_error(self) -> None:
        with pytest.raises(OSError, match=r"Disk full: big\.dat"):
            _reraise_path_error(OSError("disk"), "Disk full", "big.dat")

    def test_runtime_error(self) -> None:
        with pytest.raises(RuntimeError, match=r"Unexpected: odd\.txt"):
            _reraise_path_error(RuntimeError("boom"), "Unexpected", "odd.txt")

    def test_message_format(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _reraise_path_error(ValueError("x"), "Label", "path/to/file")
        assert str(exc_info.value) == "Label: path/to/file"


# ---------------------------------------------------------------------------
# _build_config_overrides
# ---------------------------------------------------------------------------


class TestBuildConfigOverrides:
    """Tests for the ``_build_config_overrides`` CLI helper."""

    @staticmethod
    def _make_namespace(**kwargs: Any) -> argparse.Namespace:
        defaults = {
            "repo": "/tmp/repo",
            "model": "gpt-5.2",
            "verbose": True,
            "enable_execution": False,
            "enable_web": True,
            "use_native_cli_auth": False,
            "github_token": "gh_abc",
            "reference_repos": ("owner/ref",),
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_returns_dict_with_all_fields(self) -> None:
        ns = self._make_namespace()
        result = _build_config_overrides(
            ns,
            repo="/override/path",
            selected_tools=frozenset({"execution"}),
            selected_skills=frozenset({"uv"}),
        )
        assert result["repo"] == "/override/path"
        assert result["model"] == "gpt-5.2"
        assert result["verbose"] is True
        assert result["enable_execution"] is False
        assert result["enable_web"] is True
        assert result["use_native_cli_auth"] is False
        assert result["enabled_tools"] == frozenset({"execution"})
        assert result["enabled_skills"] == frozenset({"uv"})
        assert result["github_token"] == "gh_abc"
        assert result["reference_repos"] == ("owner/ref",)

    def test_repo_override_differs_from_args_repo(self) -> None:
        ns = self._make_namespace(repo="original/repo")
        result = _build_config_overrides(
            ns,
            repo="/different/path",
            selected_tools=frozenset(),
            selected_skills=frozenset(),
        )
        assert result["repo"] == "/different/path"

    def test_none_values_preserved(self) -> None:
        ns = self._make_namespace(model=None, github_token=None, verbose=None)
        result = _build_config_overrides(
            ns,
            repo="/tmp",
            selected_tools=frozenset(),
            selected_skills=frozenset(),
        )
        assert result["model"] is None
        assert result["github_token"] is None
        assert result["verbose"] is None

    def test_empty_tools_and_skills(self) -> None:
        ns = self._make_namespace()
        result = _build_config_overrides(
            ns,
            repo="/tmp",
            selected_tools=frozenset(),
            selected_skills=frozenset(),
        )
        assert result["enabled_tools"] == frozenset()
        assert result["enabled_skills"] == frozenset()

    def test_multiple_tools_and_skills(self) -> None:
        ns = self._make_namespace()
        result = _build_config_overrides(
            ns,
            repo="/tmp",
            selected_tools=frozenset({"execution", "web"}),
            selected_skills=frozenset({"uv", "ruff"}),
        )
        assert result["enabled_tools"] == frozenset({"execution", "web"})
        assert result["enabled_skills"] == frozenset({"uv", "ruff"})


# ---------------------------------------------------------------------------
# Narrowed exception handling in main()
# ---------------------------------------------------------------------------


def _close_coroutine(coro: object) -> None:
    """Close an unawaited coroutine."""
    if hasattr(coro, "close"):
        coro.close()


class TestNarrowedException:
    """Tests for narrowed (RuntimeError, ValueError, OSError) in main()."""

    def test_runtime_error_model_not_found_exits(self, tmp_path: Path) -> None:
        """RuntimeError with model_not_found marker triggers _error_exit."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
            patch("helping_hands.cli.main._error_exit") as mock_exit,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = RuntimeError("model_not_found for foo")
            mock_exit.side_effect = SystemExit(1)

            with pytest.raises(SystemExit):
                main([str(tmp_path), "--backend", "codexcli", "--prompt", "test"])
            mock_exit.assert_called_once()
            assert "not available" in mock_exit.call_args[0][0]

    def test_value_error_cli_backend_exits(self, tmp_path: Path) -> None:
        """ValueError from CLI backend triggers _error_exit."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
            patch("helping_hands.cli.main._error_exit") as mock_exit,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = ValueError("some error")
            mock_exit.side_effect = SystemExit(1)

            with pytest.raises(SystemExit):
                main([str(tmp_path), "--backend", "codexcli", "--prompt", "test"])
            mock_exit.assert_called_once()
            assert "some error" in mock_exit.call_args[0][0]

    def test_os_error_cli_backend_exits(self, tmp_path: Path) -> None:
        """OSError from CLI backend triggers _error_exit."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
            patch("helping_hands.cli.main._error_exit") as mock_exit,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = OSError("disk full")
            mock_exit.side_effect = SystemExit(1)

            with pytest.raises(SystemExit):
                main([str(tmp_path), "--backend", "codexcli", "--prompt", "test"])
            mock_exit.assert_called_once()
            assert "disk full" in mock_exit.call_args[0][0]

    def test_runtime_error_non_cli_backend_reraises(self, tmp_path: Path) -> None:
        """RuntimeError from non-CLI backend re-raises."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = RuntimeError("some runtime error")

            with pytest.raises(RuntimeError, match="some runtime error"):
                main(
                    [
                        str(tmp_path),
                        "--backend",
                        "basic-langgraph",
                        "--prompt",
                        "test",
                    ]
                )

    def test_type_error_not_caught(self, tmp_path: Path) -> None:
        """TypeError (not in narrowed set) propagates unhandled."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = TypeError("unexpected type")

            with pytest.raises(TypeError, match="unexpected type"):
                main([str(tmp_path), "--backend", "codexcli", "--prompt", "test"])

    def test_does_not_exist_marker_exits(self, tmp_path: Path) -> None:
        """'does not exist' marker also triggers model-not-found exit."""
        with (
            patch("helping_hands.cli.main.create_hand") as mock_create,
            patch("helping_hands.cli.main.asyncio.run") as mock_run,
            patch("helping_hands.cli.main._error_exit") as mock_exit,
        ):
            mock_hand = MagicMock()
            mock_create.return_value = mock_hand
            mock_run.side_effect = ValueError("model does not exist")
            mock_exit.side_effect = SystemExit(1)

            with pytest.raises(SystemExit):
                main([str(tmp_path), "--backend", "codexcli", "--prompt", "test"])
            assert "not available" in mock_exit.call_args[0][0]
