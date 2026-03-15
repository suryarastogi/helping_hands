"""Tests for v203 — DRY clone error fallback and reference repo prefix.

Validates:
- ``UNKNOWN_CLONE_ERROR`` constant value and type
- ``ref_repo_tmp_prefix()`` output format
- Cross-module import identity (cli/main.py and celery_app.py use shared sources)
- Usage-site output verification
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# UNKNOWN_CLONE_ERROR — constant tests
# ---------------------------------------------------------------------------


class TestUnknownCloneError:
    """Verify the UNKNOWN_CLONE_ERROR constant."""

    def test_value(self) -> None:
        from helping_hands.lib.github_url import UNKNOWN_CLONE_ERROR

        assert UNKNOWN_CLONE_ERROR == "unknown git clone error"

    def test_type(self) -> None:
        from helping_hands.lib.github_url import UNKNOWN_CLONE_ERROR

        assert isinstance(UNKNOWN_CLONE_ERROR, str)

    def test_in_all_exports(self) -> None:
        from helping_hands.lib import github_url

        assert "UNKNOWN_CLONE_ERROR" in github_url.__all__


# ---------------------------------------------------------------------------
# ref_repo_tmp_prefix — helper tests
# ---------------------------------------------------------------------------


class TestRefRepoTmpPrefix:
    """Verify the ref_repo_tmp_prefix() helper."""

    def test_basic_format(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        result = ref_repo_tmp_prefix("owner/repo")
        assert result == "helping_hands_ref_owner_repo_"

    def test_no_slash_in_output(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        result = ref_repo_tmp_prefix("org/project")
        assert "/" not in result

    def test_starts_with_prefix(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        result = ref_repo_tmp_prefix("foo/bar")
        assert result.startswith("helping_hands_ref_")

    def test_ends_with_underscore(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        result = ref_repo_tmp_prefix("foo/bar")
        assert result.endswith("_")

    def test_in_all_exports(self) -> None:
        from helping_hands.lib import github_url

        assert "ref_repo_tmp_prefix" in github_url.__all__

    def test_complex_spec(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        result = ref_repo_tmp_prefix("my-org/my.repo-name")
        assert result == "helping_hands_ref_my-org_my.repo-name_"


# ---------------------------------------------------------------------------
# __all__ — updated exports
# ---------------------------------------------------------------------------


class TestGitHubUrlAllExports:
    """Verify __all__ includes new exports."""

    def test_all_contains_new_exports(self) -> None:
        from helping_hands.lib import github_url

        expected = {
            "GITHUB_HOSTNAME",
            "GITHUB_TOKEN_USER",
            "GIT_CLONE_TIMEOUT_S",
            "UNKNOWN_CLONE_ERROR",
            "build_clone_url",
            "noninteractive_env",
            "redact_credentials",
            "ref_repo_tmp_prefix",
            "validate_repo_spec",
        }
        assert set(github_url.__all__) == expected


# ---------------------------------------------------------------------------
# Cross-module import identity
# ---------------------------------------------------------------------------


def _celery_available() -> bool:
    try:
        import celery  # noqa: F401

        return True
    except ImportError:
        return False


class TestCrossModuleImportIdentity:
    """Verify consumer modules import from the shared source."""

    def test_cli_main_unknown_clone_error_identity(self) -> None:
        from helping_hands.cli import main as _cli_main
        from helping_hands.lib.github_url import UNKNOWN_CLONE_ERROR

        assert _cli_main._UNKNOWN_CLONE_ERROR is UNKNOWN_CLONE_ERROR

    def test_cli_main_ref_repo_tmp_prefix_identity(self) -> None:
        from helping_hands.cli import main as _cli_main
        from helping_hands.lib.github_url import ref_repo_tmp_prefix

        assert _cli_main._ref_repo_tmp_prefix is ref_repo_tmp_prefix

    @pytest.mark.skipif(
        not _celery_available(),
        reason="celery not installed",
    )
    def test_celery_unknown_clone_error_identity(self) -> None:
        from helping_hands.lib.github_url import UNKNOWN_CLONE_ERROR
        from helping_hands.server import celery_app as _celery

        assert _celery._UNKNOWN_CLONE_ERROR is UNKNOWN_CLONE_ERROR

    @pytest.mark.skipif(
        not _celery_available(),
        reason="celery not installed",
    )
    def test_celery_ref_repo_tmp_prefix_identity(self) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix
        from helping_hands.server import celery_app as _celery

        assert _celery._ref_repo_tmp_prefix is ref_repo_tmp_prefix


# ---------------------------------------------------------------------------
# Usage-site output verification — cli/main.py clone error uses constant
# ---------------------------------------------------------------------------


class TestCliCloneErrorUsesConstant:
    """Verify cli/main.py clone error fallback uses the shared constant."""

    @patch("helping_hands.cli.main._git_noninteractive_env", return_value={})
    @patch("helping_hands.cli.main._build_clone_url", return_value="https://fake.git")
    @patch("helping_hands.cli.main.subprocess.run")
    def test_resolve_repo_path_uses_constant_on_empty_stderr(
        self,
        mock_run: MagicMock,
        _mock_url: MagicMock,
        _mock_env: MagicMock,
    ) -> None:
        from helping_hands.lib.github_url import UNKNOWN_CLONE_ERROR

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        from helping_hands.cli.main import _resolve_repo_path

        with pytest.raises(ValueError, match=UNKNOWN_CLONE_ERROR):
            _resolve_repo_path("owner/repo")


# ---------------------------------------------------------------------------
# Usage-site output verification — ref_repo_tmp_prefix in mkdtemp calls
# ---------------------------------------------------------------------------


class TestRefPrefixUsedInMkdtemp:
    """Verify ref_repo_tmp_prefix is used for reference repo temp dirs."""

    @patch("helping_hands.cli.main._repo_tmp_dir", return_value=None)
    @patch("helping_hands.cli.main._git_noninteractive_env", return_value={})
    @patch("helping_hands.cli.main._build_clone_url", return_value="https://fake.git")
    @patch("helping_hands.cli.main.subprocess.run")
    @patch("helping_hands.cli.main.mkdtemp")
    def test_cli_clone_reference_repos_uses_prefix(
        self,
        mock_mkdtemp: MagicMock,
        mock_run: MagicMock,
        _mock_url: MagicMock,
        _mock_env: MagicMock,
        _mock_tmp: MagicMock,
        tmp_path: Path,
    ) -> None:
        from helping_hands.lib.github_url import ref_repo_tmp_prefix
        from helping_hands.lib.repo import RepoIndex

        dest = tmp_path / "ref"
        dest.mkdir()
        mock_mkdtemp.return_value = str(dest)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        repo_index = RepoIndex(
            root=tmp_path,
            reference_repos=[],
        )

        from helping_hands.cli.main import _clone_reference_repos

        _clone_reference_repos(("org/lib",), repo_index)

        expected_prefix = ref_repo_tmp_prefix("org/lib")
        mock_mkdtemp.assert_called_once()
        call_kwargs = mock_mkdtemp.call_args
        assert call_kwargs[1].get("prefix") or call_kwargs[0][0] == expected_prefix
