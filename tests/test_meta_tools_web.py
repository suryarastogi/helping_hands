"""Protects web search and browsing tools exposed to the AI during agentic loops.

search_web must correctly parse the DuckDuckGo JSON envelope and reject empty
queries (an empty query returns unrelated results that mislead the AI).
browse_url must strip scripts/styles before returning content -- leaving them in
wastes context tokens and confuses the AI with JavaScript noise. max_chars
truncation prevents oversized pages from blowing the prompt budget. The
pre-compiled regex constants must stay compiled module-level; inlining them
causes re-compilation on every call, measurably degrading performance when the
AI browses multiple pages in a single agentic loop.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from helping_hands.lib.meta.tools import web as web_tools


class _FakeResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        url: str = "https://example.com",
        status: int = 200,
        content_type: str = "application/json",
    ) -> None:
        self._payload = payload
        self._url = url
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        return None

    def read(self) -> bytes:
        return self._payload

    def geturl(self) -> str:
        return self._url


class TestSearchWeb:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_parses_results(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Python","AbstractText":"Python release notes",'
            b'"AbstractURL":"https://example.com/python",'
            b'"RelatedTopics":[{"Text":"PEP updates","FirstURL":"https://example.com/pep"}]}'
        )

        result = web_tools.search_web("python release", max_results=2, timeout_s=10)

        assert result.query == "python release"
        assert len(result.results) == 2
        assert result.results[0].url == "https://example.com/python"
        assert result.results[1].url == "https://example.com/pep"

    def test_search_web_rejects_empty_query(self) -> None:
        with pytest.raises(ValueError):
            web_tools.search_web("")


class TestBrowseUrl:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_extracts_text(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            (
                b"<html><head><title>T</title><style>.x{}</style></head>"
                b"<body><h1>Hello</h1><p>World</p></body></html>"
            ),
            url="https://example.com/final",
            content_type="text/html; charset=utf-8",
        )

        result = web_tools.browse_url(
            "https://example.com", max_chars=100, timeout_s=10
        )

        assert result.url == "https://example.com"
        assert result.final_url == "https://example.com/final"
        assert "Hello" in result.content
        assert "World" in result.content

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_truncates(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b"<html><body>abcdefghijklmnopqrstuvwxyz</body></html>",
            content_type="text/html",
        )

        result = web_tools.browse_url("https://example.com", max_chars=10, timeout_s=10)

        assert result.truncated is True
        assert len(result.content) == 10


# ---------------------------------------------------------------------------
# Pre-compiled HTML strip regex constants (v190)
# ---------------------------------------------------------------------------


class TestHtmlStripRegexConstants:
    """Tests for pre-compiled regex constants used in _strip_html."""

    def test_script_style_re_is_compiled(self) -> None:
        import re

        assert isinstance(web_tools._SCRIPT_STYLE_RE, re.Pattern)

    def test_script_style_re_case_insensitive(self) -> None:
        import re

        assert web_tools._SCRIPT_STYLE_RE.flags & re.IGNORECASE

    def test_script_style_re_dotall(self) -> None:
        import re

        assert web_tools._SCRIPT_STYLE_RE.flags & re.DOTALL

    def test_script_style_re_matches_script(self) -> None:
        text = '<script type="text/javascript">alert("hi")</script>'
        assert web_tools._SCRIPT_STYLE_RE.search(text)

    def test_script_style_re_matches_style(self) -> None:
        text = "<style>body { color: red; }</style>"
        assert web_tools._SCRIPT_STYLE_RE.search(text)

    def test_html_tag_re_is_compiled(self) -> None:
        import re

        assert isinstance(web_tools._HTML_TAG_RE, re.Pattern)

    def test_html_tag_re_matches_tag(self) -> None:
        assert web_tools._HTML_TAG_RE.search("<div>")

    def test_html_tag_re_no_match_plain(self) -> None:
        assert web_tools._HTML_TAG_RE.search("plain text") is None

    def test_horizontal_whitespace_re_is_compiled(self) -> None:
        import re

        assert isinstance(web_tools._HORIZONTAL_WHITESPACE_RE, re.Pattern)

    def test_horizontal_whitespace_re_collapses_spaces(self) -> None:
        assert web_tools._HORIZONTAL_WHITESPACE_RE.sub(" ", "a   b") == "a b"

    def test_blank_lines_re_is_compiled(self) -> None:
        import re

        assert isinstance(web_tools._BLANK_LINES_RE, re.Pattern)

    def test_blank_lines_re_collapses(self) -> None:
        result = web_tools._BLANK_LINES_RE.sub("\n\n", "a\n\n\n\nb")
        assert result == "a\n\nb"

    def test_strip_html_uses_compiled_constants(self) -> None:
        """_strip_html uses pre-compiled regex constants, not inline patterns."""
        import inspect

        src = inspect.getsource(web_tools._strip_html)
        assert "_SCRIPT_STYLE_RE" in src
        assert "_HTML_TAG_RE" in src
        assert "_HORIZONTAL_WHITESPACE_RE" in src
        assert "_BLANK_LINES_RE" in src
        # Should NOT contain inline re.sub with raw string patterns
        assert "re.sub(" not in src
