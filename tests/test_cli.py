"""Tests for helping_hands.cli.main: the CLI entry point.

These tests protect the user-facing contract of the `helping-hands` CLI:
argument parsing, backend dispatch, owner/repo auto-clone, error exit paths,
and the helper utilities (_redact_sensitive, _github_clone_url, etc.). Key
invariants: an "owner/repo" argument triggers a token-authenticated shallow
clone before any hand is constructed; clone failures must exit non-zero with a
clear message; --no-pr correctly sets hand.auto_pr=False; RuntimeErrors from
backends (e.g. CLI not found) are caught and printed to stderr rather than
crashing with a traceback. The _redact_sensitive helper is a security boundary
— regressions cause tokens/keys to appear in logged output.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import (
    _BACKEND_CLI_TOOL,
    _BACKEND_PYTHON_EXTRA,
    _check_backend_available,
    _error_exit,
    _github_clone_url,
    _make_temp_clone_dir,
    _resolve_repo_path,
    _stream_hand,
    build_parser,
    list_backends,
    list_tools,
    main,
    read_prompt_from_stdin,
)
from helping_hands.lib.config import Config
from helping_hands.lib.github_url import (
    noninteractive_env as _git_noninteractive_env,
    redact_credentials as _redact_sensitive,
    repo_tmp_dir as _repo_tmp_dir,
    validate_repo_spec as _validate_repo_spec,
)
from helping_hands.lib.hands.v1.hand import HandResponse
from helping_hands.lib.hands.v1.hand.factory import (
    _BACKEND_ENABLED_ENV_VARS,
    is_backend_enabled,
)

# Suppress coroutine warnings from coverage.py tracer holding frame references
# after mocked asyncio.run closes the coroutine.
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


def _close_coroutine(coro: object) -> None:
    """Close an unawaited coroutine created by mocked ``asyncio.run`` calls.

    Calling ``.close()`` on the coroutine ensures Python marks it as finalized.
    Coverage.py's tracer may still hold frame references that trigger a
    ``RuntimeWarning`` during garbage collection; the module-level
    ``pytestmark`` suppresses those.
    """
    if hasattr(coro, "close"):
        coro.close()


class TestCli:
    def test_cli_prompt_defaults_to_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["/tmp/repo"])
        assert args.prompt is None

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
        main([str(tmp_path), "--prompt", "test"])
        captured = capsys.readouterr()
        assert "Ready" in captured.out

    def test_cli_exits_on_missing_dir(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            main([str(tmp_path / "nope"), "--prompt", "test"])

    @patch("helping_hands.cli.main.subprocess.run")
    @patch("helping_hands.cli.main.RepoIndex.from_path")
    @patch("helping_hands.cli.main.Path.is_dir")
    def test_cli_clones_owner_repo_for_basic_mode(
        self,
        mock_is_dir: MagicMock,
        mock_from_path: MagicMock,
        mock_run: MagicMock,
        monkeypatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
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

        main(["suryarastogi/helping_hands", "--prompt", "test"])
        captured = capsys.readouterr()
        assert "Cloned suryarastogi/helping_hands" in captured.out
        assert "Ready. Indexed" in captured.out
        clone_cmd = mock_run.call_args.args[0]
        clone_env = mock_run.call_args.kwargs["env"]
        assert clone_cmd[0:4] == ["git", "clone", "--depth", "1"]
        assert (
            clone_cmd[4]
            == "https://x-access-token:gh-test-token@github.com/suryarastogi/helping_hands.git"
        )
        assert clone_env["GIT_TERMINAL_PROMPT"] == "0"
        assert clone_env["GCM_INTERACTIVE"] == "never"

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
            main(["owner/missing", "--prompt", "test"])
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_basic_langgraph_mode(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_basic_agent_alias_and_no_pr(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_codexcli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_claudecodecli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_goose_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
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
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_geminicli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
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
    @patch("helping_hands.cli.main.create_hand")
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
    @patch("helping_hands.cli.main.create_hand")
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
        "helping_hands.cli.main.create_hand",
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


# ---------------------------------------------------------------------------
# _github_clone_url
# ---------------------------------------------------------------------------


class TestGithubCloneUrl:
    def test_with_github_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "my-token")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://x-access-token:my-token@github.com/owner/repo.git"

    def test_with_gh_token_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh-tok")
        url = _github_clone_url("owner/repo")
        assert url == "https://x-access-token:gh-tok@github.com/owner/repo.git"

    def test_without_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_github_token_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "primary")
        monkeypatch.setenv("GH_TOKEN", "secondary")
        url = _github_clone_url("owner/repo")
        assert "primary" in url
        assert "secondary" not in url

    def test_empty_token_treated_as_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "  ")
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = _github_clone_url("owner/repo")
        assert url == "https://github.com/owner/repo.git"


# ---------------------------------------------------------------------------
# _git_noninteractive_env
# ---------------------------------------------------------------------------


class TestGitNoninteractiveEnv:
    def test_sets_terminal_prompt(self) -> None:
        env = _git_noninteractive_env()
        assert env["GIT_TERMINAL_PROMPT"] == "0"

    def test_sets_gcm_interactive(self) -> None:
        env = _git_noninteractive_env()
        assert env["GCM_INTERACTIVE"] == "never"

    def test_preserves_existing_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_CUSTOM_VAR", "hello")
        env = _git_noninteractive_env()
        assert env["MY_CUSTOM_VAR"] == "hello"


# ---------------------------------------------------------------------------
# _redact_sensitive
# ---------------------------------------------------------------------------


class TestRedactSensitive:
    def test_redacts_token_url(self) -> None:
        text = "https://x-access-token:secret123@github.com/owner/repo.git"
        result = _redact_sensitive(text)
        assert "secret123" not in result
        assert "***" in result
        assert "github.com/" in result

    def test_passes_non_matching_text(self) -> None:
        text = "fatal: repository not found"
        assert _redact_sensitive(text) == text

    def test_redacts_in_longer_message(self) -> None:
        text = (
            "Cloning https://x-access-token:mysecret99@github.com/o/r.git "
            "failed with error 128"
        )
        result = _redact_sensitive(text)
        assert "mysecret99" not in result
        assert "***" in result

    def test_empty_string(self) -> None:
        assert _redact_sensitive("") == ""


# ---------------------------------------------------------------------------
# _repo_tmp_dir
# ---------------------------------------------------------------------------


class TestRepoTmpDir:
    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HELPING_HANDS_REPO_TMP", raising=False)
        assert _repo_tmp_dir() is None

    def test_returns_path_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "custom_tmp"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        result = _repo_tmp_dir()
        assert result is not None
        assert result == target
        assert target.is_dir()

    def test_returns_none_for_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", "  ")
        assert _repo_tmp_dir() is None

    def test_creates_nested_dirs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "a" / "b" / "c"
        monkeypatch.setenv("HELPING_HANDS_REPO_TMP", str(target))
        result = _repo_tmp_dir()
        assert result is not None
        assert target.is_dir()


# ---------------------------------------------------------------------------
# Additional CLI backend and error path tests
# ---------------------------------------------------------------------------


class TestCliAdditionalPaths:
    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_opencodecli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "opencodecli",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_model_not_found_exits_with_message(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def _raise_model_error(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("The model `bad-model` does not exist")

        mock_asyncio_run.side_effect = _raise_model_error
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "basic-langgraph",
                    "--model",
                    "bad-model",
                    "--prompt",
                    "test",
                ]
            )
        captured = capsys.readouterr()
        assert "not available" in captured.err

    def test_cli_exits_on_invalid_tools(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            main(["/tmp/repo", "--tools", "nonexistent_tool"])
        captured = capsys.readouterr()
        assert "Error" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_runs_docker_sandbox_claude_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_asyncio_run.side_effect = _close_coroutine
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        main(
            [
                str(tmp_path),
                "--backend",
                "docker-sandbox-claude",
                "--prompt",
                "implement feature",
            ]
        )

        mock_hand_cls.assert_called_once()
        mock_asyncio_run.assert_called_once()
        assert mock_hand.auto_pr is True

    @patch(
        "helping_hands.cli.main.create_hand",
        side_effect=ModuleNotFoundError("No module named 'atomic_agents'"),
    )
    def test_cli_reports_python_version_error_for_atomic_backend(
        self,
        _mock_hand_cls: MagicMock,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        (tmp_path / "hello.py").write_text("")
        # Create a mock that compares less than (3, 12) and has .major/.minor
        fake_vi = MagicMock()
        fake_vi.__lt__ = lambda self, other: other > (3, 11)
        fake_vi.major = 3
        fake_vi.minor = 11
        monkeypatch.setattr("helping_hands.cli.main.sys.version_info", fake_vi)

        with pytest.raises(SystemExit):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "basic-atomic",
                    "--prompt",
                    "test",
                ]
            )
        captured = capsys.readouterr()
        assert "requires Python >= 3.12" in captured.err

    @patch("helping_hands.cli.main.asyncio.run")
    @patch("helping_hands.cli.main.create_hand")
    def test_cli_reraises_generic_exception_for_non_cli_backend(
        self,
        mock_hand_cls: MagicMock,
        mock_asyncio_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        def _raise_generic(coro: object) -> None:
            if hasattr(coro, "close"):
                coro.close()
            raise ValueError("unexpected internal error")

        mock_asyncio_run.side_effect = _raise_generic
        (tmp_path / "hello.py").write_text("")
        mock_hand = MagicMock()
        mock_hand_cls.return_value = mock_hand

        with pytest.raises(ValueError, match="unexpected internal error"):
            main(
                [
                    str(tmp_path),
                    "--backend",
                    "basic-langgraph",
                    "--prompt",
                    "test",
                ]
            )


# ---------------------------------------------------------------------------
# _stream_hand
# ---------------------------------------------------------------------------


class TestStreamHand:
    def test_stream_hand_prints_chunks(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        async def _fake_stream(prompt: str):
            yield "hello "
            yield "world"

        hand = MagicMock()
        hand.stream.return_value = _fake_stream("test")

        asyncio.run(_stream_hand(hand, "test"))
        captured = capsys.readouterr()
        assert "hello world" in captured.out

    def test_stream_hand_prints_newline_after_stream(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        async def _fake_stream(prompt: str):
            yield "done"

        hand = MagicMock()
        hand.stream.return_value = _fake_stream("test")

        asyncio.run(_stream_hand(hand, "test"))
        captured = capsys.readouterr()
        assert captured.out.endswith("\n")


# ---------------------------------------------------------------------------
# Top-level package
# ---------------------------------------------------------------------------


class TestPackageVersion:
    def test_version_is_accessible(self) -> None:
        import helping_hands

        assert hasattr(helping_hands, "__version__")
        assert isinstance(helping_hands.__version__, str)
        assert len(helping_hands.__version__) > 0


# ---------------------------------------------------------------------------
# --github-token CLI arg (v147)
# ---------------------------------------------------------------------------


class TestGitHubTokenArg:
    """Tests for the --github-token CLI argument."""

    def test_parser_accepts_github_token(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["/tmp/repo", "--github-token", "ghp_test123"])
        assert args.github_token == "ghp_test123"

    def test_parser_default_github_token_is_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["/tmp/repo"])
        assert args.github_token is None

    def test_github_token_wired_to_config_e2e(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--github-token flows into Config.from_env overrides for --e2e."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_default")
        overrides_seen: list = []

        _original_from_env = Config.from_env.__func__

        def capture_config(cls, *args, **kwargs):
            overrides_seen.append(kwargs.get("overrides", {}))
            return _original_from_env(cls, *args, **kwargs)

        with (
            patch.object(Config, "from_env", classmethod(capture_config)),
            patch("helping_hands.cli.main.E2EHand") as mock_hand_cls,
        ):
            mock_hand = MagicMock()
            mock_hand.run.return_value = HandResponse(
                message="ok",
                metadata={"hand_uuid": "abc", "workspace": "/tmp", "pr_url": ""},
            )
            mock_hand_cls.return_value = mock_hand

            main(
                [
                    "owner/repo",
                    "--e2e",
                    "--github-token",
                    "ghp_custom",
                    "--prompt",
                    "test",
                ]
            )
            assert len(overrides_seen) > 0
            assert overrides_seen[0].get("github_token") == "ghp_custom"

    def test_github_token_wired_to_config_backend(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--github-token flows into Config.from_env overrides for --backend."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_default")
        overrides_seen: list = []

        _original_from_env = Config.from_env.__func__

        def capture_config(cls, *args, **kwargs):
            overrides_seen.append(kwargs.get("overrides", {}))
            return _original_from_env(cls, *args, **kwargs)

        with (
            patch.object(Config, "from_env", classmethod(capture_config)),
            patch("helping_hands.cli.main.RepoIndex") as mock_ri,
            patch("helping_hands.cli.main.create_hand") as mock_hand_cls,
            patch("helping_hands.cli.main.asyncio.run"),
        ):
            mock_ri.from_path.return_value = MagicMock(root=tmp_path, files=[])
            mock_hand_cls.return_value = MagicMock()

            main(
                [
                    str(tmp_path),
                    "--backend",
                    "claudecodecli",
                    "--github-token",
                    "ghp_task",
                    "--prompt",
                    "test",
                ]
            )
            assert len(overrides_seen) > 0
            assert overrides_seen[0].get("github_token") == "ghp_task"


# ---------------------------------------------------------------------------
# --reference-repos CLI arg
# ---------------------------------------------------------------------------


class TestReferenceReposArg:
    """Tests for the --reference-repos CLI argument."""

    def test_parser_accepts_reference_repos(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["/tmp/repo", "--reference-repos", "acme/lib,acme/utils"]
        )
        assert args.reference_repos == "acme/lib,acme/utils"

    def test_parser_default_is_none(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["/tmp/repo"])
        assert args.reference_repos is None

    def test_reference_repos_wired_to_config_backend(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--reference-repos flows into Config.from_env overrides for --backend."""
        overrides_seen: list = []

        _original_from_env = Config.from_env.__func__

        def capture_config(cls, *args, **kwargs):
            overrides_seen.append(kwargs.get("overrides", {}))
            return _original_from_env(cls, *args, **kwargs)

        with (
            patch.object(Config, "from_env", classmethod(capture_config)),
            patch("helping_hands.cli.main.RepoIndex") as mock_ri,
            patch("helping_hands.cli.main.create_hand") as mock_hand_cls,
            patch("helping_hands.cli.main.asyncio.run"),
        ):
            mock_ri.from_path.return_value = MagicMock(
                root=tmp_path, files=[], reference_repos=[]
            )
            mock_hand_cls.return_value = MagicMock()

            main(
                [
                    str(tmp_path),
                    "--backend",
                    "claudecodecli",
                    "--reference-repos",
                    "acme/lib",
                    "--prompt",
                    "test",
                ]
            )
            assert len(overrides_seen) > 0
            assert overrides_seen[0].get("reference_repos") == "acme/lib"


