"""Tests for helping_hands.cli.main."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import build_parser, main
from helping_hands.lib.default_prompts import DEFAULT_SMOKE_TEST_PROMPT
from helping_hands.lib.hands.v1.hand import HandResponse


class TestCli:
    def test_cli_uses_smoke_test_default_prompt(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["/tmp/repo"])
        assert args.prompt == DEFAULT_SMOKE_TEST_PROMPT

    def test_cli_parser_supports_tool_enable_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "/tmp/repo",
                "--enable-execution",
                "--enable-web",
                "--use-native-cli-auth",
            ]
        )
        assert args.enable_execution is True
        assert args.enable_web is True
        assert args.use_native_cli_auth is True

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

    @patch("helping_hands.cli.main.subprocess.run")
    @patch("helping_hands.cli.main.RepoIndex.from_path")
    @patch("helping_hands.cli.main.Path.is_dir")
    def test_cli_clones_owner_repo_for_basic_mode(
        self,
        mock_is_dir: MagicMock,
        mock_from_path: MagicMock,
        mock_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_is_dir.side_effect = [False, True]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )
        mock_from_path.return_value = MagicMock(
            root=tmp_path / "repo",
            files=["main.py"],
        )

        main(["suryarastogi/helping_hands"])
        captured = capsys.readouterr()
        assert "Cloned suryarastogi/helping_hands" in captured.out
        assert "Ready. Indexed" in captured.out

    @patch("helping_hands.cli.main.subprocess.run")
    @patch("helping_hands.cli.main.Path.is_dir", return_value=False)
    def test_cli_exits_when_clone_fails(
        self,
        _mock_is_dir: MagicMock,
        mock_run: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="fatal: repository not found",
        )
        with pytest.raises(SystemExit):
            main(["owner/missing"])
        captured = capsys.readouterr()
        assert "failed to clone owner/missing" in captured.err

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
        mock_hand.run.assert_called_once_with("test prompt", pr_number=1, dry_run=False)

    @patch("helping_hands.cli.main.E2EHand")
    def test_cli_runs_e2e_mode_no_pr_sets_dry_run(
        self, mock_hand_cls: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_hand = MagicMock()
        mock_hand.run.return_value = HandResponse(
            message="E2EHand dry run complete. No push/PR performed.",
            metadata={
                "hand_uuid": "abc-123",
                "workspace": "/tmp/work/abc-123/git/owner_repo",
                "pr_url": "",
            },
        )
        mock_hand_cls.return_value = mock_hand

        main(
            [
                "owner/repo",
                "--e2e",
                "--no-pr",
                "--prompt",
                "test prompt",
                "--pr-number",
                "1",
            ]
        )
        captured = capsys.readouterr()
        assert "dry run complete" in captured.out.lower()
        mock_hand.run.assert_called_once_with("test prompt", pr_number=1, dry_run=True)

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.BasicLangGraphHand")
    def test_cli_runs_basic_langgraph_mode(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "basic-langgraph",
                "--prompt",
                "implement feature",
                "--max-iterations",
                "3",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.BasicAtomicHand")
    def test_cli_runs_basic_agent_alias_and_no_pr(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "basic-agent",
                "--no-pr",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        assert mock_hand.auto_pr is False

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.CodexCLIHand")
    def test_cli_runs_codexcli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "codexcli",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.CodexCLIHand")
    def test_cli_reports_codexcli_runtime_error(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_runtime_error(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("Codex CLI command not found: 'codex'")

        mock_asyncio_run.side_effect = _raise_runtime_error
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "codexcli",
                    "--prompt",
                    "implement feature",
                ]
            )
        captured = capsys.readouterr()
        assert "Codex CLI command not found" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.ClaudeCodeHand")
    def test_cli_runs_claudecodecli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "claudecodecli",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.ClaudeCodeHand")
    def test_cli_reports_claudecodecli_runtime_error(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_runtime_error(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("Claude Code CLI command not found: 'claude'")

        mock_asyncio_run.side_effect = _raise_runtime_error
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "claudecodecli",
                    "--prompt",
                    "implement feature",
                ]
            )
        captured = capsys.readouterr()
        assert "Claude Code CLI command not found" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.GooseCLIHand")
    def test_cli_runs_goose_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "goose",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.GooseCLIHand")
    def test_cli_reports_goose_runtime_error(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_runtime_error(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("Goose CLI command not found: 'goose'")

        mock_asyncio_run.side_effect = _raise_runtime_error
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "goose",
                    "--prompt",
                    "implement feature",
                ]
            )
        captured = capsys.readouterr()
        assert "Goose CLI command not found" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.GeminiCLIHand")
    def test_cli_runs_geminicli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _close_coroutine(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            return None

        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "geminicli",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.GeminiCLIHand")
    def test_cli_reports_geminicli_runtime_error(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_runtime_error(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("Gemini CLI command not found: 'gemini'")

        mock_asyncio_run.side_effect = _raise_runtime_error
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "geminicli",
                    "--prompt",
                    "implement feature",
                ]
            )
        captured = capsys.readouterr()
        assert "Gemini CLI command not found" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.BasicLangGraphHand")
    def test_cli_interrupt_requests_hand_interrupt(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_interrupt(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise KeyboardInterrupt

        mock_asyncio_run.side_effect = _raise_interrupt
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "basic-langgraph",
                "--prompt",
                "implement feature",
            ]
        )

        captured = capsys.readouterr()
        assert "Interrupted by user." in captured.out
        mock_hand.interrupt.assert_called_once()

    @patch(
        "helping_hands.cli.main.BasicLangGraphHand",
        side_effect=ModuleNotFoundError("No module named 'langchain_openai'"),
    )
    def test_cli_reports_missing_backend_dependency(
        self,
        _mock_hand_cls: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (tmp_path / "hello.py").write_text("")

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "basic-langgraph",
                    "--prompt",
                    "implement feature",
                ]
            )

        captured = capsys.readouterr()
        assert "missing dependency for --backend basic-langgraph" in captured.err
        assert "uv sync --extra langchain" in captured.err
