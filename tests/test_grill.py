"""Tests for the Grill Me interactive session module.

Pure helper functions (_build_system_prompt, _clone_repo, _summarize_tool_use,
_invoke_claude_turn) are testable without the celery extra installed.
The GrillEnabled tests require the server extra (fastapi + celery).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.repo import RepoIndex
from helping_hands.server.grill import (
    _build_system_prompt,
    _clone_repo,
    _get_state,
    _invoke_claude_turn,
    _pop_user_msg,
    _push_ai_msg,
    _set_state,
    _summarize_tool_use,
)


class TestRedisClient:
    """Tests for _redis_client factory."""

    def test_uses_redis_url_env(self) -> None:
        """_redis_client reads REDIS_URL from env and calls redis.from_url."""
        import sys

        from helping_hands.server.grill import _redis_client

        mock_redis_mod = MagicMock()
        with (
            patch.dict("os.environ", {"REDIS_URL": "redis://myhost:1234/2"}),
            patch.dict(sys.modules, {"redis": mock_redis_mod}),
        ):
            _redis_client()
            mock_redis_mod.from_url.assert_called_once_with(
                "redis://myhost:1234/2", decode_responses=True
            )

    def test_default_url(self) -> None:
        """_redis_client uses default URL when REDIS_URL is not set."""
        import sys

        from helping_hands.server.grill import _redis_client

        mock_redis_mod = MagicMock()
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.dict(sys.modules, {"redis": mock_redis_mod}),
        ):
            _redis_client()
            mock_redis_mod.from_url.assert_called_once_with(
                "redis://localhost:6379/0", decode_responses=True
            )


class TestRedisHelpers:
    """Tests for Redis helper functions using a mock Redis client."""

    def _make_redis(self) -> MagicMock:
        """Create a mock Redis client with dict-backed storage."""
        store: dict[str, str] = {}
        r = MagicMock()
        r.set.side_effect = lambda k, v, **kw: store.__setitem__(k, v)
        r.get.side_effect = lambda k: store.get(k)
        r.rpush.side_effect = lambda k, v: store.__setitem__(
            k, store.get(k, "") + "|" + v if store.get(k) else v
        )
        r.lpop.side_effect = lambda k: store.pop(k, None)
        r.expire.return_value = True
        return r

    def test_set_and_get_state(self) -> None:
        """State round-trips through set/get."""
        r = self._make_redis()
        _set_state(r, "sess1", {"status": "active", "turn_count": 3})
        state = _get_state(r, "sess1")
        assert state is not None
        assert state["status"] == "active"
        assert state["turn_count"] == 3

    def test_get_state_missing(self) -> None:
        """Missing session returns None."""
        r = self._make_redis()
        assert _get_state(r, "nonexistent") is None

    def test_push_ai_msg(self) -> None:
        """Push constructs a well-formed message and calls rpush + expire."""
        r = MagicMock()
        _push_ai_msg(r, "sess1", "assistant", "Hello!", msg_type="message")
        r.rpush.assert_called_once()
        key, raw = r.rpush.call_args[0]
        assert key == "grill:sess1:ai_msgs"
        msg = json.loads(raw)
        assert msg["role"] == "assistant"
        assert msg["content"] == "Hello!"
        assert msg["type"] == "message"
        assert "id" in msg
        assert "timestamp" in msg
        r.expire.assert_called_once()

    def test_push_ai_msg_custom_type(self) -> None:
        """msg_type parameter is respected."""
        r = MagicMock()
        _push_ai_msg(r, "sess1", "system", "Error!", msg_type="error")
        raw = r.rpush.call_args[0][1]
        msg = json.loads(raw)
        assert msg["type"] == "error"

    def test_pop_user_msg_present(self) -> None:
        """Pop returns parsed dict when message exists."""
        msg = json.dumps({"content": "yes", "type": "message"})
        r = MagicMock()
        r.lpop.return_value = msg
        result = _pop_user_msg(r, "sess1")
        assert result == {"content": "yes", "type": "message"}
        r.lpop.assert_called_once_with("grill:sess1:user_msgs")

    def test_pop_user_msg_empty(self) -> None:
        """Pop returns None when queue is empty."""
        r = MagicMock()
        r.lpop.return_value = None
        assert _pop_user_msg(r, "sess1") is None


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt."""

    def test_includes_user_prompt(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "Add a widget feature")
        assert "Add a widget feature" in result
        assert "## FINAL PLAN" in result

    def test_includes_readme(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# My Project\nA cool project.")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "test")
        assert "My Project" in result

    def test_includes_file_tree(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("")
        repo_index = RepoIndex.from_path(tmp_path)
        result = _build_system_prompt(repo_index, "test")
        assert "app.py" in result

    def test_no_write_instruction(self, tmp_path: Path) -> None:
        repo_index = RepoIndex(root=tmp_path, files=[], reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "Do NOT write" in result
        assert "Do NOT implement" in result

    def test_readme_fallback_rst(self, tmp_path: Path) -> None:
        """Falls back to README.rst when README.md absent."""
        (tmp_path / "README.rst").write_text("RST README content here")
        repo_index = RepoIndex(root=tmp_path, files=["README.rst"], reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "RST README content here" in result

    def test_readme_truncated(self, tmp_path: Path) -> None:
        """README content is truncated to 8000 chars."""
        (tmp_path / "README.md").write_text("x" * 10000)
        repo_index = RepoIndex(root=tmp_path, files=["README.md"], reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "x" * 8000 in result
        assert "x" * 8001 not in result

    def test_large_file_tree_truncated(self, tmp_path: Path) -> None:
        """File tree is truncated with '... and N more files' for >500 files."""
        files = [f"file_{i:04d}.py" for i in range(600)]
        repo_index = RepoIndex(root=tmp_path, files=files, reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "... and 100 more files" in result

    def test_no_readme(self, tmp_path: Path) -> None:
        """Shows 'No README found' when no README exists."""
        repo_index = RepoIndex(root=tmp_path, files=[], reference_repos=[])
        result = _build_system_prompt(repo_index, "test")
        assert "No README found." in result

    def test_reference_repos_section(self, tmp_path: Path) -> None:
        """Reference repos appear in the system prompt."""
        ref_path = tmp_path / "ref_repo"
        ref_path.mkdir()
        (ref_path / "lib.py").write_text("")
        repo_index = RepoIndex(
            root=tmp_path,
            files=[],
            reference_repos=[("owner/ref-repo", ref_path)],
        )
        result = _build_system_prompt(repo_index, "test")
        assert "owner/ref-repo" in result
        assert "lib.py" in result

    def test_reference_repo_index_failure(self, tmp_path: Path) -> None:
        """Failed reference repo indexing shows fallback message."""
        repo_index = RepoIndex(
            root=tmp_path,
            files=[],
            reference_repos=[("owner/broken", Path("/nonexistent/path"))],
        )
        result = _build_system_prompt(repo_index, "test")
        assert "owner/broken" in result
        assert "failed to index" in result

    def test_readme_oserror(self, tmp_path: Path) -> None:
        """OSError reading README is handled gracefully."""
        readme = tmp_path / "README.md"
        readme.write_text("content")
        repo_index = RepoIndex(root=tmp_path, files=["README.md"], reference_repos=[])
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = _build_system_prompt(repo_index, "test")
        assert "No README found." in result


class TestCloneRepo:
    """Tests for _clone_repo."""

    def test_local_path(self, tmp_path: Path) -> None:
        resolved, cloned_from, tmp_root = _clone_repo(str(tmp_path), None)
        assert resolved == tmp_path
        assert cloned_from is None
        assert tmp_root is None

    def test_invalid_path_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo path"):
            _clone_repo("/nonexistent/path/that/does/not/exist", None)

    def test_remote_clone_success(self, tmp_path: Path) -> None:
        """Successful remote clone returns (dest, spec, tmp_root)."""
        fake_result = MagicMock(returncode=0, stderr="")
        with (
            patch(
                "helping_hands.server.grill.subprocess.run", return_value=fake_result
            ),
            patch(
                "helping_hands.server.grill._repo_tmp_dir", return_value=str(tmp_path)
            ),
            patch(
                "helping_hands.server.grill.mkdtemp", return_value=str(tmp_path / "tmp")
            ),
        ):
            (tmp_path / "tmp" / "repo").mkdir(parents=True)
            _resolved, cloned_from, tmp_root = _clone_repo("owner/repo", "ghp_token")
            assert cloned_from == "owner/repo"
            assert tmp_root == tmp_path / "tmp"

    def test_remote_clone_failure(self, tmp_path: Path) -> None:
        """Failed git clone raises ValueError with redacted stderr."""
        fake_result = MagicMock(returncode=128, stderr="fatal: auth failed")
        with (
            patch(
                "helping_hands.server.grill.subprocess.run", return_value=fake_result
            ),
            patch(
                "helping_hands.server.grill._repo_tmp_dir", return_value=str(tmp_path)
            ),
            patch(
                "helping_hands.server.grill.mkdtemp", return_value=str(tmp_path / "tmp")
            ),
            patch("helping_hands.server.grill.shutil.rmtree"),
        ):
            (tmp_path / "tmp").mkdir(parents=True)
            with pytest.raises(ValueError, match="failed to clone"):
                _clone_repo("owner/repo", None)

    def test_remote_clone_timeout(self, tmp_path: Path) -> None:
        """Clone timeout raises ValueError."""
        with (
            patch(
                "helping_hands.server.grill.subprocess.run",
                side_effect=subprocess.TimeoutExpired("git", 120),
            ),
            patch(
                "helping_hands.server.grill._repo_tmp_dir", return_value=str(tmp_path)
            ),
            patch(
                "helping_hands.server.grill.mkdtemp", return_value=str(tmp_path / "tmp")
            ),
            patch("helping_hands.server.grill.shutil.rmtree"),
        ):
            (tmp_path / "tmp").mkdir(parents=True)
            with pytest.raises(ValueError, match="timed out"):
                _clone_repo("owner/repo", None)


class TestSummarizeToolUse:
    """Tests for _summarize_tool_use."""

    def test_read(self) -> None:
        assert (
            _summarize_tool_use("Read", {"file_path": "src/main.py"})
            == "Read src/main.py"
        )

    def test_grep(self) -> None:
        assert _summarize_tool_use("Grep", {"pattern": "TODO"}) == "Grep /TODO/"

    def test_glob(self) -> None:
        assert _summarize_tool_use("Glob", {"pattern": "**/*.py"}) == "Glob **/*.py"

    def test_unknown(self) -> None:
        assert _summarize_tool_use("Unknown", {}) == "tool: Unknown"

    def test_read_missing_key(self) -> None:
        """Read with missing file_path key returns empty string after name."""
        assert _summarize_tool_use("Read", {}) == "Read "

    def test_grep_empty_pattern(self) -> None:
        """Grep with empty pattern returns slashes around nothing."""
        assert _summarize_tool_use("Grep", {"pattern": ""}) == "Grep //"


class TestInvokeClaudeTurn:
    """Tests for _invoke_claude_turn subprocess interaction."""

    def test_first_turn_uses_session_id(self) -> None:
        """First turn passes --session-id and --system-prompt."""
        result_event = json.dumps({"type": "result", "result": "Hello!"})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ) as popen:
            result = _invoke_claude_turn(
                prompt="Begin the interview.",
                cwd="/tmp/repo",
                claude_session_id="test-uuid",
                is_first_turn=True,
                system_prompt="You are a griller.",
                model="claude-sonnet-4-5",
            )
            assert result == "Hello!"
            cmd = popen.call_args[0][0]
            assert "--session-id" in cmd
            assert "test-uuid" in cmd
            assert "--system-prompt" in cmd
            assert "You are a griller." in cmd
            assert "--model" in cmd
            assert "claude-sonnet-4-5" in cmd

    def test_resume_turn(self) -> None:
        """Non-first turn passes --resume instead of --session-id."""
        result_event = json.dumps({"type": "result", "result": "Next question."})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ) as popen:
            result = _invoke_claude_turn(
                prompt="My answer.",
                cwd="/tmp/repo",
                claude_session_id="test-uuid",
                is_first_turn=False,
            )
            assert result == "Next question."
            cmd = popen.call_args[0][0]
            assert "--resume" in cmd
            assert "test-uuid" in cmd
            assert "--session-id" not in cmd

    def test_claude_not_found(self) -> None:
        """FileNotFoundError from Popen raises RuntimeError."""
        with (
            patch(
                "helping_hands.server.grill.subprocess.Popen",
                side_effect=FileNotFoundError("claude"),
            ),
            pytest.raises(RuntimeError, match="not installed"),
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )

    def test_nonzero_exit_raises(self) -> None:
        """Non-zero exit code from Claude CLI raises RuntimeError."""
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b"rate limit exceeded"
        mock_proc.returncode = 1
        mock_proc.wait.return_value = None

        with (
            patch(
                "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
            ),
            pytest.raises(RuntimeError, match="rate limit exceeded"),
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )

    def test_stdin_oserror(self) -> None:
        """OSError writing stdin kills proc and raises RuntimeError."""
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdin.write.side_effect = OSError("broken pipe")

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            with pytest.raises(RuntimeError, match="Failed to send prompt"):
                _invoke_claude_turn(
                    prompt="test",
                    cwd="/tmp",
                    claude_session_id="uuid",
                    is_first_turn=True,
                )
            mock_proc.kill.assert_called_once()

    def test_stream_text_blocks(self) -> None:
        """Text blocks from assistant events are concatenated."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Part 1. "},
                            {"type": "text", "text": "Part 2."},
                        ]
                    },
                }
            ),
            json.dumps({"type": "result", "result": ""}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            # Empty result text → falls back to joined text_parts
            assert result == "Part 1. \nPart 2."

    def test_on_status_callbacks(self) -> None:
        """on_status receives thinking, tool use, and completion callbacks."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "thinking", "text": "hmm"}]},
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Read",
                                "input": {"file_path": "main.py"},
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "result": "Answer",
                    "total_cost_usd": 0.01,
                    "duration_ms": 5000,
                }
            ),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        status_calls: list[str] = []

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
                on_status=status_calls.append,
            )
            assert result == "Answer"
            assert "Thinking..." in status_calls
            assert any("Read main.py" in s for s in status_calls)
            assert any("5.0s" in s and "$0.0100" in s for s in status_calls)

    def test_github_token_in_env(self) -> None:
        """github_token is passed through to subprocess env."""
        result_event = json.dumps({"type": "result", "result": "ok"})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ) as popen:
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
                github_token="ghp_secret",
            )
            env = popen.call_args[1]["env"]
            assert env["GITHUB_TOKEN"] == "ghp_secret"

    def test_malformed_json_skipped(self) -> None:
        """Non-JSON lines are silently skipped."""
        lines = [
            b"not json\n",
            b"\n",
            b"42\n",  # valid JSON but not a dict
            json.dumps({"type": "result", "result": "ok"}).encode() + b"\n",
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter(lines)
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            assert result == "ok"

    def test_wait_timeout_kills_proc(self) -> None:
        """If proc.wait() times out, proc is killed."""
        result_event = json.dumps({"type": "result", "result": "ok"})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired("claude", 10), None]

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            assert result == "ok"
            mock_proc.kill.assert_called_once()

    def test_thinking_emitted_once(self) -> None:
        """Multiple thinking blocks only emit 'Thinking...' once."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "thinking", "text": "a"}]},
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "thinking", "text": "b"}]},
                }
            ),
            json.dumps({"type": "result", "result": "done"}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        status_calls: list[str] = []
        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
                on_status=status_calls.append,
            )
            assert status_calls.count("Thinking...") == 1

    def test_tool_use_resets_thinking(self) -> None:
        """After tool_use, thinking can emit again."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "thinking", "text": "a"}]},
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Glob",
                                "input": {"pattern": "*.py"},
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "thinking", "text": "b"}]},
                }
            ),
            json.dumps({"type": "result", "result": "done"}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        status_calls: list[str] = []
        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
                on_status=status_calls.append,
            )
            assert status_calls.count("Thinking...") == 2

    def test_non_dict_message_skipped(self) -> None:
        """Assistant event with non-dict message is skipped gracefully."""
        events = [
            json.dumps({"type": "assistant", "message": "not a dict"}),
            json.dumps({"type": "result", "result": "ok"}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            assert result == "ok"

    def test_non_dict_content_block_skipped(self) -> None:
        """Non-dict content blocks in assistant messages are skipped."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": ["just a string", 42]},
                }
            ),
            json.dumps({"type": "result", "result": "ok"}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            assert result == "ok"

    def test_empty_text_block_skipped(self) -> None:
        """Empty text blocks don't contribute to output."""
        events = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": ""},
                            {"type": "text", "text": "real"},
                        ]
                    },
                }
            ),
            json.dumps({"type": "result", "result": ""}),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            assert result == "real"

    def test_result_only_duration(self) -> None:
        """Result event with only duration_ms (no cost) shows duration."""
        events = [
            json.dumps(
                {
                    "type": "result",
                    "result": "ok",
                    "duration_ms": 3000,
                }
            ),
        ]
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([e.encode() + b"\n" for e in events])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        status_calls: list[str] = []
        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
                on_status=status_calls.append,
            )
            assert any("3.0s" in s for s in status_calls)

    def test_nonzero_exit_empty_stderr(self) -> None:
        """Non-zero exit with empty stderr shows exit code."""
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 42
        mock_proc.wait.return_value = None

        with (
            patch(
                "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
            ),
            pytest.raises(RuntimeError, match="exit code 42"),
        ):
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )

    def test_no_model_omits_flag(self) -> None:
        """When model is None, --model flag is not passed."""
        result_event = json.dumps({"type": "result", "result": "ok"})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ) as popen:
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            cmd = popen.call_args[0][0]
            assert "--model" not in cmd

    def test_read_only_tools(self) -> None:
        """Verify the command includes read-only tool restrictions."""
        result_event = json.dumps({"type": "result", "result": "ok"})
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = iter([result_event.encode() + b"\n"])
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ) as popen:
            _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            cmd = popen.call_args[0][0]
            assert "--allowedTools" in cmd
            assert "Read,Glob,Grep" in cmd
            assert "--disallowedTools" in cmd