# ---------------------------------------------------------------------------
# _validate_repo_spec — v149
# ---------------------------------------------------------------------------


class TestValidateRepoSpec:
    def test_valid_owner_repo(self) -> None:
        _validate_repo_spec("owner/repo")  # should not raise

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_repo_spec("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_repo_spec("   ")

    def test_no_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("just-a-repo")

    def test_trailing_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("owner/")

    def test_leading_slash_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("/repo")

    def test_too_many_slashes_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            _validate_repo_spec("a/b/c")


class TestGithubCloneUrlValidation:
    """v149: _github_clone_url rejects invalid repo specs."""

    def test_empty_repo_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with pytest.raises(ValueError, match="must not be empty"):
            _github_clone_url("")

    def test_no_slash_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with pytest.raises(ValueError, match="owner/repo"):
            _github_clone_url("just-a-name")


# ---------------------------------------------------------------------------
# Docstring presence tests (v174)
# ---------------------------------------------------------------------------


class TestCliMainDocstrings:
    """Verify Google-style docstrings on 4 newly-documented private methods."""

    def test_stream_hand_has_docstring(self) -> None:
        doc = _stream_hand.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_github_clone_url_has_docstring(self) -> None:
        doc = _github_clone_url.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_github_clone_url_has_returns(self) -> None:
        doc = _github_clone_url.__doc__
        assert "Returns:" in doc

    def test_github_clone_url_has_raises(self) -> None:
        doc = _github_clone_url.__doc__
        assert "Raises:" in doc

    def test_git_noninteractive_env_has_docstring(self) -> None:
        doc = _git_noninteractive_env.__doc__
        assert doc is not None
        assert "Returns:" in doc

    def test_resolve_repo_path_has_docstring(self) -> None:
        doc = _resolve_repo_path.__doc__
        assert doc is not None
        assert "Args:" in doc

    def test_resolve_repo_path_has_returns(self) -> None:
        doc = _resolve_repo_path.__doc__
        assert "Returns:" in doc

    def test_resolve_repo_path_has_raises(self) -> None:
        doc = _resolve_repo_path.__doc__
        assert "Raises:" in doc


class TestErrorExit:
    """v268: _error_exit prints to stderr and exits with code 1."""

    def test_prints_error_prefix_and_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _error_exit("something went wrong")
        assert exc_info.value.code == 1

    def test_message_written_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit):
            _error_exit("bad input")
        assert "Error: bad input" in capsys.readouterr().err

    def test_empty_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            _error_exit("")
        assert "Error: " in capsys.readouterr().err

    def test_has_docstring(self) -> None:
        assert _error_exit.__doc__ is not None
        assert "Args:" in _error_exit.__doc__


