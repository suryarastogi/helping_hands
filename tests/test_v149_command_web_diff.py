"""Tests for v149: empty command validation, web timeout cap, _get_diff OSError."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from helping_hands.lib.meta.tools.command import _run_command
from helping_hands.lib.meta.tools.web import _MAX_WEB_TIMEOUT_S

# ---------------------------------------------------------------------------
# _run_command empty command validation
# ---------------------------------------------------------------------------


class TestRunCommandEmptyValidation:
    def test_empty_list_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="command list must not be empty"):
            _run_command([], cwd=tmp_path, timeout_s=10)

    def test_single_element_list_accepted(self, tmp_path: Path) -> None:
        """A single-element command list should not raise ValueError."""
        # "echo" exists on all platforms; just verify no ValueError.
        result = _run_command(["echo", "ok"], cwd=tmp_path, timeout_s=10)
        assert result.exit_code == 0

    def test_empty_list_error_before_timeout_check(self, tmp_path: Path) -> None:
        """Empty-list check fires before timeout validation."""
        with pytest.raises(ValueError, match="command list must not be empty"):
            _run_command([], cwd=tmp_path, timeout_s=-1)


# ---------------------------------------------------------------------------
# _MAX_WEB_TIMEOUT_S constant
# ---------------------------------------------------------------------------


class TestMaxWebTimeoutConstant:
    def test_value(self) -> None:
        assert _MAX_WEB_TIMEOUT_S == 300

    def test_type(self) -> None:
        assert isinstance(_MAX_WEB_TIMEOUT_S, int)

    def test_positive(self) -> None:
        assert _MAX_WEB_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# search_web timeout clamping
# ---------------------------------------------------------------------------


class TestSearchWebTimeoutCap:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_over_max_is_clamped(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        import json

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = lambda s, *a: None
        mock_urlopen.return_value.read.return_value = json.dumps(
            {"AbstractText": "", "RelatedTopics": []}
        ).encode()

        from helping_hands.lib.meta.tools.web import search_web

        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.meta.tools.web"
        ):
            search_web("test query", timeout_s=600)

        assert any("exceeds maximum" in r.message for r in caplog.records)
        # Verify the actual timeout passed to urlopen was clamped
        call_kwargs = mock_urlopen.call_args
        assert (
            call_kwargs[1].get(
                "timeout", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
            )
            == _MAX_WEB_TIMEOUT_S
        )

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_at_max_not_clamped(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        import json

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = lambda s, *a: None
        mock_urlopen.return_value.read.return_value = json.dumps(
            {"AbstractText": "", "RelatedTopics": []}
        ).encode()

        from helping_hands.lib.meta.tools.web import search_web

        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.meta.tools.web"
        ):
            search_web("test query", timeout_s=_MAX_WEB_TIMEOUT_S)

        assert not any("exceeds maximum" in r.message for r in caplog.records)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_below_max_not_clamped(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        import json

        mock_urlopen.return_value.__enter__ = lambda s: s
        mock_urlopen.return_value.__exit__ = lambda s, *a: None
        mock_urlopen.return_value.read.return_value = json.dumps(
            {"AbstractText": "", "RelatedTopics": []}
        ).encode()

        from helping_hands.lib.meta.tools.web import search_web

        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.meta.tools.web"
        ):
            search_web("test query", timeout_s=10)

        assert not any("exceeds maximum" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# browse_url timeout clamping
# ---------------------------------------------------------------------------


class TestBrowseUrlTimeoutCap:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_over_max_is_clamped(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        from helping_hands.lib.meta.tools.web import browse_url

        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        resp.read.return_value = b"<html><body>Hello</body></html>"
        resp.geturl.return_value = "https://example.com"
        resp.status = 200
        resp.headers = {"Content-Type": "text/html"}
        mock_urlopen.return_value = resp

        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.meta.tools.web"
        ):
            browse_url("https://example.com", timeout_s=600)

        assert any("exceeds maximum" in r.message for r in caplog.records)
        call_kwargs = mock_urlopen.call_args
        assert (
            call_kwargs[1].get(
                "timeout", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
            )
            == _MAX_WEB_TIMEOUT_S
        )

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_at_max_not_clamped(
        self, mock_urlopen: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        from helping_hands.lib.meta.tools.web import browse_url

        resp = MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        resp.read.return_value = b"<html><body>Hello</body></html>"
        resp.geturl.return_value = "https://example.com"
        resp.status = 200
        resp.headers = {"Content-Type": "text/html"}
        mock_urlopen.return_value = resp

        with caplog.at_level(
            logging.WARNING, logger="helping_hands.lib.meta.tools.web"
        ):
            browse_url("https://example.com", timeout_s=_MAX_WEB_TIMEOUT_S)

        assert not any("exceeds maximum" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _get_diff OSError handling
# ---------------------------------------------------------------------------


class TestGetDiffOSError:
    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_oserror_on_first_diff_returns_empty(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """OSError on first git diff call returns empty string."""
        mock_run.side_effect = OSError("Permission denied")
        from helping_hands.lib.hands.v1.hand.pr_description import _get_diff

        assert _get_diff(tmp_path, base_branch="main") == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_oserror_on_fallback_diff_returns_empty(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """OSError on fallback git diff call returns empty string."""
        mock_run.side_effect = [
            # First diff returns failure (triggers fallback)
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
            # Fallback raises OSError
            OSError("Broken pipe"),
        ]
        from helping_hands.lib.hands.v1.hand.pr_description import _get_diff

        assert _get_diff(tmp_path, base_branch="main") == ""
        assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# _get_uncommitted_diff OSError handling
# ---------------------------------------------------------------------------


class TestGetUncommittedDiffOSError:
    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_oserror_on_git_add_returns_empty(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """OSError on git add returns empty string."""
        mock_run.side_effect = OSError("Permission denied")
        from helping_hands.lib.hands.v1.hand.pr_description import _get_uncommitted_diff

        assert _get_uncommitted_diff(tmp_path) == ""

    @patch("helping_hands.lib.hands.v1.hand.pr_description.subprocess.run")
    def test_oserror_on_git_diff_cached_returns_empty(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """OSError on git diff --cached returns empty string."""
        mock_run.side_effect = [
            # git add succeeds
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            # git diff --cached raises OSError
            OSError("Broken pipe"),
        ]
        from helping_hands.lib.hands.v1.hand.pr_description import _get_uncommitted_diff

        assert _get_uncommitted_diff(tmp_path) == ""
        assert mock_run.call_count == 2
