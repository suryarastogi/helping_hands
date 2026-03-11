"""Tests for web.py edge cases: _extract_related_topics, search/browse validation."""

from __future__ import annotations

from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from helping_hands.lib.meta.tools import web as web_tools
from helping_hands.lib.meta.tools.web import (
    WebSearchItem,
    _extract_related_topics,
    _require_http_url,
    _strip_html,
)

# ===================================================================
# _require_http_url — additional cases
# ===================================================================


class TestRequireHttpUrlExtra:
    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            _require_http_url("   ")

    def test_rejects_no_scheme(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            _require_http_url("example.com")


# ===================================================================
# _strip_html — additional cases
# ===================================================================


class TestStripHtmlExtra:
    def test_removes_noscript_tags(self) -> None:
        html = "<noscript>Enable JS</noscript><p>Body</p>"
        result = _strip_html(html)
        assert "Enable JS" not in result
        assert "Body" in result

    def test_collapses_blank_lines(self) -> None:
        html = "<p>A</p>\n\n\n\n<p>B</p>"
        result = _strip_html(html)
        assert "\n\n\n" not in result


# ===================================================================
# _extract_related_topics
# ===================================================================


class TestExtractRelatedTopics:
    def test_extracts_text_and_url(self) -> None:
        items = [{"Text": "Python", "FirstURL": "https://python.org"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "Python"
        assert output[0].url == "https://python.org"

    def test_recursive_topics(self) -> None:
        items = [
            {
                "Topics": [
                    {"Text": "Nested", "FirstURL": "https://example.com/nested"},
                ],
            }
        ]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "Nested"

    def test_skips_non_dict_items(self) -> None:
        items = ["not a dict", 42, None]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 0

    def test_skips_missing_text(self) -> None:
        items = [{"FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 0

    def test_skips_empty_text(self) -> None:
        items = [{"Text": "  ", "FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 0

    def test_skips_missing_url(self) -> None:
        items = [{"Text": "Hello"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 0

    def test_skips_empty_url(self) -> None:
        items = [{"Text": "Hello", "FirstURL": "  "}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 0


# ===================================================================
# search_web edge cases
# ===================================================================


class _FakeResponse:
    def __init__(self, payload: bytes, **kwargs) -> None:
        self._payload = payload
        self._url = kwargs.get("url", "https://example.com")
        self.status = kwargs.get("status", 200)
        self.headers = {"Content-Type": kwargs.get("content_type", "application/json")}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None

    def read(self):
        return self._payload

    def geturl(self):
        return self._url


class TestSearchWebEdgeCases:
    def test_invalid_max_results(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            web_tools.search_web("query", max_results=0)

    def test_negative_max_results(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            web_tools.search_web("query", max_results=-1)

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.search_web("query", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_unexpected_response_format(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(b'"just a string"')
        with pytest.raises(RuntimeError, match="unexpected"):
            web_tools.search_web("query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_deduplicates_urls(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Test","AbstractText":"","AbstractURL":"",'
            b'"RelatedTopics":['
            b'{"Text":"A","FirstURL":"https://same.com"},'
            b'{"Text":"B","FirstURL":"https://same.com"},'
            b'{"Text":"C","FirstURL":"https://other.com"}'
            b"]}"
        )
        result = web_tools.search_web("test", max_results=10)
        urls = [r.url for r in result.results]
        assert urls.count("https://same.com") == 1
        assert "https://other.com" in urls

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_empty_url_items_skipped(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Test","AbstractText":"","AbstractURL":"",'
            b'"RelatedTopics":[{"Text":"NoURL","FirstURL":""}]}'
        )
        result = web_tools.search_web("test")
        assert len(result.results) == 0

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_related_topics_non_list_skipped(self, mock_urlopen) -> None:
        """When RelatedTopics is a string instead of list, it is ignored."""
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Test","AbstractText":"summary",'
            b'"AbstractURL":"https://example.com",'
            b'"RelatedTopics":"not a list"}'
        )
        result = web_tools.search_web("test")
        # Only the abstract result should be present
        assert len(result.results) == 1
        assert result.results[0].url == "https://example.com"

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_max_results_limits_output(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Test","AbstractText":"","AbstractURL":"",'
            b'"RelatedTopics":['
            b'{"Text":"A","FirstURL":"https://a.com"},'
            b'{"Text":"B","FirstURL":"https://b.com"},'
            b'{"Text":"C","FirstURL":"https://c.com"}'
            b"]}"
        )
        result = web_tools.search_web("test", max_results=2)
        assert len(result.results) == 2


# ===================================================================
# browse_url edge cases
# ===================================================================


class TestBrowseUrlEdgeCases:
    def test_invalid_max_chars(self) -> None:
        with pytest.raises(ValueError, match="max_chars"):
            web_tools.browse_url("https://example.com", max_chars=0)

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.browse_url("https://example.com", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_non_html_content(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b"plain text content",
            url="https://example.com/file.txt",
            content_type="text/plain",
        )
        result = web_tools.browse_url("https://example.com/file.txt")
        assert result.content == "plain text content"
        assert result.truncated is False

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_html_detected_by_body(self, mock_urlopen) -> None:
        """HTML detected by <html tag even if content-type is generic."""
        mock_urlopen.return_value = _FakeResponse(
            b"<html><body><p>Content</p></body></html>",
            url="https://example.com",
            content_type="application/octet-stream",
        )
        result = web_tools.browse_url("https://example.com")
        assert "Content" in result.content
        assert "<p>" not in result.content


# ===================================================================
# search_web network errors
# ===================================================================


class TestSearchWebNetworkErrors:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_raises_runtime_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://api.duckduckgo.com/",
            code=503,
            msg="Service Unavailable",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError, match="HTTP 503"):
            web_tools.search_web("test query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_url_error_raises_runtime_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("Name or service not known")
        with pytest.raises(RuntimeError, match="search request failed"):
            web_tools.search_web("test query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_includes_status_code(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://api.duckduckgo.com/",
            code=429,
            msg="Too Many Requests",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError, match="HTTP 429"):
            web_tools.search_web("test query")


# ===================================================================
# browse_url network errors
# ===================================================================


class TestBrowseUrlNetworkErrors:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_raises_runtime_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError, match="HTTP 404"):
            web_tools.browse_url("https://example.com")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_url_error_raises_runtime_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("Connection refused")
        with pytest.raises(RuntimeError, match="browse request failed"):
            web_tools.browse_url("https://example.com")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_includes_reason(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
        with pytest.raises(RuntimeError, match="Internal Server Error"):
            web_tools.browse_url("https://example.com")