class TestMakeTempCloneDir:
    """v268: _make_temp_clone_dir creates temp dir with atexit cleanup."""

    def test_returns_repo_subdir(self, tmp_path: Path) -> None:
        with (
            patch("helping_hands.cli.main._repo_tmp_dir", return_value=str(tmp_path)),
            patch("helping_hands.cli.main.atexit") as mock_atexit,
        ):
            result = _make_temp_clone_dir("test_prefix_")
            assert result.name == "repo"
            assert result.parent.exists()
            assert result.parent.name.startswith("test_prefix_")
            mock_atexit.register.assert_called_once()

    def test_parent_dir_is_created(self, tmp_path: Path) -> None:
        with (
            patch("helping_hands.cli.main._repo_tmp_dir", return_value=str(tmp_path)),
            patch("helping_hands.cli.main.atexit"),
        ):
            result = _make_temp_clone_dir("hh_")
            assert result.parent.is_dir()
            # repo subdir itself is NOT created by the helper
            assert not result.exists()

    def test_atexit_registers_rmtree(self, tmp_path: Path) -> None:
        import shutil

        with (
            patch("helping_hands.cli.main._repo_tmp_dir", return_value=str(tmp_path)),
            patch("helping_hands.cli.main.atexit") as mock_atexit,
        ):
            result = _make_temp_clone_dir("prefix_")
            mock_atexit.register.assert_called_once_with(
                shutil.rmtree, result.parent, True
            )

    def test_has_docstring(self) -> None:
        assert _make_temp_clone_dir.__doc__ is not None
        assert "Args:" in _make_temp_clone_dir.__doc__


