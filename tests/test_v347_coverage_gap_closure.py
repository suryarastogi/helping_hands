"""Tests closing small coverage gaps across CLI hands, _LinePrefixEmitter, and github.

v347: Push overall coverage past the 75% CI gate by covering:
- ``_LinePrefixEmitter`` (``cli/base.py`` lines 311-328) -- async line
  buffering, prefix injection, blank-line passthrough, flush behaviour
- ``opencode.py`` ``_pr_description_cmd`` when opencode is on PATH (lines 35-37)
- ``devin.py`` ``_pr_description_cmd`` when devin is on PATH (lines 38-40)
  and ``_pr_description_prompt_as_arg`` (line 44)
- ``github.py`` ``update_pr`` title/body/both update paths (lines 542-549)
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _LinePrefixEmitter
from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand
from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

# ---------------------------------------------------------------------------
# _LinePrefixEmitter
# ---------------------------------------------------------------------------


class TestLinePrefixEmitter:
    """Cover all branches in _LinePrefixEmitter.__call__ and flush."""

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def test_prefixes_plain_line(self) -> None:
        """A non-blank, non-prefixed complete line gets prefixed."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "test")
        self._run(emitter("hello world\n"))
        assert emitted == ["[test] hello world\n"]

    def test_blank_line_no_prefix(self) -> None:
        """Blank lines pass through as bare newlines (no prefix)."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "lbl")
        self._run(emitter("\n"))
        assert emitted == ["\n"]

    def test_whitespace_only_line_no_prefix(self) -> None:
        """A line containing only whitespace is treated as blank."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "lbl")
        self._run(emitter("   \n"))
        assert emitted == ["\n"]

    def test_already_prefixed_line_not_double_prefixed(self) -> None:
        """A line already carrying the [label] prefix is forwarded as-is."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "cli")
        self._run(emitter("[cli] already tagged\n"))
        assert emitted == ["[cli] already tagged\n"]

    def test_buffering_across_chunks(self) -> None:
        """Incomplete lines are buffered until a newline arrives."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "x")
        self._run(emitter("hel"))
        assert emitted == []  # no newline yet
        self._run(emitter("lo\n"))
        assert emitted == ["[x] hello\n"]

    def test_multiple_lines_in_single_chunk(self) -> None:
        """Multiple newlines in a single chunk emit multiple prefixed lines."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "m")
        self._run(emitter("a\nb\n"))
        assert emitted == ["[m] a\n", "[m] b\n"]

    def test_flush_unprefixed_remainder(self) -> None:
        """flush() emits remaining un-prefixed buffered text."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "f")
        self._run(emitter("leftover"))
        assert emitted == []
        self._run(emitter.flush())
        assert emitted == ["[f] leftover"]

    def test_flush_already_prefixed_remainder(self) -> None:
        """flush() emits already-prefixed buffered text without re-prefixing."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "f")
        emitter._buffer = "[f] tagged"
        self._run(emitter.flush())
        assert emitted == ["[f] tagged"]

    def test_flush_empty_buffer_noop(self) -> None:
        """flush() with empty/whitespace-only buffer does not emit."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "f")
        self._run(emitter.flush())
        assert emitted == []

    def test_flush_whitespace_only_buffer_noop(self) -> None:
        """flush() with whitespace-only buffer does not emit."""
        emitted: list[str] = []

        async def _emit(s: str) -> None:
            emitted.append(s)

        emitter = _LinePrefixEmitter(_emit, "f")
        emitter._buffer = "   "
        self._run(emitter.flush())
        assert emitted == []


# ---------------------------------------------------------------------------
# OpenCodeCLIHand._pr_description_cmd
# ---------------------------------------------------------------------------


class TestOpenCodePrDescriptionCmd:
    """Cover the opencode-on-PATH branch in _pr_description_cmd."""

    def test_returns_command_when_opencode_on_path(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-6")
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/opencode")
        assert hand._pr_description_cmd() == ["opencode", "run"]

    def test_returns_none_when_opencode_missing(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-6")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        assert hand._pr_description_cmd() is None


# ---------------------------------------------------------------------------
# DevinCLIHand._pr_description_cmd and _pr_description_prompt_as_arg
# ---------------------------------------------------------------------------


class TestDevinPrDescriptionCmd:
    """Cover the devin-on-PATH branch in _pr_description_cmd."""

    def test_returns_command_when_devin_on_path(
        self, make_cli_hand, monkeypatch
    ) -> None:
        hand = make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/devin")
        assert hand._pr_description_cmd() == ["devin", "-p", "--"]

    def test_returns_none_when_devin_missing(self, make_cli_hand, monkeypatch) -> None:
        hand = make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        assert hand._pr_description_cmd() is None


class TestDevinPrDescriptionPromptAsArg:
    """Cover _pr_description_prompt_as_arg returning True."""

    def test_returns_true(self, make_cli_hand) -> None:
        hand = make_cli_hand(DevinCLIHand, model="anthropic/claude-sonnet-4-6")
        assert hand._pr_description_prompt_as_arg() is True


# ---------------------------------------------------------------------------
# GitHubClient.update_pr
# ---------------------------------------------------------------------------


class TestUpdatePr:
    """Cover all branches of GitHubClient.update_pr (lines 542-549)."""

    @pytest.fixture()
    def client(self):
        from helping_hands.lib.github import GitHubClient

        with patch.object(GitHubClient, "__init__", lambda self, **kw: None):
            c = object.__new__(GitHubClient)
            c._gh = MagicMock()
            return c

    def test_both_none_returns_early(self, client) -> None:
        """When both title and body are None the method returns immediately."""
        client.update_pr("owner/repo", 1, title=None, body=None)
        client._gh.get_repo.assert_not_called()

    def test_title_only(self, client) -> None:
        """Update title, body passed as NotSet."""
        mock_pr = MagicMock()
        client._gh.get_repo.return_value.get_pull.return_value = mock_pr

        # Patch the deferred import inside the method to use a sentinel
        sentinel = object()
        with patch.dict("sys.modules", {"github": MagicMock(NotSet=sentinel)}):
            client.update_pr("owner/repo", 5, title="New Title")

        mock_pr.edit.assert_called_once_with(title="New Title", body=sentinel)

    def test_body_only(self, client) -> None:
        """Update body, title passed as NotSet."""
        mock_pr = MagicMock()
        client._gh.get_repo.return_value.get_pull.return_value = mock_pr

        sentinel = object()
        with patch.dict("sys.modules", {"github": MagicMock(NotSet=sentinel)}):
            client.update_pr("owner/repo", 5, body="New body text")

        mock_pr.edit.assert_called_once_with(title=sentinel, body="New body text")

    def test_both_title_and_body(self, client) -> None:
        """Update both title and body — neither is NotSet."""
        mock_pr = MagicMock()
        client._gh.get_repo.return_value.get_pull.return_value = mock_pr

        sentinel = object()
        with patch.dict("sys.modules", {"github": MagicMock(NotSet=sentinel)}):
            client.update_pr("owner/repo", 5, title="T", body="B")

        mock_pr.edit.assert_called_once_with(title="T", body="B")
