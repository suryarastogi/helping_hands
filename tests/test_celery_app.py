"""Tests for Celery configuration helpers."""

from __future__ import annotations

import asyncio
import json
import os
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
    def test_defaults_to_claudecodecli(self) -> None:
        requested, runtime = celery_app._normalize_backend(None)
        assert requested == "claudecodecli"
        assert runtime == "claudecodecli"

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

    def test_devincli_is_supported(self) -> None:
        requested, runtime = celery_app._normalize_backend("devincli")
        assert requested == "devincli"
        assert runtime == "devincli"

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


def _make_emitter(mock_task=None, updates=None, **kwargs):
    """Create a _ProgressEmitter with sensible test defaults."""
    defaults = {
        "task_id": "t-1",
        "updates": updates if updates is not None else [],
        "prompt": "test prompt",
        "pr_number": None,
        "backend": "codexcli",
        "runtime_backend": "codexcli",
        "repo_path": "/tmp/repo",
        "model": None,
        "max_iterations": 6,
        "no_pr": False,
        "enable_execution": False,
        "enable_web": False,
        "use_native_cli_auth": False,
        "tools": (),
        "skills": (),
    }
    defaults.update(kwargs)
    task = mock_task or MagicMock()
    return celery_app._ProgressEmitter(task, **defaults)


class TestCollectStream:
    def test_collects_chunks_and_calls_update(self) -> None:
        mock_task = MagicMock()
        updates: list[str] = []
        chunks = ["chunk1\n", "chunk2\n", "chunk3\n"]

        async def mock_stream(prompt):
            for c in chunks:
                yield c

        hand = MagicMock()
        hand.stream = mock_stream
        emitter = _make_emitter(mock_task, updates=updates)

        result = asyncio.run(
            celery_app._collect_stream(
                hand,
                "test prompt",
                emitter=emitter,
                updates=updates,
            )
        )

        assert result == "chunk1\nchunk2\nchunk3\n"
        # update_progress is called at least once (final call)
        assert mock_task.update_state.call_count >= 1

    def test_empty_stream_returns_empty_string(self) -> None:
        mock_task = MagicMock()
        updates: list[str] = []

        async def mock_stream(prompt):
            return
            yield  # make this an async generator

        hand = MagicMock()
        hand.stream = mock_stream
        emitter = _make_emitter(mock_task, updates=updates)

        result = asyncio.run(
            celery_app._collect_stream(
                hand,
                "test prompt",
                emitter=emitter,
                updates=updates,
            )
        )
        assert result == ""
        # Final update_progress is still called
        assert mock_task.update_state.call_count >= 1

    def test_workspace_and_started_at_forwarded(self) -> None:
        mock_task = MagicMock()
        updates: list[str] = []

        async def mock_stream(prompt):
            yield "data\n"

        hand = MagicMock()
        hand.stream = mock_stream
        emitter = _make_emitter(
            mock_task,
            updates=updates,
            task_id="t-ws",
            workspace="/tmp/workspace",
            started_at="2026-03-10T00:00:00+00:00",
        )

        asyncio.run(
            celery_app._collect_stream(
                hand,
                "test prompt",
                emitter=emitter,
                updates=updates,
            )
        )
        # Verify the final call includes workspace and started_at
        final_meta = mock_task.update_state.call_args.kwargs["meta"]
        assert final_meta["workspace"] == "/tmp/workspace"
        assert final_meta["started_at"] == "2026-03-10T00:00:00+00:00"

    def test_periodic_updates_called_for_many_chunks(self) -> None:
        mock_task = MagicMock()
        updates: list[str] = []
        chunk_count = 24

        async def mock_stream(prompt):
            for i in range(chunk_count):
                yield f"chunk{i}\n"

        hand = MagicMock()
        hand.stream = mock_stream
        emitter = _make_emitter(mock_task, updates=updates, task_id="t-many")

        asyncio.run(
            celery_app._collect_stream(
                hand,
                "prompt",
                emitter=emitter,
                updates=updates,
            )
        )
        # With 24 chunks and update every 8, expect 3 periodic + 1 final = 4
        assert mock_task.update_state.call_count >= 4


