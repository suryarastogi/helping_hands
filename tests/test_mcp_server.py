"""Tests for helping_hands.server.mcp_server."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.server.mcp_server import (
    _indexed_repos,
    get_config,
    get_task_status,
    index_repo,
    list_indexed_repos,
    mkdir,
    path_exists,
    read_file,
    run_bash_script,
    run_python_code,
    run_python_script,
    web_browse,
    web_search,
    write_file,
)

# ---------------------------------------------------------------------------
# index_repo
# ---------------------------------------------------------------------------


class TestIndexRepo:
    def test_indexes_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1")
        (tmp_path / "b.py").write_text("y = 2")

        result = index_repo(str(tmp_path))

        assert result["file_count"] == 2
        assert "a.py" in result["files"]
        assert "b.py" in result["files"]
        assert result["root"] == str(tmp_path.resolve())

    def test_stores_in_cache(self, tmp_path: Path) -> None:
        (tmp_path / "c.py").write_text("")
        _indexed_repos.clear()

        index_repo(str(tmp_path))

        assert str(tmp_path.resolve()) in _indexed_repos

    def test_raises_on_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            index_repo(str(tmp_path / "nonexistent"))


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------


class TestReadFile:
    def test_reads_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world")

        content = read_file(str(tmp_path), "hello.txt")
        assert content == "hello world"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_path), "nope.txt")

    def test_rejects_path_escape(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            read_file(str(tmp_path), "../outside.txt")

    def test_respects_max_chars(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("abcdef")
        content = read_file(str(tmp_path), "hello.txt", max_chars=3)
        assert content == "abc"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------


class TestWriteFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        result = write_file(str(tmp_path), "nested/hello.txt", "hello world")
        assert result["path"] == "nested/hello.txt"
        assert result["bytes"] == len(b"hello world")
        assert (tmp_path / "nested" / "hello.txt").read_text(encoding="utf-8") == (
            "hello world"
        )

    def test_rejects_invalid_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            write_file(str(tmp_path), "../outside.txt", "x")


# ---------------------------------------------------------------------------
# mkdir
# ---------------------------------------------------------------------------


class TestMkdir:
    def test_creates_directory(self, tmp_path: Path) -> None:
        result = mkdir(str(tmp_path), "a/b/c")
        assert result["path"] == "a/b/c"
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_rejects_invalid_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            mkdir(str(tmp_path), "../outside")


# ---------------------------------------------------------------------------
# path_exists
# ---------------------------------------------------------------------------


class TestPathExists:
    def test_true_for_existing_path(self, tmp_path: Path) -> None:
        (tmp_path / "exists.txt").write_text("x")
        assert path_exists(str(tmp_path), "exists.txt") is True

    def test_false_for_missing_path(self, tmp_path: Path) -> None:
        assert path_exists(str(tmp_path), "missing.txt") is False

    def test_false_for_invalid_relative_path(self, tmp_path: Path) -> None:
        assert path_exists(str(tmp_path), "../outside.txt") is False


# ---------------------------------------------------------------------------
# command tools
# ---------------------------------------------------------------------------


class TestCommandTools:
    @patch("helping_hands.server.mcp_server.exec_tools.run_python_code")
    def test_run_python_code(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["uv", "run", "--python", "3.13", "python", "-c", "print('ok')"],
            cwd=str(tmp_path.resolve()),
            exit_code=0,
            stdout="ok\n",
            stderr="",
            timed_out=False,
        )

        result = run_python_code(
            str(tmp_path),
            code="print('ok')",
            python_version="3.13",
            args=["--flag"],
            timeout_s=45,
            cwd=None,
        )
        assert result["success"] is True
        assert result["stdout"] == "ok\n"
        mock_run.assert_called_once()

    @patch("helping_hands.server.mcp_server.exec_tools.run_python_script")
    def test_run_python_script(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["uv", "run", "--python", "3.13", "python", "scripts/tool.py"],
            cwd=str(tmp_path.resolve()),
            exit_code=0,
            stdout="script-ok\n",
            stderr="",
            timed_out=False,
        )

        result = run_python_script(
            str(tmp_path),
            script_path="scripts/tool.py",
        )
        assert result["success"] is True
        assert result["stdout"] == "script-ok\n"
        mock_run.assert_called_once()

    @patch("helping_hands.server.mcp_server.exec_tools.run_bash_script")
    def test_run_bash_script(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["bash", "scripts/tool.sh"],
            cwd=str(tmp_path.resolve()),
            exit_code=0,
            stdout="bash-ok\n",
            stderr="",
            timed_out=False,
        )

        result = run_bash_script(
            str(tmp_path),
            script_path="scripts/tool.sh",
            args=["--x"],
        )
        assert result["success"] is True
        assert result["stdout"] == "bash-ok\n"
        mock_run.assert_called_once()


class TestWebTools:
    @patch("helping_hands.server.mcp_server.web_tools.search_web")
    def test_web_search(self, mock_search: MagicMock) -> None:
        from helping_hands.lib.meta.tools.web import WebSearchItem, WebSearchResult

        mock_search.return_value = WebSearchResult(
            query="python",
            results=[
                WebSearchItem(
                    title="Python",
                    url="https://example.com/python",
                    snippet="language",
                )
            ],
        )

        result = web_search("python", max_results=1, timeout_s=5)

        assert result["query"] == "python"
        assert result["results"][0]["url"] == "https://example.com/python"
        mock_search.assert_called_once()

    @patch("helping_hands.server.mcp_server.web_tools.browse_url")
    def test_web_browse(self, mock_browse: MagicMock) -> None:
        from helping_hands.lib.meta.tools.web import WebBrowseResult

        mock_browse.return_value = WebBrowseResult(
            url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content="hello",
            truncated=False,
        )

        result = web_browse("https://example.com", max_chars=100, timeout_s=5)

        assert result["url"] == "https://example.com"
        assert result["content"] == "hello"
        mock_browse.assert_called_once()


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_returns_defaults(self) -> None:
        result = get_config()
        assert result["model"] == "default"
        assert result["verbose"] is False
        assert result["enable_execution"] is False
        assert result["enable_web"] is False

    def test_picks_up_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HELPING_HANDS_MODEL", "gpt-test")
        result = get_config()
        assert result["model"] == "gpt-test"


# ---------------------------------------------------------------------------
# build_feature (enqueues via Celery — mock it)
# ---------------------------------------------------------------------------


def _mock_celery_module() -> MagicMock:
    """Create a mock that stands in for helping_hands.server.celery_app."""
    mock_mod = MagicMock()
    return mock_mod


class TestBuildFeature:
    def test_enqueues_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_task = MagicMock()
        fake_task.id = "task-abc-123"
        mock_mod.build_feature.delay.return_value = fake_task

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature("/tmp/repo", "add tests")

        assert result["task_id"] == "task-abc-123"
        assert result["status"] == "queued"
        assert result["backend"] == "codexcli"
        assert (
            mock_mod.build_feature.delay.call_args.kwargs["enable_execution"] is False
        )
        assert mock_mod.build_feature.delay.call_args.kwargs["enable_web"] is False
        assert mock_mod.build_feature.delay.call_args.kwargs["skills"] == []

    def test_enqueues_task_with_skills(self) -> None:
        mock_mod = _mock_celery_module()
        fake_task = MagicMock()
        fake_task.id = "task-xyz-999"
        mock_mod.build_feature.delay.return_value = fake_task

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature

            result = build_feature(
                "/tmp/repo",
                "search docs",
                skills=["execution", "web"],
            )

        assert result["task_id"] == "task-xyz-999"
        assert result["status"] == "queued"
        assert mock_mod.build_feature.delay.call_args.kwargs["skills"] == [
            "execution",
            "web",
        ]


# ---------------------------------------------------------------------------
# get_task_status (reads Celery result — mock it)
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    def test_pending_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "PENDING"
        fake_result.ready.return_value = False
        fake_result.info = None
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "PENDING"
        assert result["result"] is None

    def test_progress_task_returns_update_meta(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "PROGRESS"
        fake_result.ready.return_value = False
        fake_result.info = {"stage": "running", "updates": ["step 1"]}
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "PROGRESS"
        assert result["result"] == {"stage": "running", "updates": ["step 1"]}

    def test_completed_task(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "SUCCESS"
        fake_result.ready.return_value = True
        fake_result.result = {"greeting": "done"}
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "SUCCESS"
        assert result["result"] == {"greeting": "done"}

    def test_failed_task_normalizes_exception_result(self) -> None:
        mock_mod = _mock_celery_module()
        fake_result = MagicMock()
        fake_result.status = "FAILURE"
        fake_result.ready.return_value = True
        fake_result.result = RuntimeError("boom")
        mock_mod.build_feature.AsyncResult.return_value = fake_result

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            result = get_task_status("task-abc-123")

        assert result["status"] == "FAILURE"
        assert result["result"] == {
            "error": "boom",
            "error_type": "RuntimeError",
            "status": "FAILURE",
        }


# ---------------------------------------------------------------------------
# list_indexed_repos (resource)
# ---------------------------------------------------------------------------


class TestListIndexedRepos:
    def test_empty(self) -> None:
        _indexed_repos.clear()
        text = list_indexed_repos()
        assert "No repositories" in text

    def test_with_repos(self, tmp_path: Path) -> None:
        _indexed_repos.clear()
        (tmp_path / "f.py").write_text("")
        index_repo(str(tmp_path))

        text = list_indexed_repos()
        assert str(tmp_path.resolve()) in text
        assert "1 files" in text

    def test_multiple_repos(self, tmp_path: Path) -> None:
        _indexed_repos.clear()
        repo_a = tmp_path / "repo_a"
        repo_a.mkdir()
        (repo_a / "x.py").write_text("")
        repo_b = tmp_path / "repo_b"
        repo_b.mkdir()
        (repo_b / "y.py").write_text("")
        (repo_b / "z.py").write_text("")

        index_repo(str(repo_a))
        index_repo(str(repo_b))

        text = list_indexed_repos()
        assert str(repo_a.resolve()) in text
        assert str(repo_b.resolve()) in text
        assert "1 files" in text
        assert "2 files" in text


# ---------------------------------------------------------------------------
# _repo_root helper
# ---------------------------------------------------------------------------


class TestRepoRoot:
    def test_raises_on_missing_directory(self) -> None:
        from helping_hands.server.mcp_server import _repo_root

        with pytest.raises(FileNotFoundError, match="not found"):
            _repo_root("/nonexistent/path/to/repo")

    def test_resolves_valid_directory(self, tmp_path: Path) -> None:
        from helping_hands.server.mcp_server import _repo_root

        result = _repo_root(str(tmp_path))
        assert result == tmp_path.resolve()


# ---------------------------------------------------------------------------
# _command_result_to_dict helper
# ---------------------------------------------------------------------------


class TestCommandResultToDict:
    def test_converts_all_fields(self) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult
        from helping_hands.server.mcp_server import _command_result_to_dict

        cr = CommandResult(
            command=["echo", "hi"],
            cwd="/tmp",
            exit_code=1,
            stdout="hi\n",
            stderr="err\n",
            timed_out=True,
        )
        d = _command_result_to_dict(cr)
        assert d == {
            "success": False,
            "command": ["echo", "hi"],
            "cwd": "/tmp",
            "exit_code": 1,
            "timed_out": True,
            "stdout": "hi\n",
            "stderr": "err\n",
        }

    def test_success_true_on_zero_exit(self) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult
        from helping_hands.server.mcp_server import _command_result_to_dict

        cr = CommandResult(
            command=["true"],
            cwd="/tmp",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
        )
        d = _command_result_to_dict(cr)
        assert d["success"] is True


# ---------------------------------------------------------------------------
# read_file edge cases
# ---------------------------------------------------------------------------


class TestReadFileEdgeCases:
    def test_raises_is_a_directory_error(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        with pytest.raises(IsADirectoryError):
            read_file(str(tmp_path), "subdir")

    def test_raises_unicode_error_for_binary(self, tmp_path: Path) -> None:
        (tmp_path / "binary.bin").write_bytes(b"\x80\x81\x82\x83\xff\xfe")
        with pytest.raises(UnicodeError):
            read_file(str(tmp_path), "binary.bin")


# ---------------------------------------------------------------------------
# command tools edge cases
# ---------------------------------------------------------------------------


class TestCommandToolEdgeCases:
    @patch("helping_hands.server.mcp_server.exec_tools.run_python_code")
    def test_run_python_code_nonzero_exit(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["python", "-c", "exit(1)"],
            cwd=str(tmp_path.resolve()),
            exit_code=1,
            stdout="",
            stderr="SyntaxError: oops",
            timed_out=False,
        )

        result = run_python_code(str(tmp_path), code="exit(1)")
        assert result["success"] is False
        assert result["exit_code"] == 1
        assert result["stderr"] == "SyntaxError: oops"

    @patch("helping_hands.server.mcp_server.exec_tools.run_python_code")
    def test_run_python_code_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["python", "-c", "while True: pass"],
            cwd=str(tmp_path.resolve()),
            exit_code=-9,
            stdout="",
            stderr="",
            timed_out=True,
        )

        result = run_python_code(str(tmp_path), code="while True: pass", timeout_s=1)
        assert result["success"] is False
        assert result["timed_out"] is True

    @patch("helping_hands.server.mcp_server.exec_tools.run_bash_script")
    def test_run_bash_script_inline(self, mock_run: MagicMock, tmp_path: Path) -> None:
        from helping_hands.lib.meta.tools.command import CommandResult

        mock_run.return_value = CommandResult(
            command=["bash", "-c", "echo hi"],
            cwd=str(tmp_path.resolve()),
            exit_code=0,
            stdout="hi\n",
            stderr="",
            timed_out=False,
        )

        result = run_bash_script(str(tmp_path), inline_script="echo hi")
        assert result["success"] is True
        assert result["stdout"] == "hi\n"
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("inline_script") == "echo hi"


# ---------------------------------------------------------------------------
# web tools edge cases
# ---------------------------------------------------------------------------


class TestWebToolEdgeCases:
    @patch("helping_hands.server.mcp_server.web_tools.search_web")
    def test_web_search_empty_results(self, mock_search: MagicMock) -> None:
        from helping_hands.lib.meta.tools.web import WebSearchResult

        mock_search.return_value = WebSearchResult(query="nothing", results=[])

        result = web_search("nothing")
        assert result["query"] == "nothing"
        assert result["results"] == []

    @patch("helping_hands.server.mcp_server.web_tools.browse_url")
    def test_web_browse_truncated(self, mock_browse: MagicMock) -> None:
        from helping_hands.lib.meta.tools.web import WebBrowseResult

        mock_browse.return_value = WebBrowseResult(
            url="https://example.com/long",
            final_url="https://example.com/long",
            status_code=200,
            content="a" * 100,
            truncated=True,
        )

        result = web_browse("https://example.com/long", max_chars=100)
        assert result["truncated"] is True
        assert len(result["content"]) == 100

    @patch("helping_hands.server.mcp_server.web_tools.browse_url")
    def test_web_browse_redirect(self, mock_browse: MagicMock) -> None:
        from helping_hands.lib.meta.tools.web import WebBrowseResult

        mock_browse.return_value = WebBrowseResult(
            url="https://old.example.com",
            final_url="https://new.example.com",
            status_code=200,
            content="redirected",
            truncated=False,
        )

        result = web_browse("https://old.example.com")
        assert result["url"] == "https://old.example.com"
        assert result["final_url"] == "https://new.example.com"


# ---------------------------------------------------------------------------
# build_feature edge cases
# ---------------------------------------------------------------------------


class TestBuildFeatureEdgeCases:
    def test_invalid_skill_names_rejected(self) -> None:
        mock_mod = _mock_celery_module()
        fake_task = MagicMock()
        fake_task.id = "task-bad-skill"
        mock_mod.build_feature.delay.return_value = fake_task

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature as bf

            with pytest.raises(ValueError, match=r"[Uu]nknown"):
                bf("/tmp/repo", "test", skills=["nonexistent_skill_xyz"])

    def test_custom_backend_and_params(self) -> None:
        mock_mod = _mock_celery_module()
        fake_task = MagicMock()
        fake_task.id = "task-custom"
        mock_mod.build_feature.delay.return_value = fake_task

        with patch.dict("sys.modules", {"helping_hands.server.celery_app": mock_mod}):
            from helping_hands.server.mcp_server import build_feature as bf

            result = bf(
                "/tmp/repo",
                "implement feature",
                backend="geminicli",
                model="gemini-2.0-flash",
                max_iterations=10,
                no_pr=True,
                enable_execution=True,
                enable_web=True,
                pr_number=42,
            )

        assert result["backend"] == "geminicli"
        call_kwargs = mock_mod.build_feature.delay.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.0-flash"
        assert call_kwargs["max_iterations"] == 10
        assert call_kwargs["no_pr"] is True
        assert call_kwargs["enable_execution"] is True
        assert call_kwargs["enable_web"] is True
        assert call_kwargs["pr_number"] == 42


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


class TestMain:
    @patch("helping_hands.server.mcp_server.mcp")
    def test_stdio_transport(self, mock_mcp: MagicMock) -> None:
        import sys

        from helping_hands.server.mcp_server import main

        original_argv = sys.argv
        try:
            sys.argv = ["helping-hands-mcp"]
            main()
            mock_mcp.run.assert_called_once_with(transport="stdio")
        finally:
            sys.argv = original_argv

    @patch("helping_hands.server.mcp_server.mcp")
    def test_http_transport(self, mock_mcp: MagicMock) -> None:
        import sys

        from helping_hands.server.mcp_server import main

        original_argv = sys.argv
        try:
            sys.argv = ["helping-hands-mcp", "--http"]
            main()
            mock_mcp.run.assert_called_once_with(transport="streamable-http")
        finally:
            sys.argv = original_argv