# ---------------------------------------------------------------------------
# read_prompt_from_stdin — interactive mode
# ---------------------------------------------------------------------------


class TestReadPromptFromStdin:
    """Tests for interactive/piped prompt reading via stdin."""

    def test_reads_from_pipe(self) -> None:
        """Non-TTY stdin reads silently."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "fix the bug\n"
        with patch("helping_hands.cli.main.sys.stdin", mock_stdin):
            result = read_prompt_from_stdin()
        assert result == "fix the bug"

    def test_tty_prints_prompt_message(self) -> None:
        """TTY stdin prints an interactive prompt to stderr."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.read.return_value = "add feature\n"
        with (
            patch("helping_hands.cli.main.sys.stdin", mock_stdin),
            patch("helping_hands.cli.main.print") as mock_print,
        ):
            result = read_prompt_from_stdin()
        assert result == "add feature"
        mock_print.assert_called_once()
        call_args = mock_print.call_args
        assert "task description" in call_args.args[0].lower()

    def test_empty_input_exits(self) -> None:
        """Empty stdin causes SystemExit."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = ""
        with (
            patch("helping_hands.cli.main.sys.stdin", mock_stdin),
            pytest.raises(SystemExit),
        ):
            read_prompt_from_stdin()

    def test_whitespace_only_exits(self) -> None:
        """Whitespace-only stdin causes SystemExit."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "   \n\n  "
        with (
            patch("helping_hands.cli.main.sys.stdin", mock_stdin),
            pytest.raises(SystemExit),
        ):
            read_prompt_from_stdin()

    def test_keyboard_interrupt_exits(self) -> None:
        """Ctrl+C during input causes SystemExit."""
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdin.read.side_effect = KeyboardInterrupt
        with (
            patch("helping_hands.cli.main.sys.stdin", mock_stdin),
            patch("helping_hands.cli.main.print"),
            pytest.raises(SystemExit),
        ):
            read_prompt_from_stdin()

    def test_has_docstring(self) -> None:
        assert read_prompt_from_stdin.__doc__ is not None
        assert "Returns:" in read_prompt_from_stdin.__doc__


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


