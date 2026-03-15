"""Tests for v212 — run_git_clone() helper and DEFAULT_CLONE_DEPTH constant."""

from __future__ import annotations

from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest


class TestDefaultCloneDepth:
    """Tests for the DEFAULT_CLONE_DEPTH constant."""

    def test_value_is_one(self) -> None:
        from helping_hands.lib.github_url import DEFAULT_CLONE_DEPTH

        assert DEFAULT_CLONE_DEPTH == 1

    def test_exported_in_all(self) -> None:
        from helping_hands.lib.github_url import __all__

        assert "DEFAULT_CLONE_DEPTH" in __all__

    def test_run_git_clone_exported_in_all(self) -> None:
        from helping_hands.lib.github_url import __all__

        assert "run_git_clone" in __all__


class TestUnknownCloneError:
    """Tests for the _UNKNOWN_CLONE_ERROR sentinel."""

    def test_value(self) -> None:
        from helping_hands.lib.github_url import _UNKNOWN_CLONE_ERROR

        assert _UNKNOWN_CLONE_ERROR == "unknown git clone error"


class TestRunGitClone:
    """Tests for the run_git_clone() helper function."""

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)
        dest = tmp_path / "repo"

        run_git_clone("https://github.com/owner/repo.git", dest)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:4] == ["git", "clone", "--depth", "1"]
        assert cmd[-2] == "https://github.com/owner/repo.git"
        assert cmd[-1] == str(dest)

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_custom_depth(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)
        dest = tmp_path / "repo"

        run_git_clone("https://example.com/r.git", dest, depth=5)

        cmd = mock_run.call_args[0][0]
        assert "--depth" in cmd
        idx = cmd.index("--depth")
        assert cmd[idx + 1] == "5"

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_extra_args(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)
        dest = tmp_path / "repo"

        run_git_clone(
            "https://example.com/r.git",
            dest,
            extra_args=["--no-single-branch"],
        )

        cmd = mock_run.call_args[0][0]
        assert "--no-single-branch" in cmd
        # extra_args should appear before the URL
        nsi_idx = cmd.index("--no-single-branch")
        url_idx = cmd.index("https://example.com/r.git")
        assert nsi_idx < url_idx

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_uses_noninteractive_env(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)

        run_git_clone("https://example.com/r.git", tmp_path / "repo")

        env = mock_run.call_args[1]["env"]
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "never"

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_uses_capture_output_and_text(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)

        run_git_clone("https://example.com/r.git", tmp_path / "repo")

        kwargs = mock_run.call_args[1]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_timeout_raises_value_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.side_effect = TimeoutExpired("git", 120)

        with pytest.raises(ValueError, match="timed out"):
            run_git_clone("https://example.com/r.git", tmp_path / "repo")

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_timeout_with_custom_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.side_effect = TimeoutExpired("git", 30)

        with pytest.raises(ValueError, match="timed out after 30s"):
            run_git_clone("https://example.com/r.git", tmp_path / "repo", timeout=30)

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_nonzero_exit_raises_value_error(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(
            returncode=128, stderr="fatal: repository not found"
        )

        with pytest.raises(ValueError, match=r"clone failed.*repository not found"):
            run_git_clone("https://example.com/r.git", tmp_path / "repo")

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_nonzero_exit_empty_stderr_uses_fallback(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=1, stderr="")

        with pytest.raises(ValueError, match="unknown git clone error"):
            run_git_clone("https://example.com/r.git", tmp_path / "repo")

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_nonzero_exit_redacts_credentials(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import GITHUB_TOKEN_USER, run_git_clone

        mock_run.return_value = MagicMock(
            returncode=128,
            stderr=f"fatal: https://{GITHUB_TOKEN_USER}:ghp_secret@github.com/o/r.git not found",
        )

        with pytest.raises(ValueError, match=r"\*\*\*") as exc_info:
            run_git_clone("https://example.com/r.git", tmp_path / "repo")
        assert "ghp_secret" not in str(exc_info.value)

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_default_timeout_uses_git_clone_timeout(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import GIT_CLONE_TIMEOUT_S, run_git_clone

        mock_run.return_value = MagicMock(returncode=0)

        run_git_clone("https://example.com/r.git", tmp_path / "repo")

        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == GIT_CLONE_TIMEOUT_S

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_custom_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)

        run_git_clone("https://example.com/r.git", tmp_path / "repo", timeout=60)

        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 60

    @patch("helping_hands.lib.github_url.subprocess.run")
    def test_no_extra_args_omits_them(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.github_url import run_git_clone

        mock_run.return_value = MagicMock(returncode=0)

        run_git_clone("https://example.com/r.git", tmp_path / "repo")

        cmd = mock_run.call_args[0][0]
        assert "--no-single-branch" not in cmd


class TestCliMainNoDuplicateCloneCode:
    """Verify cli/main.py no longer has inline subprocess clone patterns."""

    def test_no_subprocess_import(self) -> None:
        import ast
        from pathlib import Path

        src = Path("src/helping_hands/cli/main.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "subprocess", (
                        "cli/main.py should not import subprocess"
                    )

    def test_no_timeout_expired_import(self) -> None:
        src = Path("src/helping_hands/cli/main.py").read_text()
        assert "TimeoutExpired" not in src

    def test_no_local_default_clone_depth(self) -> None:
        src = Path("src/helping_hands/cli/main.py").read_text()
        assert "_DEFAULT_CLONE_DEPTH = " not in src

    def test_no_github_clone_url_wrapper(self) -> None:
        src = Path("src/helping_hands/cli/main.py").read_text()
        assert "def _github_clone_url" not in src

    def test_imports_run_git_clone(self) -> None:
        src = Path("src/helping_hands/cli/main.py").read_text()
        assert "run_git_clone" in src


class TestCeleryAppNoDuplicateCloneCode:
    """Verify celery_app.py no longer has inline subprocess clone patterns."""

    def test_no_timeout_expired_import(self) -> None:
        src = Path("src/helping_hands/server/celery_app.py").read_text()
        assert "TimeoutExpired" not in src

    def test_no_github_clone_url_wrapper(self) -> None:
        src = Path("src/helping_hands/server/celery_app.py").read_text()
        assert "def _github_clone_url" not in src

    def test_no_git_noninteractive_env_import(self) -> None:
        src = Path("src/helping_hands/server/celery_app.py").read_text()
        assert "noninteractive_env" not in src

    def test_no_git_clone_timeout_import(self) -> None:
        src = Path("src/helping_hands/server/celery_app.py").read_text()
        assert "GIT_CLONE_TIMEOUT_S" not in src

    def test_imports_run_git_clone(self) -> None:
        src = Path("src/helping_hands/server/celery_app.py").read_text()
        assert "run_git_clone" in src
