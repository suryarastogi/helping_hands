"""Tests for v347 coverage gap closure.

Closes remaining non-server coverage gaps:

- ``_LinePrefixEmitter`` in ``cli/base.py`` (lines 312-320, 325-329): buffered
  line-by-line emission with prefix deduplication and blank-line passthrough.
  A bug here would corrupt streaming output seen by users monitoring long-
  running CLI hand invocations.

- ``DevinCLIHand._pr_description_cmd`` and ``_pr_description_prompt_as_arg``
  (lines 38-40, 44): PR description generation delegation when ``devin`` is
  on ``$PATH``.

- ``OpenCodeCLIHand._pr_description_cmd`` (lines 35-37): PR description
  generation delegation when ``opencode`` is on ``$PATH``.

- ``GitHubClient.update_pr`` (lines 542-549): title/body update
  with ``NotSet`` passthrough for unchanged fields.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helping_hands.lib.hands.v1.hand.cli.base import _LinePrefixEmitter

# ---------------------------------------------------------------------------
# _LinePrefixEmitter
# ---------------------------------------------------------------------------


class TestLinePrefixEmitterCall:
    """Tests for _LinePrefixEmitter.__call__ line-by-line emission."""

    @pytest.mark.asyncio
    async def test_single_line_with_newline(self) -> None:
        """A complete line gets the [label] prefix."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "test")
        await le("hello\n")
        emit.assert_awaited_once_with("[test] hello\n")

    @pytest.mark.asyncio
    async def test_blank_line_passthrough(self) -> None:
        """Blank lines emit a bare newline without prefix."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "test")
        await le("\n")
        emit.assert_awaited_once_with("\n")

    @pytest.mark.asyncio
    async def test_already_prefixed_not_doubled(self) -> None:
        """Lines that already carry the [label] prefix are not re-prefixed."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "x")
        await le("[x] already prefixed\n")
        emit.assert_awaited_once_with("[x] already prefixed\n")

    @pytest.mark.asyncio
    async def test_multiple_lines_in_one_chunk(self) -> None:
        """Multiple lines in a single chunk all get emitted."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "m")
        await le("line1\nline2\n")
        assert emit.await_count == 2
        emit.assert_any_await("[m] line1\n")
        emit.assert_any_await("[m] line2\n")

    @pytest.mark.asyncio
    async def test_partial_chunk_buffered(self) -> None:
        """Text without a trailing newline is buffered, not emitted yet."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "b")
        await le("no newline")
        emit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_partial_then_completed(self) -> None:
        """Buffered partial text is emitted once newline arrives."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "b")
        await le("first ")
        await le("half\n")
        emit.assert_awaited_once_with("[b] first half\n")

    @pytest.mark.asyncio
    async def test_whitespace_only_line_is_blank(self) -> None:
        """A line with only whitespace counts as blank."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "w")
        await le("   \n")
        emit.assert_awaited_once_with("\n")


