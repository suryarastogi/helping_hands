"""Tests for hhpy.helping_hands.cli.main."""

from __future__ import annotations

from pathlib import Path

import pytest

from hhpy.helping_hands.cli.main import main


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