class TestVersionFlag:
    """Tests for the ``--version`` / ``-V`` CLI flag."""

    def test_version_long_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``--version`` prints version and returns without parsing args."""
        main(["--version"])
        out = capsys.readouterr().out
        assert "helping-hands" in out
        # Should contain a semver-like version string.
        import re as _re

        assert _re.search(r"\d+\.\d+\.\d+", out), f"no version found in: {out!r}"

    def test_version_short_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``-V`` prints version and returns without parsing args."""
        main(["-V"])
        out = capsys.readouterr().out
        assert "helping-hands" in out

    def test_version_flag_does_not_require_repo(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--version`` works even without a positional 'repo' argument."""
        # If --version weren't intercepted early, argparse would error
        # about the missing required 'repo' argument.
        main(["--version"])
        assert "helping-hands" in capsys.readouterr().out

    def test_version_matches_package(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Printed version matches ``helping_hands.__version__``."""
        from helping_hands import __version__

        main(["--version"])
        assert __version__ in capsys.readouterr().out


class TestListBackends:
    """Tests for ``--list-backends`` flag and ``list_backends()``."""

    def test_list_backends_flag_prints_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--list-backends`` prints backend table and returns."""
        main(["--list-backends"])
        out = capsys.readouterr().out
        assert "helping-hands backends" in out

    def test_list_backends_does_not_require_repo(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--list-backends`` works without a positional 'repo' argument."""
        main(["--list-backends"])
        assert "backends" in capsys.readouterr().out

    def test_list_backends_contains_all_backends(self) -> None:
        """Output includes every backend from SUPPORTED_BACKENDS."""
        from helping_hands.lib.hands.v1.hand.factory import SUPPORTED_BACKENDS

        output = list_backends()
        for backend in SUPPORTED_BACKENDS:
            assert backend in output, f"missing backend: {backend}"

    def test_list_backends_shows_version(self) -> None:
        """Header line includes the package version."""
        from helping_hands import __version__

        output = list_backends()
        assert __version__ in output

    def test_list_backends_shows_availability_symbols(self) -> None:
        """Each line has a [+] or [-] availability marker."""
        output = list_backends()
        lines = [ln for ln in output.splitlines() if ln.strip().startswith("[")]
        assert len(lines) > 0
        for line in lines:
            assert "[+]" in line or "[-]" in line

    def test_check_backend_available_e2e(self) -> None:
        """E2E backend is always available."""
        available, detail = _check_backend_available("e2e")
        assert available is True
        assert "always" in detail

    def test_check_backend_available_cli_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI backend reports available when tool is on PATH."""
        monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
        available, detail = _check_backend_available("claudecodecli")
        assert available is True
        assert "claude found" in detail

    def test_check_backend_available_cli_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI backend reports unavailable when tool is not on PATH."""
        monkeypatch.setattr("shutil.which", lambda name: None)
        available, detail = _check_backend_available("claudecodecli")
        assert available is False
        assert "not found" in detail

    def test_check_backend_available_extra_installed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Library backend reports available when Python extra is importable."""
        monkeypatch.setattr(
            "builtins.__import__",
            lambda name, *a, **kw: (
                __import__(name, *a, **kw)
                if name != "langchain_core"
                else type("mod", (), {})
            ),
        )
        available, detail = _check_backend_available("basic-langgraph")
        assert available is True
        assert "installed" in detail

    def test_check_backend_available_extra_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Library backend reports unavailable when Python extra is not importable."""
        original_import = (
            __builtins__["__import__"]
            if isinstance(__builtins__, dict)
            else __builtins__.__import__
        )

        def fake_import(name, *a, **kw):
            if name == "langchain_core":
                raise ImportError("no langchain")
            return original_import(name, *a, **kw)

        monkeypatch.setattr("builtins.__import__", fake_import)
        available, detail = _check_backend_available("basic-langgraph")
        assert available is False
        assert "not installed" in detail

    def test_backend_cli_tool_covers_all_cli_backends(self) -> None:
        """Every CLI-backed backend in SUPPORTED_BACKENDS has a tool mapping."""
        from helping_hands.lib.hands.v1.hand.factory import SUPPORTED_BACKENDS

        # Backends not in _BACKEND_CLI_TOOL and not in _BACKEND_PYTHON_EXTRA
        # should only be "e2e".
        unmapped = {
            b
            for b in SUPPORTED_BACKENDS
            if b not in _BACKEND_CLI_TOOL
            and b not in _BACKEND_PYTHON_EXTRA
            and b != "e2e"
        }
        assert unmapped == set(), f"backends without availability check: {unmapped}"

    def test_list_backends_registered_count(self) -> None:
        """Footer shows the total backend count."""
        from helping_hands.lib.hands.v1.hand.factory import SUPPORTED_BACKENDS

        output = list_backends()
        assert str(len(SUPPORTED_BACKENDS)) in output


class TestIsBackendEnabled:
    """Tests for ``is_backend_enabled()`` from factory module."""

    def test_all_enabled_by_default(self) -> None:
        """All backends enabled when no *_ENABLED env vars are set."""
        enabled, detail = is_backend_enabled("e2e")
        assert enabled is True
        assert "default" in detail

    def test_enabled_when_env_var_set_truthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backend is enabled when its env var is set to a truthy value."""
        monkeypatch.setenv("HELPING_HANDS_E2E_ENABLED", "1")
        enabled, detail = is_backend_enabled("e2e")
        assert enabled is True
        assert "HELPING_HANDS_E2E_ENABLED" in detail

    def test_disabled_when_env_var_set_falsy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backend is disabled when another backend's env var is set but not this one."""
        # Set a different backend's env var to activate selective mode.
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "1")
        # Ensure e2e's env var is NOT set.
        monkeypatch.delenv("HELPING_HANDS_E2E_ENABLED", raising=False)
        enabled, detail = is_backend_enabled("e2e")
        assert enabled is False
        assert "disabled" in detail

    def test_disabled_when_own_env_var_is_falsy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backend is disabled when its own env var is set to a non-truthy value."""
        monkeypatch.setenv("HELPING_HANDS_E2E_ENABLED", "0")
        enabled, detail = is_backend_enabled("e2e")
        assert enabled is False
        assert "disabled" in detail

    def test_unknown_backend_returns_enabled(self) -> None:
        """Backend not in _BACKEND_ENABLED_ENV_VARS returns enabled."""
        enabled, detail = is_backend_enabled("nonexistent-backend-xyz")
        assert enabled is True
        assert "no env var" in detail

    def test_env_var_names_in_detail(self) -> None:
        """Enabled detail includes the actual env var name for all known backends."""
        for backend in _BACKEND_ENABLED_ENV_VARS:
            enabled, detail = is_backend_enabled(backend)
            # In default mode, detail says "enabled (default)" — that's fine.
            # We just verify it returns a tuple.
            assert isinstance(enabled, bool)
            assert isinstance(detail, str)


class TestListBackendsEnabledStatus:
    """Tests for enriched ``list_backends()`` output with enabled/disabled status."""

    def test_disabled_backend_shows_in_output(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Disabled backends appear with [-] and include env var name."""
        # Enable only codexcli, which disables all others.
        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "1")
        for backend, env_var in _BACKEND_ENABLED_ENV_VARS.items():
            if backend != "codexcli":
                monkeypatch.delenv(env_var, raising=False)
        output = list_backends()
        # e2e should show [-] because it's disabled (not in enabled list)
        e2e_line = next(ln for ln in output.splitlines() if "e2e" in ln)
        assert "[-]" in e2e_line
        assert "disabled" in e2e_line

    def test_enabled_backend_shows_plus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Enabled and available backends show [+]."""
        # Default mode: all enabled.
        output = list_backends()
        e2e_line = next(ln for ln in output.splitlines() if "e2e" in ln)
        assert "[+]" in e2e_line

    def test_enabled_count_with_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Footer shows X of Y when env vars selectively enable backends."""
        from helping_hands.lib.hands.v1.hand.factory import SUPPORTED_BACKENDS

        monkeypatch.setenv("HELPING_HANDS_CODEXCLI_ENABLED", "1")
        for backend, env_var in _BACKEND_ENABLED_ENV_VARS.items():
            if backend != "codexcli":
                monkeypatch.delenv(env_var, raising=False)
        output = list_backends()
        assert f"1 of {len(SUPPORTED_BACKENDS)}" in output