class TestLinePrefixEmitterFlush:
    """Tests for _LinePrefixEmitter.flush."""

    @pytest.mark.asyncio
    async def test_flush_remaining_buffer(self) -> None:
        """Flush emits buffered text with prefix."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "f")
        await le("leftover")
        await le.flush()
        emit.assert_awaited_once_with("[f] leftover")

    @pytest.mark.asyncio
    async def test_flush_already_prefixed(self) -> None:
        """Flush does not double-prefix buffered text."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "f")
        await le("[f] already")
        await le.flush()
        emit.assert_awaited_once_with("[f] already")

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_noop(self) -> None:
        """Flush with empty buffer does not emit."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "f")
        await le.flush()
        emit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_flush_whitespace_only_noop(self) -> None:
        """Flush with whitespace-only buffer does not emit."""
        emit = AsyncMock()
        le = _LinePrefixEmitter(emit, "f")
        le._buffer = "   "
        await le.flush()
        emit.assert_not_awaited()


# ---------------------------------------------------------------------------
# DevinCLIHand._pr_description_cmd / _pr_description_prompt_as_arg
# ---------------------------------------------------------------------------


class TestDevinPrDescriptionCmd:
    """Tests for DevinCLIHand._pr_description_cmd and prompt arg flag."""

    def test_returns_cmd_when_devin_on_path(self, make_cli_hand) -> None:
        from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

        hand = make_cli_hand(DevinCLIHand, model="claude-opus-4-6")
        with patch("shutil.which", return_value="/usr/bin/devin"):
            result = hand._pr_description_cmd()
        assert result == ["devin", "-p", "--"]

    def test_returns_none_when_devin_not_on_path(self, make_cli_hand) -> None:
        from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

        hand = make_cli_hand(DevinCLIHand, model="claude-opus-4-6")
        with patch("shutil.which", return_value=None):
            result = hand._pr_description_cmd()
        assert result is None

    def test_pr_description_prompt_as_arg(self, make_cli_hand) -> None:
        from helping_hands.lib.hands.v1.hand.cli.devin import DevinCLIHand

        hand = make_cli_hand(DevinCLIHand, model="claude-opus-4-6")
        assert hand._pr_description_prompt_as_arg() is True


# ---------------------------------------------------------------------------
# OpenCodeCLIHand._pr_description_cmd
# ---------------------------------------------------------------------------


class TestOpenCodePrDescriptionCmd:
    """Tests for OpenCodeCLIHand._pr_description_cmd."""

    def test_returns_cmd_when_opencode_on_path(self, make_cli_hand) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-6")
        with patch("shutil.which", return_value="/usr/bin/opencode"):
            result = hand._pr_description_cmd()
        assert result == ["opencode", "run"]

    def test_returns_none_when_opencode_not_on_path(self, make_cli_hand) -> None:
        from helping_hands.lib.hands.v1.hand.cli.opencode import OpenCodeCLIHand

        hand = make_cli_hand(OpenCodeCLIHand, model="anthropic/claude-sonnet-4-6")
        with patch("shutil.which", return_value=None):
            result = hand._pr_description_cmd()
        assert result is None


# ---------------------------------------------------------------------------
# GitHubClient.update_pr
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure GITHUB_TOKEN is set for GitHubClient construction."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake_token_for_tests")


class TestUpdatePr:
    """Tests for GitHubClient.update_pr."""

    _SENTINEL = object()

    def _make_client(self):
        from helping_hands.lib.github import GitHubClient

        with patch("helping_hands.lib.github.Github"):
            return GitHubClient()

    def _call_update_pr(self, client, *args, **kwargs):
        """Call update_pr with github.NotSet patched into the github module."""
        import sys

        # Temporarily make `from github import NotSet` work by injecting it
        github_mod = sys.modules["github"]
        had_notset = hasattr(github_mod, "NotSet")
        original = getattr(github_mod, "NotSet", None)
        github_mod.NotSet = self._SENTINEL
        try:
            client.update_pr(*args, **kwargs)
        finally:
            if had_notset:
                github_mod.NotSet = original
            else:
                delattr(github_mod, "NotSet")

    def test_both_none_returns_early(self) -> None:
        """When both title and body are None, no API call is made."""
        client = self._make_client()
        mock_repo = MagicMock()
        client.get_repo = MagicMock(return_value=mock_repo)
        client.update_pr("owner/repo", 1, title=None, body=None)
        mock_repo.get_pull.assert_not_called()

    def test_title_only(self) -> None:
        """When only title is provided, body is passed as NotSet sentinel."""
        client = self._make_client()
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client.get_repo = MagicMock(return_value=mock_repo)

        self._call_update_pr(client, "owner/repo", 5, title="New Title")

        mock_repo.get_pull.assert_called_once_with(5)
        call_kwargs = mock_pr.edit.call_args[1]
        assert call_kwargs["title"] == "New Title"
        assert call_kwargs["body"] is self._SENTINEL

    def test_body_only(self) -> None:
        """When only body is provided, title is passed as NotSet sentinel."""
        client = self._make_client()
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client.get_repo = MagicMock(return_value=mock_repo)

        self._call_update_pr(client, "owner/repo", 3, body="Updated body")

        call_kwargs = mock_pr.edit.call_args[1]
        assert call_kwargs["title"] is self._SENTINEL
        assert call_kwargs["body"] == "Updated body"

    def test_both_title_and_body(self) -> None:
        """When both are provided, both are passed directly."""
        client = self._make_client()
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        client.get_repo = MagicMock(return_value=mock_repo)

        self._call_update_pr(client, "owner/repo", 2, title="T", body="B")

        call_kwargs = mock_pr.edit.call_args[1]
        assert call_kwargs["title"] == "T"
        assert call_kwargs["body"] == "B"

    def test_invalid_pr_number_raises(self) -> None:
        """Non-positive PR number raises ValueError."""
        client = self._make_client()
        with pytest.raises(ValueError, match="PR number"):
            client.update_pr("owner/repo", 0, title="X")
