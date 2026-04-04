"""Tests for remaining edge-case coverage gaps in high-use modules.

Covers:
- ``update_pr`` in ``github.py``: positive-int validation, both-None early
  return, title-only / body-only / both-provided edit paths (lines 542-549).
- ``_LinePrefixEmitter`` in ``cli/base.py``: line buffering, prefix insertion,
  blank-line pass-through, already-prefixed detection, flush (lines 311-328).
- ``_summarize_tool`` Skill branch in ``cli/claude.py``: skill name present
  vs. empty (lines 292-293).
- ``_pr_description_cmd`` Google/Gemini path in ``cli/goose.py``: Google
  provider with/without ``gemini`` binary (line 58).

Part of v354 execution plan.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.github import GitHubClient
from helping_hands.lib.hands.v1.hand.cli.base import _LinePrefixEmitter
from helping_hands.lib.hands.v1.hand.cli.claude import _StreamJsonEmitter
from helping_hands.lib.hands.v1.hand.cli.goose import GooseCLIHand

# ---------------------------------------------------------------------------
# update_pr (github.py, lines 542-549)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _ensure_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GITHUB_TOKEN is set so GitHubClient can be constructed."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")


@pytest.fixture()
def client() -> GitHubClient:
    with patch("helping_hands.lib.github.Github"):
        return GitHubClient()


def _patch_notset():
    """Context manager that injects a sentinel ``NotSet`` into the github module.

    PyGithub's ``NotSet`` may not be importable as ``from github import NotSet``
    in all versions.  We inject a sentinel so ``update_pr``'s deferred import
    resolves without hitting an ``ImportError``.
    """
    import github as gh_mod

    sentinel = object()
    orig = getattr(gh_mod, "NotSet", None)
    gh_mod.NotSet = sentinel  # type: ignore[attr-defined]

    class _Ctx:
        notset = sentinel

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            if orig is None:
                delattr(gh_mod, "NotSet")
            else:
                gh_mod.NotSet = orig  # type: ignore[attr-defined]

    return _Ctx()


class TestUpdatePr:
    """Tests for ``GitHubClient.update_pr`` edge cases."""

    def test_rejects_non_positive_pr_number(self, client: GitHubClient) -> None:
        """``require_positive_int`` raises for zero / negative numbers."""
        with pytest.raises(ValueError, match="PR number"):
            client.update_pr("owner/repo", 0, title="t")
        with pytest.raises(ValueError, match="PR number"):
            client.update_pr("owner/repo", -1, body="b")

    def test_noop_when_both_title_and_body_none(self, client: GitHubClient) -> None:
        """Early return when nothing to update — no API call made."""
        client._gh.get_repo = MagicMock(
            side_effect=AssertionError("should not be called")
        )
        client.update_pr("owner/repo", 1)

    def test_title_only(self, client: GitHubClient) -> None:
        """When only title is provided, body is passed as NotSet sentinel."""
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client._gh.get_repo.return_value = mock_repo

        with _patch_notset() as ctx:
            client.update_pr("owner/repo", 5, title="New Title")

        mock_pr.edit.assert_called_once()
        kw = mock_pr.edit.call_args.kwargs
        assert kw["title"] == "New Title"
        assert kw["body"] is ctx.notset

    def test_body_only(self, client: GitHubClient) -> None:
        """When only body is provided, title is passed as NotSet sentinel."""
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client._gh.get_repo.return_value = mock_repo

        with _patch_notset() as ctx:
            client.update_pr("owner/repo", 5, body="New body")

        mock_pr.edit.assert_called_once()
        kw = mock_pr.edit.call_args.kwargs
        assert kw["title"] is ctx.notset
        assert kw["body"] == "New body"

    def test_both_title_and_body(self, client: GitHubClient) -> None:
        """When both provided, both are passed directly."""
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client._gh.get_repo.return_value = mock_repo

        with _patch_notset():
            client.update_pr("owner/repo", 5, title="T", body="B")

        mock_pr.edit.assert_called_once_with(title="T", body="B")


# ---------------------------------------------------------------------------
# _LinePrefixEmitter (cli/base.py, lines 309-328)
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously using a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestLinePrefixEmitter:
    """Tests for ``_LinePrefixEmitter`` line buffering and prefix logic."""

    @staticmethod
    def _make_emitter(label: str = "test") -> tuple[_LinePrefixEmitter, list]:
        """Create an emitter that collects output into a list."""
        collected: list[str] = []

        async def emit(chunk: str) -> None:
            collected.append(chunk)

        return _LinePrefixEmitter(emit, label), collected

    def test_complete_line_gets_prefix(self) -> None:
        """A complete line (ending with \\n) gets the label prefix."""
        emitter, out = self._make_emitter("srv")
        _run(emitter("hello\n"))
        assert out == ["[srv] hello\n"]

    def test_blank_line_no_prefix(self) -> None:
        """A blank line passes through without a prefix."""
        emitter, out = self._make_emitter("srv")
        _run(emitter("\n"))
        assert out == ["\n"]

    def test_already_prefixed_line_not_double_prefixed(self) -> None:
        """A line already carrying the prefix is forwarded unchanged."""
        emitter, out = self._make_emitter("srv")
        _run(emitter("[srv] existing\n"))
        assert out == ["[srv] existing\n"]

    def test_multi_line_chunk(self) -> None:
        """Multiple lines in one chunk are each prefixed independently."""
        emitter, out = self._make_emitter("x")
        _run(emitter("line1\nline2\n"))
        assert out == ["[x] line1\n", "[x] line2\n"]

    def test_incomplete_line_buffered(self) -> None:
        """Text without a trailing newline is buffered, not emitted."""
        emitter, out = self._make_emitter("x")
        _run(emitter("partial"))
        assert out == []
        # Complete the line
        _run(emitter(" done\n"))
        assert out == ["[x] partial done\n"]

    def test_flush_emits_remaining_buffer(self) -> None:
        """Flush emits buffered content with prefix and clears buffer."""
        emitter, out = self._make_emitter("f")
        _run(emitter("leftover"))
        assert out == []
        _run(emitter.flush())
        assert out == ["[f] leftover"]

    def test_flush_noop_when_empty(self) -> None:
        """Flush with empty buffer emits nothing."""
        emitter, out = self._make_emitter("f")
        _run(emitter.flush())
        assert out == []

    def test_flush_already_prefixed(self) -> None:
        """Flush with already-prefixed buffer forwards unchanged."""
        emitter, out = self._make_emitter("f")
        _run(emitter("[f] tagged"))
        assert out == []
        _run(emitter.flush())
        assert out == ["[f] tagged"]


# ---------------------------------------------------------------------------
# _summarize_tool Skill branch (cli/claude.py, lines 291-293)
# ---------------------------------------------------------------------------


class TestSummarizeToolSkillBranch:
    """Tests for the Skill branch in ``_summarize_tool``."""

    def test_skill_with_name(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("Skill", {"skill": "pdf"})
        assert result == "Skill: pdf"

    def test_skill_empty(self) -> None:
        result = _StreamJsonEmitter._summarize_tool("Skill", {})
        assert result == "Skill"


# ---------------------------------------------------------------------------
# _pr_description_cmd Google/Gemini path (cli/goose.py, line 58)
# ---------------------------------------------------------------------------


class TestGoosePrDescriptionCmdGooglePath:
    """Tests for the Google/Gemini branch of ``_pr_description_cmd``."""

    def test_google_with_gemini_binary(self, make_cli_hand) -> None:
        """Google provider + gemini on PATH delegates to gemini CLI."""
        hand = make_cli_hand(GooseCLIHand, model="google/gemini-2.5-pro")
        with patch("shutil.which", return_value="/usr/bin/gemini"):
            result = hand._pr_description_cmd()
        assert result == ["gemini", "-p"]

    def test_google_without_gemini_binary(self, make_cli_hand) -> None:
        """Google provider but no gemini binary returns None."""
        hand = make_cli_hand(GooseCLIHand, model="google/gemini-2.5-pro")
        with patch("shutil.which", return_value=None):
            result = hand._pr_description_cmd()
        assert result is None