class TestInvokeClaudeTurnStreamError:
    """Tests for _invoke_claude_turn stream error handling."""

    def test_stream_read_exception_logged(self) -> None:
        """Exception during stdout iteration is logged, not raised."""

        def _exploding_iter():
            yield (
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": "partial"}]},
                    }
                ).encode()
                + b"\n"
            )
            raise OSError("Connection reset")

        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = _exploding_iter()
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with patch(
            "helping_hands.server.grill.subprocess.Popen", return_value=mock_proc
        ):
            result = _invoke_claude_turn(
                prompt="test",
                cwd="/tmp",
                claude_session_id="uuid",
                is_first_turn=True,
            )
            # Falls back to text_parts since result_text is empty
            assert result == "partial"


class TestGrillEnabled:
    """Tests for the grill feature flag in app.py."""

    def test_disabled_by_default(self) -> None:
        pytest.importorskip("fastapi", reason="server extra not installed")
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {}, clear=True):
            assert _grill_enabled() is False

    def test_enabled_when_set(self) -> None:
        pytest.importorskip("fastapi", reason="server extra not installed")
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {"GRILL_ME_ENABLED": "1"}):
            assert _grill_enabled() is True

    def test_disabled_when_zero(self) -> None:
        pytest.importorskip("fastapi", reason="server extra not installed")
        from helping_hands.server.app import _grill_enabled

        with patch.dict("os.environ", {"GRILL_ME_ENABLED": "0"}):
            assert _grill_enabled() is False
