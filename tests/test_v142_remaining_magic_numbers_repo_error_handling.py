"""Tests for v142: remaining magic number extraction and repo.py PermissionError handling."""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# 1. server/app.py preview truncation constants
# ---------------------------------------------------------------------------


class TestServerAppPreviewConstants:
    """Verify _HTTP_ERROR_BODY_PREVIEW_LENGTH and _USAGE_DATA_PREVIEW_LENGTH."""

    def test_http_error_body_preview_length_value(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _HTTP_ERROR_BODY_PREVIEW_LENGTH

        assert _HTTP_ERROR_BODY_PREVIEW_LENGTH == 200

    def test_http_error_body_preview_length_type(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _HTTP_ERROR_BODY_PREVIEW_LENGTH

        assert isinstance(_HTTP_ERROR_BODY_PREVIEW_LENGTH, int)

    def test_http_error_body_preview_length_positive(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _HTTP_ERROR_BODY_PREVIEW_LENGTH

        assert _HTTP_ERROR_BODY_PREVIEW_LENGTH > 0

    def test_usage_data_preview_length_value(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _USAGE_DATA_PREVIEW_LENGTH

        assert _USAGE_DATA_PREVIEW_LENGTH == 300

    def test_usage_data_preview_length_type(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _USAGE_DATA_PREVIEW_LENGTH

        assert isinstance(_USAGE_DATA_PREVIEW_LENGTH, int)

    def test_usage_data_preview_length_positive(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _USAGE_DATA_PREVIEW_LENGTH

        assert _USAGE_DATA_PREVIEW_LENGTH > 0

    def test_http_error_body_used_in_fetch_claude_usage(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _fetch_claude_usage

        source = inspect.getsource(_fetch_claude_usage)
        assert "_HTTP_ERROR_BODY_PREVIEW_LENGTH" in source

    def test_usage_data_preview_used_in_fetch_claude_usage(self) -> None:
        pytest.importorskip("fastapi")
        from helping_hands.server.app import _fetch_claude_usage

        source = inspect.getsource(_fetch_claude_usage)
        assert "_USAGE_DATA_PREVIEW_LENGTH" in source


# ---------------------------------------------------------------------------
# 2. cli/base.py hook/display constants
# ---------------------------------------------------------------------------


class TestCLIBaseHookDisplayConstants:
    """Verify _HOOK_ERROR_TRUNCATION_LIMIT and _GIT_REF_DISPLAY_LENGTH."""

    def test_hook_error_truncation_limit_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _HOOK_ERROR_TRUNCATION_LIMIT,
        )

        assert _HOOK_ERROR_TRUNCATION_LIMIT == 3000

    def test_hook_error_truncation_limit_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _HOOK_ERROR_TRUNCATION_LIMIT,
        )

        assert isinstance(_HOOK_ERROR_TRUNCATION_LIMIT, int)

    def test_hook_error_truncation_limit_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _HOOK_ERROR_TRUNCATION_LIMIT,
        )

        assert _HOOK_ERROR_TRUNCATION_LIMIT > 0

    def test_hook_error_used_in_build_hook_fix_prompt(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        source = inspect.getsource(_TwoPhaseCLIHand._build_hook_fix_prompt)
        assert "_HOOK_ERROR_TRUNCATION_LIMIT" in source

    def test_git_ref_display_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _GIT_REF_DISPLAY_LENGTH,
        )

        assert _GIT_REF_DISPLAY_LENGTH == 8

    def test_git_ref_display_length_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _GIT_REF_DISPLAY_LENGTH,
        )

        assert isinstance(_GIT_REF_DISPLAY_LENGTH, int)

    def test_git_ref_display_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import (
            _GIT_REF_DISPLAY_LENGTH,
        )

        assert _GIT_REF_DISPLAY_LENGTH > 0

    def test_git_ref_used_in_poll_ci_checks(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        source = inspect.getsource(_TwoPhaseCLIHand._poll_ci_checks)
        assert "_GIT_REF_DISPLAY_LENGTH" in source


# ---------------------------------------------------------------------------
# 3. docker_sandbox_claude.py naming constants
# ---------------------------------------------------------------------------


class TestDockerSandboxNamingConstants:
    """Verify _SANDBOX_NAME_MAX_LENGTH and _SANDBOX_UUID_HEX_LENGTH."""

    def test_sandbox_name_max_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_NAME_MAX_LENGTH,
        )

        assert _SANDBOX_NAME_MAX_LENGTH == 30

    def test_sandbox_name_max_length_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_NAME_MAX_LENGTH,
        )

        assert isinstance(_SANDBOX_NAME_MAX_LENGTH, int)

    def test_sandbox_name_max_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_NAME_MAX_LENGTH,
        )

        assert _SANDBOX_NAME_MAX_LENGTH > 0

    def test_sandbox_uuid_hex_length_value(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_UUID_HEX_LENGTH,
        )

        assert _SANDBOX_UUID_HEX_LENGTH == 8

    def test_sandbox_uuid_hex_length_type(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_UUID_HEX_LENGTH,
        )

        assert isinstance(_SANDBOX_UUID_HEX_LENGTH, int)

    def test_sandbox_uuid_hex_length_positive(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            _SANDBOX_UUID_HEX_LENGTH,
        )

        assert _SANDBOX_UUID_HEX_LENGTH > 0

    def test_constants_used_in_resolve_sandbox_name(self) -> None:
        from helping_hands.lib.hands.v1.hand.cli.docker_sandbox_claude import (
            DockerSandboxClaudeCodeHand,
        )

        source = inspect.getsource(DockerSandboxClaudeCodeHand._resolve_sandbox_name)
        assert "_SANDBOX_NAME_MAX_LENGTH" in source
        assert "_SANDBOX_UUID_HEX_LENGTH" in source


# ---------------------------------------------------------------------------
# 4. repo.py PermissionError handling
# ---------------------------------------------------------------------------


class TestRepoIndexPermissionError:
    """Verify RepoIndex.from_path() handles PermissionError gracefully."""

    def test_permission_error_returns_empty_files(self, tmp_path: Path) -> None:
        from helping_hands.lib.repo import RepoIndex

        with patch.object(
            Path,
            "rglob",
            side_effect=PermissionError("Permission denied"),
        ):
            index = RepoIndex.from_path(tmp_path)

        assert index.root == tmp_path
        assert index.files == []

    def test_permission_error_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from helping_hands.lib.repo import RepoIndex

        with (
            patch.object(
                Path,
                "rglob",
                side_effect=PermissionError("Permission denied"),
            ),
            caplog.at_level(logging.WARNING, logger="helping_hands.lib.repo"),
        ):
            RepoIndex.from_path(tmp_path)

        assert any("Permission denied" in r.message for r in caplog.records)

    def test_normal_path_still_works(self, tmp_path: Path) -> None:
        """Verify from_path() still works normally without permission errors."""
        from helping_hands.lib.repo import RepoIndex

        (tmp_path / "hello.txt").write_text("hi")
        index = RepoIndex.from_path(tmp_path)
        assert "hello.txt" in index.files