class TestFormatRuntime:
    """Tests for _format_runtime helper (via celery_app module)."""

    def test_sub_minute(self) -> None:
        assert celery_app._format_runtime(30.5) == "30.5s"

    def test_over_minute(self) -> None:
        assert celery_app._format_runtime(90.0) == "1m 30s"

    def test_zero(self) -> None:
        assert celery_app._format_runtime(0.0) == "0.0s"


class TestGetDbUrlWriter:
    def test_returns_env_value(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/mydb")
        assert (
            celery_app._get_db_url_writer() == "postgresql://user:pass@host:5432/mydb"
        )

    def test_raises_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            celery_app._get_db_url_writer()

    def test_raises_when_empty(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "")
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            celery_app._get_db_url_writer()

    def test_raises_when_whitespace_only(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "   ")
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            celery_app._get_db_url_writer()

    def test_strips_whitespace(self, monkeypatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "  postgresql://host/db  ")
        assert celery_app._get_db_url_writer() == "postgresql://host/db"


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

        fake_pg_error = type("Error", (Exception,), {})
        mock_psycopg2 = MagicMock()
        mock_psycopg2.Error = fake_pg_error
        mock_psycopg2.connect.side_effect = fake_pg_error("connection refused")

        with (
            patch(
                "helping_hands.server.celery_app.subprocess.run",
                return_value=self._make_keychain_result(token="ey-test-token"),
            ),
            patch("urllib.request.urlopen", return_value=mock_resp),
            patch.dict("sys.modules", {"psycopg2": mock_psycopg2}),
            patch.dict("os.environ", {"DATABASE_URL": "postgresql://localhost/test"}),
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

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
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
            patch.dict(
                os.environ, {"DATABASE_URL": "postgres://test:test@localhost/test"}
            ),
        ):
            result = celery_app.log_claude_usage()

        assert result["status"] == "ok", f"Expected ok but got: {result}"
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


# ---------------------------------------------------------------------------
# _maybe_persist_pr_to_schedule (v304)
# ---------------------------------------------------------------------------


class TestMaybePersistPrToSchedule:
    """Tests for the _maybe_persist_pr_to_schedule helper."""

    def test_skips_when_no_schedule_id(self) -> None:
        """No-op when schedule_id is None (non-scheduled build)."""
        with patch(
            "helping_hands.server.schedules.get_schedule_manager"
        ) as mock_get_mgr:
            celery_app._maybe_persist_pr_to_schedule(None, None, "42")
        mock_get_mgr.assert_not_called()

    def test_skips_when_input_pr_already_set(self) -> None:
        """No-op when input pr_number was already set on the schedule."""
        with patch(
            "helping_hands.server.schedules.get_schedule_manager"
        ) as mock_get_mgr:
            celery_app._maybe_persist_pr_to_schedule("sched_abc", 10, "42")
        mock_get_mgr.assert_not_called()

    def test_skips_when_result_pr_empty(self) -> None:
        """No-op when the hand did not create a PR (empty string)."""
        with patch(
            "helping_hands.server.schedules.get_schedule_manager"
        ) as mock_get_mgr:
            celery_app._maybe_persist_pr_to_schedule("sched_abc", None, "")
        mock_get_mgr.assert_not_called()

    def test_skips_when_result_pr_non_digit(self) -> None:
        """No-op when result PR number is not a digit string."""
        with patch(
            "helping_hands.server.schedules.get_schedule_manager"
        ) as mock_get_mgr:
            celery_app._maybe_persist_pr_to_schedule("sched_abc", None, "abc")
        mock_get_mgr.assert_not_called()

    def test_persists_newly_created_pr(self) -> None:
        """Should call update_pr_number when a new PR was created."""
        mock_mgr = MagicMock()
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            return_value=mock_mgr,
        ):
            celery_app._maybe_persist_pr_to_schedule("sched_abc", None, "42")
        mock_mgr.update_pr_number.assert_called_once_with("sched_abc", 42)

    def test_exception_does_not_propagate(self) -> None:
        """Errors during persist are swallowed (logged, not re-raised)."""
        with patch(
            "helping_hands.server.schedules.get_schedule_manager",
            side_effect=RuntimeError("Redis down"),
        ):
            # Should not raise
            celery_app._maybe_persist_pr_to_schedule("sched_abc", None, "42")


