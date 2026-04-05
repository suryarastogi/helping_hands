"""Tests for v374: CLI error exit backends consistency.

Verifies that `_CLI_ERROR_EXIT_BACKENDS` stays in sync with
`_BACKEND_CLI_TOOL` (all CLI-tool-backed backends should get clean error
messages instead of full tracebacks), and that the opencode/devin error
exit paths work correctly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.cli.main import (
    _BACKEND_CLI_TOOL,
    _CLI_ERROR_EXIT_BACKENDS,
    main,
)
from helping_hands.lib.hands.v1.hand.factory import (
    BACKEND_DEVINCLI,
    BACKEND_E2E,
    BACKEND_OPENCODECLI,
)

# ---------------------------------------------------------------------------
# Structural consistency
# ---------------------------------------------------------------------------


class TestCliErrorExitBackendsConsistency:
    """All CLI-tool-backed backends must be in _CLI_ERROR_EXIT_BACKENDS."""

    def test_all_cli_tool_backends_in_error_exit_set(self) -> None:
        """Every backend in _BACKEND_CLI_TOOL should be in _CLI_ERROR_EXIT_BACKENDS."""
        missing = set(_BACKEND_CLI_TOOL.keys()) - _CLI_ERROR_EXIT_BACKENDS
        assert not missing, (
            f"CLI backends missing from _CLI_ERROR_EXIT_BACKENDS: {sorted(missing)}. "
            "Add them so these backends get clean error messages instead of tracebacks."
        )

    def test_no_non_cli_backends_in_error_exit_set(self) -> None:
        """_CLI_ERROR_EXIT_BACKENDS should not contain non-CLI backends."""
        cli_backends = set(_BACKEND_CLI_TOOL.keys())
        non_cli = _CLI_ERROR_EXIT_BACKENDS - cli_backends
        assert not non_cli, (
            f"Non-CLI backends in _CLI_ERROR_EXIT_BACKENDS: {sorted(non_cli)}. "
            "Only CLI-tool-backed backends should be in this set."
        )

    def test_e2e_not_in_error_exit_set(self) -> None:
        """E2E backend has its own flow and should not be in the error exit set."""
        assert BACKEND_E2E not in _CLI_ERROR_EXIT_BACKENDS

    def test_opencodecli_in_error_exit_set(self) -> None:
        """opencodecli must be in the error exit set (regression check for v374)."""
        assert BACKEND_OPENCODECLI in _CLI_ERROR_EXIT_BACKENDS

    def test_devincli_in_error_exit_set(self) -> None:
        """devincli must be in the error exit set (regression check for v374)."""
        assert BACKEND_DEVINCLI in _CLI_ERROR_EXIT_BACKENDS


# ---------------------------------------------------------------------------
# Error exit paths for opencode and devin
# ---------------------------------------------------------------------------


class TestOpenCodeErrorExit:
    """Verify opencodecli triggers _error_exit on RuntimeError."""

    def test_runtime_error_exits_cleanly(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        repo_dir = tmp_path / "repo"  # type: ignore[operator]
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# test")

        mock_hand = MagicMock()
        mock_hand.stream = MagicMock(
            return_value=AsyncMock(side_effect=RuntimeError("opencode failed"))
        )
        mock_hand.auto_pr = True

        with (
            patch("helping_hands.cli.main.create_hand", return_value=mock_hand),
            patch(
                "helping_hands.cli.main.asyncio.run",
                side_effect=RuntimeError("opencode failed"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main([str(repo_dir), "--backend", "opencodecli", "--prompt", "test task"])
        assert exc_info.value.code == 1

    def test_os_error_exits_cleanly(self, tmp_path: pytest.TempPathFactory) -> None:
        repo_dir = tmp_path / "repo"  # type: ignore[operator]
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# test")

        mock_hand = MagicMock()
        mock_hand.auto_pr = True

        with (
            patch("helping_hands.cli.main.create_hand", return_value=mock_hand),
            patch(
                "helping_hands.cli.main.asyncio.run",
                side_effect=OSError("connection refused"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main([str(repo_dir), "--backend", "opencodecli", "--prompt", "test task"])
        assert exc_info.value.code == 1


class TestDevinErrorExit:
    """Verify devincli triggers _error_exit on RuntimeError."""

    def test_runtime_error_exits_cleanly(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        repo_dir = tmp_path / "repo"  # type: ignore[operator]
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# test")

        mock_hand = MagicMock()
        mock_hand.auto_pr = True

        with (
            patch("helping_hands.cli.main.create_hand", return_value=mock_hand),
            patch(
                "helping_hands.cli.main.asyncio.run",
                side_effect=RuntimeError("devin failed"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main([str(repo_dir), "--backend", "devincli", "--prompt", "test task"])
        assert exc_info.value.code == 1

    def test_value_error_exits_cleanly(self, tmp_path: pytest.TempPathFactory) -> None:
        repo_dir = tmp_path / "repo"  # type: ignore[operator]
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# test")

        mock_hand = MagicMock()
        mock_hand.auto_pr = True

        with (
            patch("helping_hands.cli.main.create_hand", return_value=mock_hand),
            patch(
                "helping_hands.cli.main.asyncio.run",
                side_effect=ValueError("bad input"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main([str(repo_dir), "--backend", "devincli", "--prompt", "test task"])
        assert exc_info.value.code == 1
