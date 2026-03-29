"""Tests for v221: DRY git clone helper, auth status line, and validation wrapper.

_run_git_clone() is the single subprocess callsite that clones repos; if it
stops surfacing CalledProcessError or FileNotFoundError the CLI swallows clone
failures silently and hands a broken workspace to the hand.

_validate_or_exit() is the CLI's early-exit guard — regressions cause invalid
arguments to propagate into hand initialisation rather than producing a clean
user-facing error.

_auth_status_line() emits the auth banner printed at the start of every
iterative hand stream; verifying it uses _REPO_SPEC_PATTERN ensures pattern
changes are picked up consistently across the CLI and the iterative base.
"""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.cli.main import (
    _REPO_SPEC_PATTERN,
    _run_git_clone,
    _validate_or_exit,
    main,
)
from helping_hands.lib.hands.v1.hand.iterative import _BasicIterativeHand

# ---------------------------------------------------------------------------
# _run_git_clone — behaviour
# ---------------------------------------------------------------------------


class TestRunGitClone:
    """Verify _run_git_clone delegates to subprocess correctly."""

    def test_success_returns_completed_process(self, tmp_path: Path) -> None:
        dest = tmp_path / "repo"
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with patch("helping_hands.cli.main.subprocess.run", return_value=mock_result):
            result = _run_git_clone("https://github.com/o/r.git", dest, label="o/r")
        assert result.returncode == 0

    def test_timeout_raises_value_error(self, tmp_path: Path) -> None:
        dest = tmp_path / "repo"
        with (
            patch(
                "helping_hands.cli.main.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30),
            ),
            pytest.raises(ValueError, match="timed out"),
        ):
            _run_git_clone("https://x.com/r.git", dest, label="o/r")

    def test_nonzero_exit_raises_value_error(self, tmp_path: Path) -> None:
        dest = tmp_path / "repo"
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="fatal: repo not found"
        )
        with (
            patch("helping_hands.cli.main.subprocess.run", return_value=mock_result),
            pytest.raises(ValueError, match="failed to clone"),
        ):
            _run_git_clone("https://x.com/r.git", dest, label="o/r")

    def test_empty_stderr_uses_fallback_message(self, tmp_path: Path) -> None:
        dest = tmp_path / "repo"
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        with (
            patch("helping_hands.cli.main.subprocess.run", return_value=mock_result),
            pytest.raises(ValueError, match="unknown git clone error"),
        ):
            _run_git_clone("https://x.com/r.git", dest, label="o/r")

    def test_label_appears_in_error_messages(self, tmp_path: Path) -> None:
        dest = tmp_path / "repo"
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="err"
        )
        with (
            patch("helping_hands.cli.main.subprocess.run", return_value=mock_result),
            pytest.raises(ValueError, match="my-org/my-repo"),
        ):
            _run_git_clone("https://x.com/r.git", dest, label="my-org/my-repo")

    def test_is_function(self) -> None:
        assert callable(_run_git_clone)

    def test_has_docstring(self) -> None:
        assert _run_git_clone.__doc__


# ---------------------------------------------------------------------------
# _validate_or_exit — behaviour
# ---------------------------------------------------------------------------


class TestValidateOrExit:
    """Verify _validate_or_exit wraps validation and exits on error."""

    def test_returns_result_on_success(self) -> None:
        result = _validate_or_exit(int, "42")
        assert result == 42

    def test_exits_on_value_error(self) -> None:
        def _bad() -> None:
            raise ValueError("boom")

        with pytest.raises(SystemExit) as exc_info:
            _validate_or_exit(_bad)
        assert exc_info.value.code == 1

    def test_passes_args_through(self) -> None:
        def _adder(a: int, b: int) -> int:
            return a + b

        assert _validate_or_exit(_adder, 3, 7) == 10

    def test_passes_kwargs_through(self) -> None:
        def _greet(*, name: str) -> str:
            return f"hi {name}"

        assert _validate_or_exit(_greet, name="world") == "hi world"

    def test_prints_error_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        def _fail() -> None:
            raise ValueError("test message")

        with pytest.raises(SystemExit):
            _validate_or_exit(_fail)
        assert "test message" in capsys.readouterr().err

    def test_is_function(self) -> None:
        assert callable(_validate_or_exit)

    def test_has_docstring(self) -> None:
        assert _validate_or_exit.__doc__


# ---------------------------------------------------------------------------
# _REPO_SPEC_PATTERN — constant
# ---------------------------------------------------------------------------


class TestRepoSpecPattern:
    """Verify _REPO_SPEC_PATTERN matches expected owner/repo strings."""

    @pytest.mark.parametrize(
        "spec",
        ["owner/repo", "my-org/my-repo", "a.b/c_d", "X/Y"],
    )
    def test_matches_valid_specs(self, spec: str) -> None:
        assert re.fullmatch(_REPO_SPEC_PATTERN, spec)

    @pytest.mark.parametrize(
        "spec",
        ["owner", "/repo", "a/b/c", "owner/", ""],
    )
    def test_rejects_invalid_specs(self, spec: str) -> None:
        assert not re.fullmatch(_REPO_SPEC_PATTERN, spec)