# ---------------------------------------------------------------------------
# _try_create_issue (v326)
# ---------------------------------------------------------------------------


class TestTryCreateIssue:
    """Tests for the _try_create_issue helper."""

    def test_creates_issue_and_sets_hand_issue_number(self) -> None:
        """On success, hand.issue_number is set and updates list is appended."""
        hand = MagicMock()
        hand.issue_number = None
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.create_issue.return_value = {
            "number": 55,
            "url": "https://github.com/owner/repo/issues/55",
        }
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch(
            "helping_hands.lib.github.GitHubClient",
            return_value=mock_gh,
        ):
            from helping_hands.server import celery_app as _mod

            _mod._try_create_issue(
                repo_spec="owner/repo",
                prompt="Add feature X",
                hand=hand,
                updates=updates,
                github_token="tok_123",
            )

        assert hand.issue_number == 55
        assert any("#55" in u for u in updates)
        mock_gh.create_issue.assert_called_once_with(
            "owner/repo",
            title="[helping-hands] Add feature X",
            body="Add feature X",
            labels=["helping-hands"],
        )

    def test_truncates_long_prompt_title(self) -> None:
        """Title is truncated to first 120 chars of first line."""
        hand = MagicMock()
        hand.issue_number = None
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.create_issue.return_value = {"number": 1, "url": "url"}
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        long_prompt = "A" * 200 + "\nSecond line"
        with patch(
            "helping_hands.lib.github.GitHubClient",
            return_value=mock_gh,
        ):
            from helping_hands.server import celery_app as _mod

            _mod._try_create_issue(
                repo_spec="owner/repo",
                prompt=long_prompt,
                hand=hand,
                updates=updates,
                github_token=None,
            )

        call_kwargs = mock_gh.create_issue.call_args
        title = call_kwargs[1]["title"] if call_kwargs[1] else call_kwargs[0][1]
        # Title prefix is "[helping-hands] " (16 chars) + 120 chars = 136
        assert len(title) == 16 + 120

    def test_multiline_prompt_uses_first_line(self) -> None:
        """Title uses only the first line of a multi-line prompt."""
        hand = MagicMock()
        hand.issue_number = None
        updates: list[str] = []
        mock_gh = MagicMock()
        mock_gh.create_issue.return_value = {"number": 2, "url": "url"}
        mock_gh.__enter__ = MagicMock(return_value=mock_gh)
        mock_gh.__exit__ = MagicMock(return_value=False)

        with patch(
            "helping_hands.lib.github.GitHubClient",
            return_value=mock_gh,
        ):
            from helping_hands.server import celery_app as _mod

            _mod._try_create_issue(
                repo_spec="owner/repo",
                prompt="First line\nSecond line\nThird line",
                hand=hand,
                updates=updates,
                github_token=None,
            )

        call_kwargs = mock_gh.create_issue.call_args[1]
        assert call_kwargs["title"] == "[helping-hands] First line"
        # Body is the full prompt
        assert call_kwargs["body"] == "First line\nSecond line\nThird line"

    def test_exception_does_not_propagate(self) -> None:
        """API errors are swallowed — hand.issue_number stays None."""
        hand = MagicMock()
        hand.issue_number = None
        updates: list[str] = []

        with patch(
            "helping_hands.lib.github.GitHubClient",
            side_effect=RuntimeError("No token"),
        ):
            from helping_hands.server import celery_app as _mod

            # Should not raise
            _mod._try_create_issue(
                repo_spec="owner/repo",
                prompt="test",
                hand=hand,
                updates=updates,
                github_token=None,
            )

        # issue_number should not be set on failure
        assert hand.issue_number is None
        assert any("Failed" in u for u in updates)
