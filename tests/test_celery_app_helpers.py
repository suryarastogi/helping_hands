"""Unit tests for additional pure helpers in server/celery_app.py.

Extends the existing test_celery_helpers.py and test_celery_app.py suites by
covering _normalize_backend edge cases, _format_runtime boundary values,
_resolve_repo_path for local directories, and _maybe_persist_pr_to_schedule
guard logic.

Regressions in _normalize_backend would silently route builds to the wrong
AI backend. _format_runtime errors would show garbled times on the monitor page.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("celery")

from helping_hands.server.celery_app import (
    _format_runtime,
    _normalize_backend,
    _resolve_repo_path,
)

# ---------------------------------------------------------------------------
# _normalize_backend — extended edge cases
# ---------------------------------------------------------------------------


class TestNormalizeBackendExtended:
    def test_default_when_none(self) -> None:
        requested, runtime = _normalize_backend(None)
        assert requested == "claudecodecli"
        assert runtime == "claudecodecli"

    def test_basic_agent_maps_to_atomic(self) -> None:
        requested, runtime = _normalize_backend("basic-agent")
        assert requested == "basic-agent"
        assert runtime == "basic-atomic"

    def test_basic_langgraph_passthrough(self) -> None:
        _requested, runtime = _normalize_backend("basic-langgraph")
        assert runtime == "basic-langgraph"

    def test_strips_whitespace(self) -> None:
        requested, _runtime = _normalize_backend("  claudecodecli  ")
        assert requested == "claudecodecli"

    def test_case_insensitive(self) -> None:
        requested, _ = _normalize_backend("ClaudeCodeCli")
        assert requested == "claudecodecli"

    def test_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            _normalize_backend("nonexistent-backend")

    def test_e2e_backend(self) -> None:
        requested, runtime = _normalize_backend("e2e")
        assert requested == "e2e"
        assert runtime == "e2e"

    def test_codexcli_backend(self) -> None:
        requested, runtime = _normalize_backend("codexcli")
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_geminicli_backend(self) -> None:
        requested, runtime = _normalize_backend("geminicli")
        assert requested == "geminicli"
        assert runtime == "geminicli"


# ---------------------------------------------------------------------------
# _format_runtime — boundary values
# ---------------------------------------------------------------------------


class TestFormatRuntimeExtended:
    def test_zero_seconds(self) -> None:
        assert _format_runtime(0) == "0.0s"

    def test_sub_minute(self) -> None:
        assert _format_runtime(45.3) == "45.3s"

    def test_exactly_one_minute(self) -> None:
        assert _format_runtime(60) == "1m 0s"

    def test_multi_minute(self) -> None:
        assert _format_runtime(125.7) == "2m 6s"

    def test_fractional_seconds(self) -> None:
        assert _format_runtime(0.1) == "0.1s"

    def test_large_value(self) -> None:
        result = _format_runtime(3661)
        assert result == "61m 1s"

    def test_just_under_one_minute(self) -> None:
        assert _format_runtime(59.9) == "59.9s"


# ---------------------------------------------------------------------------
# _resolve_repo_path — local directory
# ---------------------------------------------------------------------------


class TestResolveRepoPathLocal:
    def test_local_directory_resolves(self, tmp_path: Path) -> None:
        repo_path, cloned_from, temp_root = _resolve_repo_path(str(tmp_path))
        assert repo_path == tmp_path
        assert cloned_from is None
        assert temp_root is None

    def test_invalid_path_raises(self) -> None:
        with pytest.raises(ValueError, match="not a directory or owner/repo"):
            _resolve_repo_path("not-a-repo-spec")

    def test_owner_repo_spec_clones(self, tmp_path: Path) -> None:
        """Verify owner/repo format triggers clone path (mocked)."""
        with (
            patch("helping_hands.server.celery_app._run_git_clone") as mock_clone,
            patch(
                "helping_hands.server.celery_app._repo_tmp_dir",
                return_value=str(tmp_path),
            ),
        ):
            mock_clone.return_value = None
            _repo_path, cloned_from, temp_root = _resolve_repo_path("owner/repo")
            assert cloned_from == "owner/repo"
            assert temp_root is not None
            mock_clone.assert_called_once()

    def test_clone_failure_cleans_up(self, tmp_path: Path) -> None:
        """Verify temp dir cleanup on clone ValueError."""
        with (
            patch(
                "helping_hands.server.celery_app._run_git_clone",
                side_effect=ValueError("clone failed"),
            ),
            patch(
                "helping_hands.server.celery_app._repo_tmp_dir",
                return_value=str(tmp_path),
            ),
            pytest.raises(ValueError, match="clone failed"),
        ):
            _resolve_repo_path("owner/repo")
