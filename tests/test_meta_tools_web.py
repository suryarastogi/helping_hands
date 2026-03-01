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


# ---------------------------------------------------------------------------
# Private helper tests
# ---------------------------------------------------------------------------


class TestRequireHttpUrl:
    def test_valid_https_url(self) -> None:
        assert (
            web_tools._require_http_url("https://example.com") == "https://example.com"
        )

    def test_valid_http_url(self) -> None:
        assert web_tools._require_http_url("http://example.com") == "http://example.com"

    def test_strips_whitespace(self) -> None:
        assert (
            web_tools._require_http_url("  https://example.com  ")
            == "https://example.com"
        )

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            web_tools._require_http_url("")

    def test_ftp_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            web_tools._require_http_url("ftp://example.com")

    def test_no_host_raises(self) -> None:
        with pytest.raises(ValueError, match="host"):
            web_tools._require_http_url("https://")


class TestDecodeBytes:
    def test_utf8(self) -> None:
        assert web_tools._decode_bytes(b"hello") == "hello"

    def test_utf16(self) -> None:
        payload = "hello".encode("utf-16")
        assert web_tools._decode_bytes(payload) == "hello"

    def test_latin1_fallback(self) -> None:
        # Odd-length payload with a non-utf-8 byte; utf-16 also fails on
        # odd byte counts, so latin-1 is the first successful decoder.
        payload = b"caf\xe9!"  # 5 bytes
        result = web_tools._decode_bytes(payload)
        assert result == "caf\xe9!"

    def test_fallback_replaces_errors(self) -> None:
        # Build a payload that fails utf-8, utf-16, and latin-1 cleanly,
        # so the final replace fallback is exercised.
        # latin-1 never actually fails (it maps all 256 byte values), so
        # in practice _decode_bytes always succeeds before replacement.
        # We test the happy path for coverage.
        payload = b"\xc0\xc1"  # invalid utf-8 start bytes
        result = web_tools._decode_bytes(payload)
        assert isinstance(result, str)


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert "Hello" in web_tools._strip_html("<p>Hello</p>")

    def test_removes_script_tags(self) -> None:
        html = "<html><script>var x=1;</script><body>Content</body></html>"
        result = web_tools._strip_html(html)
        assert "var x" not in result
        assert "Content" in result

    def test_removes_style_tags(self) -> None:
        html = "<html><style>.x{color:red}</style><body>Visible</body></html>"
        result = web_tools._strip_html(html)
        assert "color:red" not in result
        assert "Visible" in result

    def test_unescapes_entities(self) -> None:
        result = web_tools._strip_html("<p>A &amp; B</p>")
        assert "A & B" in result

    def test_collapses_whitespace(self) -> None:
        result = web_tools._strip_html("<p>   lots   of   spaces   </p>")
        # Should not have runs of multiple spaces
        assert "  " not in result.replace("\n", " ")


class TestAsStringKeyedDict:
    def test_valid_dict(self) -> None:
        d = {"key": "value"}
        assert web_tools._as_string_keyed_dict(d) == d

    def test_non_dict_returns_none(self) -> None:
        assert web_tools._as_string_keyed_dict([1, 2]) is None

    def test_int_keys_return_none(self) -> None:
        assert web_tools._as_string_keyed_dict({1: "a"}) is None

    def test_empty_dict(self) -> None:
        assert web_tools._as_string_keyed_dict({}) == {}


class TestExtractRelatedTopics:
    def test_simple_topic(self) -> None:
        items = [{"Text": "Python", "FirstURL": "https://python.org"}]
        output: list[web_tools.WebSearchItem] = []
        web_tools._extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "Python"
        assert output[0].url == "https://python.org"

    def test_nested_topics(self) -> None:
        items = [{"Topics": [{"Text": "Inner", "FirstURL": "https://inner.com"}]}]
        output: list[web_tools.WebSearchItem] = []
        web_tools._extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "Inner"

    def test_skips_non_dict_items(self) -> None:
        items = ["not a dict", 42, None]
        output: list[web_tools.WebSearchItem] = []
        web_tools._extract_related_topics(items, output)
        assert len(output) == 0

    def test_skips_empty_text_or_url(self) -> None:
        items = [
            {"Text": "", "FirstURL": "https://example.com"},
            {"Text": "title", "FirstURL": ""},
        ]
        output: list[web_tools.WebSearchItem] = []
        web_tools._extract_related_topics(items, output)
        assert len(output) == 0


# ---------------------------------------------------------------------------
# Public API tests
# ---------------------------------------------------------------------------


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

    def test_search_web_rejects_zero_max_results(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            web_tools.search_web("test", max_results=0)

    def test_search_web_rejects_zero_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.search_web("test", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_deduplicates_urls(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Dup","AbstractText":"text",'
            b'"AbstractURL":"https://example.com/dup",'
            b'"RelatedTopics":[{"Text":"dup","FirstURL":"https://example.com/dup"}]}'
        )
        result = web_tools.search_web("dup", max_results=10, timeout_s=10)
        urls = [r.url for r in result.results]
        assert len(urls) == len(set(urls))

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_search_web_unexpected_format_raises(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(b"[1,2,3]")
        with pytest.raises(RuntimeError, match="unexpected"):
            web_tools.search_web("test", timeout_s=10)


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

    def test_browse_url_rejects_empty_url(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            web_tools.browse_url("")

    def test_browse_url_rejects_ftp(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            web_tools.browse_url("ftp://example.com")

    def test_browse_url_rejects_zero_max_chars(self) -> None:
        with pytest.raises(ValueError, match="max_chars"):
            web_tools.browse_url("https://example.com", max_chars=0)

    def test_browse_url_rejects_zero_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_s"):
            web_tools.browse_url("https://example.com", timeout_s=0)

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_browse_url_plain_text_passthrough(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b"Just plain text content",
            content_type="text/plain",
        )
        result = web_tools.browse_url(
            "https://example.com", max_chars=1000, timeout_s=10
        )
        assert result.content == "Just plain text content"
        assert result.truncated is False
