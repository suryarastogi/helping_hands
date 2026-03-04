"""Tests for helping_hands.lib.meta.tools.web."""

from __future__ import annotations

from unittest.mock import patch
from urllib.error import HTTPError, URLError

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


class TestSearchWebErrors:
    def test_search_web_rejects_negative_max_results(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            web_tools.search_web("test", max_results=0)

    def test_search_web_rejects_negative_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.search_web("test", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_handles_unexpected_format(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(b'"just a string"')
        with pytest.raises(RuntimeError, match="unexpected"):
            web_tools.search_web("test")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_deduplicates_urls(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"","AbstractText":"","AbstractURL":"",'
            b'"RelatedTopics":[{"Text":"A","FirstURL":"https://example.com/a"},'
            b'{"Text":"B","FirstURL":"https://example.com/a"},'
            b'{"Text":"C","FirstURL":"https://example.com/c"}]}'
        )
        result = web_tools.search_web("test", max_results=10)
        urls = [r.url for r in result.results]
        assert urls == ["https://example.com/a", "https://example.com/c"]

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_http_error_propagates(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            "https://api.duckduckgo.com/", 403, "Forbidden", {}, None
        )
        with pytest.raises(HTTPError):
            web_tools.search_web("test")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_network_error_propagates(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("Connection refused")
        with pytest.raises(URLError):
            web_tools.search_web("test")


class TestBrowseUrlErrors:
    def test_browse_url_rejects_empty_url(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            web_tools.browse_url("")

    def test_browse_url_rejects_non_http(self) -> None:
        with pytest.raises(ValueError, match="http"):
            web_tools.browse_url("ftp://example.com")

    def test_browse_url_rejects_no_host(self) -> None:
        with pytest.raises(ValueError, match="host"):
            web_tools.browse_url("http://")

    def test_browse_url_rejects_negative_max_chars(self) -> None:
        with pytest.raises(ValueError, match="max_chars"):
            web_tools.browse_url("https://example.com", max_chars=0)

    def test_browse_url_rejects_negative_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.browse_url("https://example.com", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_handles_plain_text(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b"Just plain text content",
            content_type="text/plain",
        )
        result = web_tools.browse_url("https://example.com", max_chars=100)
        assert result.content == "Just plain text content"
        assert result.truncated is False

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_http_error_propagates(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )
        with pytest.raises(HTTPError):
            web_tools.browse_url("https://example.com")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_strips_script_and_style_tags(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b"<html><body><script>alert(1)</script>"
            b"<style>.x{color:red}</style><p>Safe</p></body></html>",
            content_type="text/html",
        )
        result = web_tools.browse_url("https://example.com", max_chars=1000)
        assert "alert" not in result.content
        assert "color:red" not in result.content
        assert "Safe" in result.content