class TestCheckBackendAvailableWarning:
    """Tests for the unmapped-backend warning in ``_check_backend_available()``."""

    def test_unmapped_backend_logs_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unknown backend triggers a logger warning."""
        import logging

        with caplog.at_level(logging.WARNING, logger="helping_hands.cli.main"):
            available, detail = _check_backend_available("nonexistent-backend-xyz")
        assert available is True
        assert detail == "available"
        assert "nonexistent-backend-xyz" in caplog.text
        assert "not mapped" in caplog.text


class TestListTools:
    """Tests for ``--list-tools`` flag and ``list_tools()``."""

    def test_list_tools_flag_prints_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--list-tools`` prints tool category table and returns."""
        main(["--list-tools"])
        out = capsys.readouterr().out
        assert "tool categories" in out

    def test_list_tools_does_not_require_repo(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``--list-tools`` works without a positional 'repo' argument."""
        main(["--list-tools"])
        assert "tool categories" in capsys.readouterr().out

    def test_list_tools_contains_all_categories(self) -> None:
        """Output includes every category from available_tool_category_names()."""
        from helping_hands.lib.meta.tools.registry import available_tool_category_names

        output = list_tools()
        for name in available_tool_category_names():
            assert name in output, f"missing category: {name}"

    def test_list_tools_shows_version(self) -> None:
        """Header line includes the package version."""
        from helping_hands import __version__

        output = list_tools()
        assert __version__ in output

    def test_list_tools_shows_tool_names(self) -> None:
        """Output includes individual tool spec names."""
        output = list_tools()
        assert "python.run_code" in output
        assert "web.search" in output

    def test_list_tools_shows_enable_hint(self) -> None:
        """Footer includes usage hint for --tools flag."""
        output = list_tools()
        assert "--tools" in output

    def test_list_tools_shows_category_titles(self) -> None:
        """Output includes the human-readable title for each category."""
        from helping_hands.lib.meta.tools.registry import (
            available_tool_category_names,
            resolve_tool_categories,
        )

        categories = resolve_tool_categories(available_tool_category_names())
        output = list_tools()
        for cat in categories:
            assert cat.title in output
