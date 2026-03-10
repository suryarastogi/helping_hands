"""Tests for Celery configuration helpers."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("celery")

from helping_hands.server import celery_app


class TestResolveCeleryUrls:
    def test_uses_explicit_broker_and_backend(self, monkeypatch) -> None:
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker-host:6379/0")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://backend-host:6379/1")
        monkeypatch.setenv("REDIS_URL", "redis://shared-host:6379/0")

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://broker-host:6379/0"
        assert backend == "redis://backend-host:6379/1"

    def test_all_defaults_when_no_env_vars(self, monkeypatch) -> None:
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://localhost:6379/0"
        assert backend == "redis://localhost:6379/0"

    def test_falls_back_to_redis_url(self, monkeypatch) -> None:
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://shared-host:6379/0")

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://shared-host:6379/0"
        assert backend == "redis://shared-host:6379/0"

    def test_backend_falls_back_to_broker_url(self, monkeypatch) -> None:
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker-host:6379/0")
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)

        broker, backend = celery_app._resolve_celery_urls()

        assert broker == "redis://broker-host:6379/0"
        assert backend == "redis://broker-host:6379/0"


class TestResolveRepoPath:
    def test_clone_owner_repo_uses_token_and_noninteractive_env(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "gh-test-token")
        monkeypatch.setenv("GH_TOKEN", "gh-test-token")
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_test",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            repo_path, cloned_from, temp_root = celery_app._resolve_repo_path(
                "owner/repo"
            )

        clone_cmd = mock_run.call_args.args[0]
        clone_env = mock_run.call_args.kwargs["env"]
        assert clone_cmd[0:4] == ["git", "clone", "--depth", "1"]
        assert (
            clone_cmd[4]
            == "https://x-access-token:gh-test-token@github.com/owner/repo.git"
        )
        assert clone_env["GIT_TERMINAL_PROMPT"] == "0"
        assert clone_env["GCM_INTERACTIVE"] == "never"
        assert repo_path == Path("/tmp/helping_hands_repo_test/repo").resolve()
        assert cloned_from == "owner/repo"
        assert temp_root == Path("/tmp/helping_hands_repo_test")

    def test_clone_owner_repo_falls_back_to_plain_https_without_token(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_test_plain",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            celery_app._resolve_repo_path("owner/repo")

        clone_cmd = mock_run.call_args.args[0]
        assert clone_cmd[4] == "https://github.com/owner/repo.git"

    def test_local_directory_path(self, tmp_path) -> None:
        repo_path, cloned_from, temp_root = celery_app._resolve_repo_path(str(tmp_path))
        assert repo_path == tmp_path.resolve()
        assert cloned_from is None
        assert temp_root is None

    def test_invalid_repo_format_raises(self) -> None:
        with pytest.raises(ValueError, match="not a directory or owner/repo"):
            celery_app._resolve_repo_path("not-a-valid-reference!!!")

    def test_clone_failure_raises_with_redacted_message(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_fail",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
            patch("helping_hands.server.celery_app.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=128,
                stdout="",
                stderr=(
                    "fatal: https://x-access-token:secret-token"
                    "@github.com/owner/repo.git: not found"
                ),
            )
            with pytest.raises(ValueError, match="failed to clone owner/repo"):
                celery_app._resolve_repo_path("owner/repo")
            mock_rmtree.assert_called_once()

    def test_pr_number_adds_no_single_branch(self, monkeypatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        with (
            patch("helping_hands.server.celery_app.Path.is_dir", return_value=False),
            patch(
                "helping_hands.server.celery_app.mkdtemp",
                return_value="/tmp/helping_hands_repo_pr",
            ),
            patch("helping_hands.server.celery_app.subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            celery_app._resolve_repo_path("owner/repo", pr_number=42)

        clone_cmd = mock_run.call_args.args[0]
        assert "--no-single-branch" in clone_cmd


class TestNormalizeBackend:
    def test_defaults_to_codexcli(self) -> None:
        requested, runtime = celery_app._normalize_backend(None)
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_basic_agent_maps_to_atomic_runtime(self) -> None:
        requested, runtime = celery_app._normalize_backend("basic-agent")
        assert requested == "basic-agent"
        assert runtime == "basic-atomic"

    def test_codexcli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("codexcli")
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_claudecodecli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("claudecodecli")
        assert requested == "claudecodecli"
        assert runtime == "claudecodecli"

    def test_goose_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("goose")
        assert requested == "goose"
        assert runtime == "goose"

    def test_geminicli_backend_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("geminicli")
        assert requested == "geminicli"
        assert runtime == "geminicli"

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported backend"):
            celery_app._normalize_backend("unknown-backend")

    def test_strips_whitespace_and_lowercases(self) -> None:
        requested, runtime = celery_app._normalize_backend("  CodexCLI  ")
        assert requested == "codexcli"
        assert runtime == "codexcli"

    def test_opencodecli_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("opencodecli")
        assert requested == "opencodecli"
        assert runtime == "opencodecli"

    def test_e2e_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("e2e")
        assert requested == "e2e"
        assert runtime == "e2e"

    def test_docker_sandbox_claude_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("docker-sandbox-claude")
        assert requested == "docker-sandbox-claude"
        assert runtime == "docker-sandbox-claude"


class TestCodexAuth:
    def test_has_codex_auth_with_openai_key(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert celery_app._has_codex_auth() is True

    def test_has_codex_auth_with_auth_file(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "auth.json").write_text("{}", encoding="utf-8")
        monkeypatch.setenv("HOME", str(tmp_path))
        assert celery_app._has_codex_auth() is True

    def test_has_codex_auth_false_when_no_key_or_auth_file(
        self, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert celery_app._has_codex_auth() is False


class TestGeminiAuth:
    def test_has_gemini_auth_with_key(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "gem-test")
        assert celery_app._has_gemini_auth() is True

    def test_has_gemini_auth_false_without_key(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert celery_app._has_gemini_auth() is False

    def test_has_gemini_auth_false_for_empty_string(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "")
        assert celery_app._has_gemini_auth() is False

    def test_has_gemini_auth_false_for_whitespace_only(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        assert celery_app._has_gemini_auth() is False


class TestUpdateProgress:
    def test_invokes_callable_update_state(self) -> None:
        mock_task = MagicMock()
        celery_app._update_progress(
            mock_task,
            task_id="tid-1",
            stage="running",
            updates=["hello"],
            prompt="do stuff",
            pr_number=None,
            backend="codexcli",
            runtime_backend="codexcli",
            repo_path="/tmp/repo",
            model="gpt-5",
            max_iterations=6,
            no_pr=False,
            enable_execution=False,
            enable_web=False,
            use_native_cli_auth=False,
            tools=("filesystem",),
            skills=(),
        )
        mock_task.update_state.assert_called_once()
        call_kwargs = mock_task.update_state.call_args
        assert call_kwargs.kwargs["state"] == "PROGRESS"
        meta = call_kwargs.kwargs["meta"]
        assert meta["task_id"] == "tid-1"
        assert meta["stage"] == "running"
        assert meta["prompt"] == "do stuff"
        assert meta["backend"] == "codexcli"
        assert meta["tools"] == ["filesystem"]
        assert "workspace" not in meta

    def test_noop_when_update_state_not_callable(self) -> None:
        task = MagicMock(spec=[])  # no update_state attribute
        # Should not raise
        celery_app._update_progress(
            task,
            task_id=None,
            stage="starting",
            updates=[],
            prompt="p",
            pr_number=None,
            backend="codexcli",
            runtime_backend="codexcli",
            repo_path="/tmp",
            model=None,
            max_iterations=1,
            no_pr=False,
            enable_execution=False,
            enable_web=False,
            use_native_cli_auth=False,
            tools=(),
            skills=(),
        )

    def test_workspace_included_when_set(self) -> None:
        mock_task = MagicMock()
        celery_app._update_progress(
            mock_task,
            task_id="tid-2",
            stage="running",
            updates=[],
            prompt="p",
            pr_number=None,
            backend="codexcli",
            runtime_backend="codexcli",
            repo_path="/tmp/repo",
            model=None,
            max_iterations=1,
            no_pr=False,
            enable_execution=False,
            enable_web=False,
            use_native_cli_auth=False,
            tools=(),
            skills=(),
            workspace="/tmp/workspace",
        )
        meta = mock_task.update_state.call_args.kwargs["meta"]
        assert meta["workspace"] == "/tmp/workspace"


class TestCollectStream:
    def test_collects_chunks_and_calls_update(self) -> None:
        mock_task = MagicMock()
        chunks = ["chunk1\n", "chunk2\n", "chunk3\n"]

        async def mock_stream(prompt):
            for c in chunks:
                yield c

        hand = MagicMock()
        hand.stream = mock_stream

        result = asyncio.run(
            celery_app._collect_stream(
                hand,
                "test prompt",
                task=mock_task,
                task_id="t-1",
                pr_number=None,
                updates=[],
                backend="codexcli",
                runtime_backend="codexcli",
                repo_path="/tmp/repo",
                model=None,
                max_iterations=6,
                no_pr=False,
                enable_execution=False,
                enable_web=False,
                use_native_cli_auth=False,
                tools=(),
                skills=(),
            )
        )

        assert result == "chunk1\nchunk2\nchunk3\n"
        # update_progress is called at least once (final call)
        assert mock_task.update_state.call_count >= 1


class TestGetDbUrlWriter:
    def test_returns_env_override(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/mydb")
        assert (
            celery_app._get_db_url_writer() == "postgresql://user:pass@host:5432/mydb"
        )

    def test_returns_default_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        result = celery_app._get_db_url_writer()
        assert result.startswith("postgresql://")
        assert "cavern" in result


class TestEnsureUsageSchedule:
    def test_skips_when_entry_already_exists(self) -> None:
        mock_redbeat = MagicMock()
        mock_entry_cls = mock_redbeat.RedBeatSchedulerEntry
        mock_existing = MagicMock()
        mock_entry_cls.from_key.return_value = mock_existing

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}):
            celery_app.ensure_usage_schedule()

        mock_entry_cls.from_key.assert_called_once()
        # Should NOT create a new entry (constructor not called)
        mock_entry_cls.assert_not_called()

    def test_creates_entry_when_not_exists(self) -> None:
        mock_redbeat = MagicMock()
        mock_entry_cls = mock_redbeat.RedBeatSchedulerEntry
        mock_entry_cls.from_key.side_effect = KeyError("not found")
        mock_new_entry = MagicMock()
        mock_entry_cls.return_value = mock_new_entry

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}):
            celery_app.ensure_usage_schedule()

        mock_new_entry.save.assert_called_once()

    def test_swallows_import_error(self) -> None:
        with patch.dict("sys.modules", {"redbeat": None}):
            # Should not raise even when redbeat is not importable
            celery_app.ensure_usage_schedule()


class TestLogClaudeUsage:
    def _make_keychain_result(self, *, token: str | None = None) -> MagicMock:
        """Build a mock subprocess result for Keychain reads."""
        if token is None:
            return subprocess.CompletedProcess(
                args=[], returncode=44, stdout="", stderr=""
            )
        creds = json.dumps({"claudeAiOauth": {"accessToken": token}})
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=creds, stderr=""
        )

    def test_returns_error_when_keychain_read_fails(self) -> None:
        with patch(
            "helping_hands.server.celery_app.subprocess.run",
            side_effect=OSError("no keychain"),
        ):
            result = celery_app.log_claude_usage()
        assert result["status"] == "error"
        assert "Keychain read failed" in result["message"]

    def test_returns_error_when_no_token_found(self) -> None:
        with patch(
            "helping_hands.server.celery_app.subprocess.run",
            return_value=self._make_keychain_result(token=None),
        ):
            result = celery_app.log_claude_usage()
        assert result["status"] == "error"
        assert "No OAuth token" in result["message"]

    def test_returns_error_on_api_http_error(self) -> None:
        from urllib.error import HTTPError

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(token="ey-test-token"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=HTTPError(
                    url="https://api.anthropic.com/api/oauth/usage",
                    code=401,
                    msg="Unauthorized",
                    hdrs=None,  # type: ignore[arg-type]
                    fp=None,
                ),
            ),
        ):
            result = celery_app.log_claude_usage()
        assert result["status"] == "error"
        assert "HTTP 401" in result["message"]

    def test_returns_error_on_api_generic_error(self) -> None:
        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(token="ey-test-token"),
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=TimeoutError("timed out"),
            ),
        ):
            result = celery_app.log_claude_usage()
        assert result["status"] == "error"
        assert "Usage API failed" in result["message"]

    def test_returns_error_on_db_write_failure(self) -> None:
        usage_data = json.dumps(
            {
                "five_hour": {"utilization": 0.5, "resets_at": "2026-03-06T12:00:00Z"},
                "seven_day": {"utilization": 0.3, "resets_at": "2026-03-10T00:00:00Z"},
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = usage_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.side_effect = Exception("connection refused")

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(token="ey-test-token"),
            ),
            patch("urllib.request.urlopen", return_value=mock_resp),
            patch.dict("sys.modules", {"psycopg2": mock_psycopg2}),
        ):
            result = celery_app.log_claude_usage()

        assert result["status"] == "error"
        assert "DB write failed" in result["message"]
        assert result["session_pct"] == 0.5
        assert result["weekly_pct"] == 0.3

    def test_success_path(self) -> None:
        usage_data = json.dumps(
            {
                "five_hour": {"utilization": 0.25, "resets_at": "2026-03-06T12:00:00Z"},
                "seven_day": {"utilization": 0.1, "resets_at": "2026-03-10T00:00:00Z"},
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = usage_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_psycopg2 = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(token="ey-test-token"),
            ),
            patch("urllib.request.urlopen", return_value=mock_resp),
            patch.dict("sys.modules", {"psycopg2": mock_psycopg2}),
        ):
            result = celery_app.log_claude_usage()

        assert result["status"] == "ok"
        assert result["session_pct"] == 0.25
        assert result["weekly_pct"] == 0.1
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_keychain_non_json_jwt_token(self) -> None:
        """When keychain returns a raw JWT (starts with 'ey'), use it directly."""
        raw_jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test"
        keychain_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=raw_jwt, stderr=""
        )

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=keychain_result,
            ),
            patch(
                "urllib.request.urlopen",
                side_effect=TimeoutError("api down"),
            ),
        ):
            result = celery_app.log_claude_usage()

        # Should have gotten past the token extraction (error is from API call)
        assert result["status"] == "error"
        assert "Usage API failed" in result["message"]

    def test_keychain_non_json_non_jwt_returns_no_token(self) -> None:
        """Non-JSON, non-JWT keychain output means no token."""
        keychain_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="some-garbage-output", stderr=""
        )

        with patch(
            "helping_hands.server.celery_app.subprocess.run",
            return_value=keychain_result,
        ):
            result = celery_app.log_claude_usage()

        assert result["status"] == "error"
        assert "No OAuth token" in result["message"]
