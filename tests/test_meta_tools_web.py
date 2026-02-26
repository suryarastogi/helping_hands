"""Tests for helping_hands.lib.meta.tools.web."""

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