# ---------------------------------------------------------------------------
# _auth_status_line — behaviour
# ---------------------------------------------------------------------------


class _ConcreteIterativeHand(_BasicIterativeHand):
    """Minimal concrete subclass for testing instance methods."""

    _BACKEND_NAME = "test-backend"

    def run(self, prompt: str, **kwargs):  # type: ignore[override]
        raise NotImplementedError

    async def stream(self, prompt: str, **kwargs):  # type: ignore[override]
        raise NotImplementedError


class TestAuthStatusLine:
    """Verify _auth_status_line returns correct auth banner."""

    def _make_hand(
        self, *, env_var: str = "TEST_API_KEY", provider_name: str = "test"
    ) -> _ConcreteIterativeHand:
        """Create a minimal hand with mocked internals."""
        hand = object.__new__(_ConcreteIterativeHand)
        hand._hand_model = MagicMock()
        hand._hand_model.provider.api_key_env_var = env_var
        hand._hand_model.provider.name = provider_name
        return hand

    def test_returns_set_when_env_var_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-123")
        hand = self._make_hand()
        line = hand._auth_status_line()
        assert "(set)" in line
        assert "TEST_API_KEY" in line

    def test_returns_not_set_when_env_var_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        hand = self._make_hand()
        line = hand._auth_status_line()
        assert "(not set)" in line

    def test_returns_not_set_when_env_var_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_API_KEY", "   ")
        hand = self._make_hand()
        line = hand._auth_status_line()
        assert "(not set)" in line

    def test_includes_backend_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        hand = self._make_hand()
        assert "[test-backend]" in hand._auth_status_line()

    def test_includes_provider_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        hand = self._make_hand(provider_name="openai")
        assert "provider=openai" in hand._auth_status_line()

    def test_newline_terminated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_API_KEY", raising=False)
        hand = self._make_hand()
        assert hand._auth_status_line().endswith("\n")

    def test_is_method(self) -> None:
        assert hasattr(_BasicIterativeHand, "_auth_status_line")
        assert callable(_BasicIterativeHand._auth_status_line)

    def test_has_docstring(self) -> None:
        assert _BasicIterativeHand._auth_status_line.__doc__


# ---------------------------------------------------------------------------
# Source consistency — stream methods use _auth_status_line
# ---------------------------------------------------------------------------

_ITERATIVE_SRC = Path(inspect.getfile(_BasicIterativeHand)).read_text()


class TestSourceConsistency:
    """Verify stream methods delegate to _auth_status_line."""

    def test_no_inline_auth_label_in_stream_methods(self) -> None:
        """Stream methods should not reference _AUTH_PRESENT_LABEL directly."""
        tree = ast.parse(_ITERATIVE_SRC)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "stream":
                body_src = ast.get_source_segment(_ITERATIVE_SRC, node)
                assert body_src is not None
                assert "_AUTH_PRESENT_LABEL" not in body_src, (
                    "stream() should use _auth_status_line() instead of "
                    "inline _AUTH_PRESENT_LABEL"
                )
                assert "_AUTH_ABSENT_LABEL" not in body_src

    def test_stream_methods_call_auth_status_line(self) -> None:
        """Stream methods should call self._auth_status_line()."""
        tree = ast.parse(_ITERATIVE_SRC)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "stream":
                body_src = ast.get_source_segment(_ITERATIVE_SRC, node)
                assert body_src is not None
                assert "_auth_status_line" in body_src

    def test_resolve_repo_uses_run_git_clone(self) -> None:
        """_resolve_repo_path should delegate to _run_git_clone."""
        cli_src = Path(inspect.getfile(main)).read_text()
        tree = ast.parse(cli_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_repo_path":
                body_src = ast.get_source_segment(cli_src, node)
                assert body_src is not None
                assert "_run_git_clone" in body_src

    def test_clone_reference_repos_uses_run_git_clone(self) -> None:
        """_clone_reference_repos should delegate to _run_git_clone."""
        cli_src = Path(inspect.getfile(main)).read_text()
        tree = ast.parse(cli_src)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_clone_reference_repos"
            ):
                body_src = ast.get_source_segment(cli_src, node)
                assert body_src is not None
                assert "_run_git_clone" in body_src

    def test_main_uses_validate_or_exit(self) -> None:
        """main() should use _validate_or_exit for validation."""
        cli_src = Path(inspect.getfile(main)).read_text()
        tree = ast.parse(cli_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                body_src = ast.get_source_segment(cli_src, node)
                assert body_src is not None
                assert "_validate_or_exit" in body_src

    def test_resolve_repo_uses_repo_spec_pattern(self) -> None:
        """_resolve_repo_path should use _REPO_SPEC_PATTERN constant."""
        cli_src = Path(inspect.getfile(main)).read_text()
        tree = ast.parse(cli_src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_repo_path":
                body_src = ast.get_source_segment(cli_src, node)
                assert body_src is not None
                assert "_REPO_SPEC_PATTERN" in body_src
