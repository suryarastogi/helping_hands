"""Tests for helping_hands.cli.main."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import main
from helping_hands.lib.hands.v1.hand import HandResponse


class TestCli:
    def test_cli_runs_on_valid_dir(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "hello.py").write_text("")
        main([str(tmp_path)])
        captured = capsys.readouterr()
        assert "Ready" in captured.out

    def test_cli_exits_on_missing_dir(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            main([str(tmp_path / "nope")])

    @patch("helping_hands.cli.main.E2EHand")
    def test_cli_runs_e2e_mode(
        self, mock_hand_cls: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_hand = MagicMock()
        mock_hand.run.return_value = HandResponse(
            message="E2EHand complete. PR: https://example/pr/1",
            metadata={
                "hand_uuid": "abc-123",
                "workspace": "/tmp/work/abc-123/git/owner_repo",
                "pr_url": "https://example/pr/1",
            },
        )
        mock_hand_cls.return_value = mock_hand

        main(
            [
                "owner/repo",
                "--e2e",
                "--prompt",
                "test prompt",
                "--pr-number",
                "1",
            ]
        )
        captured = capsys.readouterr()
        assert "E2EHand complete" in captured.out
        assert "hand_uuid=abc-123" in captured.out
        mock_hand.run.assert_called_once_with("test prompt", pr_number=1)
