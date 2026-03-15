"""Tests for v188 — DRY redact_credentials, constant-based regex, debug logging.

Validates:
- ``redact_credentials()`` in ``github_url.py`` uses constants in regex
- ``_redact_sensitive()`` in ``github.py`` delegates to ``redact_credentials()``
- ``_finalize_repo_pr()`` catch-all logs debug traceback
- ``_ci_fix_loop()`` catch-all logs debug traceback
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# redact_credentials uses constants in regex
# ---------------------------------------------------------------------------


class TestRedactCredentialsUsesConstants:
    """Verify that ``redact_credentials`` derives its regex from module constants."""

    def test_regex_matches_github_token_user_constant(self) -> None:
        """The regex should redact URLs using the GITHUB_TOKEN_USER constant."""
        from helping_hands.lib.github_url import (
            GITHUB_TOKEN_USER,
            redact_credentials,
        )

        url = f"https://{GITHUB_TOKEN_USER}:secret@github.com/o/r.git"
        result = redact_credentials(url)
        assert "secret" not in result
        assert "***" in result

    def test_regex_matches_github_hostname_constant(self) -> None:
        """The regex should use the GITHUB_HOSTNAME constant for the host portion."""
        from helping_hands.lib.github_url import (
            GITHUB_HOSTNAME,
            redact_credentials,
        )

        url = f"https://x-access-token:secret@{GITHUB_HOSTNAME}/o/r.git"
        result = redact_credentials(url)
        assert "secret" not in result

    def test_non_github_hostname_not_redacted(self) -> None:
        """URLs with a different hostname should NOT be redacted."""
        from helping_hands.lib.github_url import redact_credentials

        url = "https://x-access-token:secret@gitlab.com/o/r.git"
        assert redact_credentials(url) == url

    def test_different_username_not_redacted(self) -> None:
        """URLs with a different username prefix should NOT be redacted."""
        from helping_hands.lib.github_url import redact_credentials

        url = "https://other-user:secret@github.com/o/r.git"
        assert redact_credentials(url) == url

    def test_consistency_with_build_clone_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A URL built by ``build_clone_url`` should be fully redactable."""
        from helping_hands.lib.github_url import build_clone_url, redact_credentials

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        url = build_clone_url("owner/repo", token="ghp_abc123")
        redacted = redact_credentials(url)
        assert "ghp_abc123" not in redacted
        assert "***" in redacted


# ---------------------------------------------------------------------------
# _redact_sensitive delegates to redact_credentials
# ---------------------------------------------------------------------------


class TestRedactSensitiveDelegation:
    """Verify ``_redact_sensitive`` in github.py uses the shared implementation."""

    def test_delegates_to_redact_credentials(self) -> None:
        """_redact_sensitive() should produce the same output as redact_credentials()."""
        from helping_hands.lib.github import _redact_sensitive
        from helping_hands.lib.github_url import redact_credentials

        text = "https://x-access-token:ghp_secret@github.com/owner/repo.git"
        assert _redact_sensitive(text) == redact_credentials(text)

    def test_no_token_passthrough(self) -> None:
        """Text without tokens should pass through unchanged."""
        from helping_hands.lib.github import _redact_sensitive

        text = "https://github.com/owner/repo.git"
        assert _redact_sensitive(text) == text

    def test_redacts_multiple_occurrences(self) -> None:
        """Multiple token URLs should all be redacted."""
        from helping_hands.lib.github import _redact_sensitive

        text = (
            "clone https://x-access-token:aaa@github.com/a/b "
            "push https://x-access-token:bbb@github.com/c/d"
        )
        result = _redact_sensitive(text)
        assert "aaa" not in result
        assert "bbb" not in result

    def test_github_py_no_longer_imports_re(self) -> None:
        """github.py should not import 're' now that redaction is delegated."""
        import inspect

        import helping_hands.lib.github as gh_mod

        source = inspect.getsource(gh_mod)
        # Should not have a standalone 'import re' line (re is no longer needed)
        assert "\nimport re\n" not in source


# ---------------------------------------------------------------------------
# _finalize_repo_pr catch-all debug logging
# ---------------------------------------------------------------------------


class TestFinalizeRepoPrDebugLogging:
    """Verify the catch-all exception handler logs debug traceback."""

    def test_catch_all_logs_debug_with_exc_info(self, repo_index, caplog) -> None:
        """_finalize_repo_pr catch-all should log with exc_info=True."""
        from helping_hands.lib.config import Config
        from helping_hands.lib.hands.v1.hand.base import Hand, HandResponse

        class _Stub(Hand):
            def run(self, prompt: str) -> HandResponse:
                return HandResponse(message=prompt)

            async def stream(self, prompt: str):  # type: ignore[override]
                yield prompt

        config = Config(repo=str(repo_index.root), model="test-model")
        hand = _Stub(config, repo_index)

        from pathlib import Path

        def fake_git_read(_repo_dir: Path, *args: str) -> str:
            if args == ("rev-parse", "--is-inside-work-tree"):
                return "true"
            if args == ("status", "--porcelain"):
                return " M main.py"
            return ""

        with (
            patch.object(Hand, "_run_git_read", side_effect=fake_git_read),
            patch.object(Hand, "_github_repo_from_origin", return_value="owner/repo"),
            patch(
                "helping_hands.lib.github.GitHubClient",
                side_effect=TypeError("unexpected type error"),
            ),
            caplog.at_level(logging.DEBUG),
        ):
            result = hand._finalize_repo_pr(
                backend="test", prompt="task", summary="done"
            )

        assert result["pr_status"] == "error"
        assert any(
            "_finalize_repo_pr unexpected error" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _ci_fix_loop catch-all debug logging
# ---------------------------------------------------------------------------


class TestCiFixLoopDebugLogging:
    """Verify the catch-all exception handler logs debug traceback."""

    def test_catch_all_logs_debug_with_exc_info(self, caplog) -> None:
        """_ci_fix_loop catch-all should log with exc_info=True."""
        from helping_hands.lib.hands.v1.hand.cli.base import _TwoPhaseCLIHand

        class _Stub(_TwoPhaseCLIHand):
            _CLI_LABEL = "stub"
            _BACKEND_NAME = "stub-backend"

            def __init__(self):
                self._interrupt_event = MagicMock()
                self._interrupt_event.is_set.return_value = False
                self._active_process = None
                self.fix_ci = True
                self.ci_check_wait_minutes = 0.001
                self.ci_max_retries = 2
                self.repo_index = MagicMock()
                self.repo_index.root.resolve.return_value = "/fake/repo"
                self.config = MagicMock()
                self.config.model = "test-model"
                self.config.verbose = False
                self.auto_pr = True

        stub = _Stub()

        async def _emit(chunk: str) -> None:
            pass

        meta = {
            "pr_status": "created",
            "pr_branch": "test-branch",
            "pr_number": "1",
            "pr_commit": "abc123",
        }

        with (
            patch.object(
                _TwoPhaseCLIHand,
                "_github_repo_from_origin",
                return_value="owner/repo",
            ),
            patch(
                "helping_hands.lib.github.GitHubClient",
                return_value=MagicMock(),
            ),
            patch.object(
                stub,
                "_poll_ci_checks",
                new=AsyncMock(side_effect=TypeError("unexpected type")),
            ),
            caplog.at_level(logging.DEBUG),
        ):
            result = asyncio.run(
                stub._ci_fix_loop(prompt="p", metadata=meta, emit=_emit)
            )

        assert result["ci_fix_status"] == "error"
        assert any("_ci_fix_loop unexpected error" in r.message for r in caplog.records)
