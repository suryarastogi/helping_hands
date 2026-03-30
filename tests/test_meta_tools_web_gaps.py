"""Tests for uncovered branches in helping_hands.lib.meta.tools.web.

Closes coverage gaps in: _raise_url_error (HTTP vs URL error paths),
_require_http_url (scheme/netloc validation), _decode_bytes (UTF-16
fallback), _as_string_keyed_dict (non-dict and non-string keys),
_extract_related_topics (nested Topics recursion, non-dict items,
missing/non-string Text/URL), search_web (HTTPError/URLError catch,
unexpected response format, deduplication, empty URL filtering,
abstract-only without RelatedTopics), and browse_url (HTTPError/URLError
catch, non-HTML content type, plain text passthrough).
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from helping_hands.lib.meta.tools.web import (
    WebSearchItem,
    _as_string_keyed_dict,
    _decode_bytes,
    _extract_related_topics,
    _raise_url_error,
    _require_http_url,
    browse_url,
    search_web,
)

# -- _FakeResponse helper (same pattern as test_meta_tools_web.py) ----------


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

    def read(self) -> bytes:
        return self._payload

    def geturl(self) -> str:
        return self._url


# ---------------------------------------------------------------------------
# _raise_url_error
# ---------------------------------------------------------------------------


class TestRaiseUrlError:
    def test_http_error_includes_code_and_reason(self) -> None:
        exc = HTTPError("https://example.com", 404, "Not Found", {}, BytesIO(b""))
        with pytest.raises(RuntimeError, match=r"HTTP 404.*Not Found"):
            _raise_url_error(exc, operation="search")

    def test_url_error_includes_reason(self) -> None:
        exc = URLError("Connection refused")
        with pytest.raises(RuntimeError, match="Connection refused"):
            _raise_url_error(exc, operation="browse")

    def test_http_error_chains_original(self) -> None:
        exc = HTTPError(
            "https://example.com", 500, "Internal Server Error", {}, BytesIO(b"")
        )
        with pytest.raises(RuntimeError) as exc_info:
            _raise_url_error(exc, operation="fetch")
        assert exc_info.value.__cause__ is exc

    def test_url_error_chains_original(self) -> None:
        exc = URLError("timeout")
        with pytest.raises(RuntimeError) as exc_info:
            _raise_url_error(exc, operation="fetch")
        assert exc_info.value.__cause__ is exc

    def test_operation_label_appears_in_message(self) -> None:
        exc = URLError("fail")
        with pytest.raises(RuntimeError, match=r"^browse request failed"):
            _raise_url_error(exc, operation="browse")


# ---------------------------------------------------------------------------
# _require_http_url
# ---------------------------------------------------------------------------


class TestRequireHttpUrl:
    def test_accepts_http(self) -> None:
        assert _require_http_url("http://example.com") == "http://example.com"

    def test_accepts_https(self) -> None:
        assert _require_http_url("https://example.com") == "https://example.com"

    def test_rejects_ftp_scheme(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            _require_http_url("ftp://example.com")

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            _require_http_url("file:///etc/passwd")

    def test_rejects_missing_host(self) -> None:
        with pytest.raises(ValueError, match="must include host"):
            _require_http_url("http://")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError):
            _require_http_url("")

    def test_strips_whitespace(self) -> None:
        result = _require_http_url("  https://example.com  ")
        assert result == "https://example.com"


# ---------------------------------------------------------------------------
# _decode_bytes
# ---------------------------------------------------------------------------


class TestDecodeBytes:
    def test_utf8(self) -> None:
        assert _decode_bytes(b"hello") == "hello"

    def test_utf16_fallback(self) -> None:
        """UTF-16 BOM bytes that are invalid UTF-8 fall through to UTF-16."""
        payload = "café".encode("utf-16")
        result = _decode_bytes(payload)
        assert "caf" in result

    def test_latin1_fallback(self) -> None:
        """Bytes invalid in both UTF-8 and UTF-16 fall through to latin-1."""
        # Single byte 0xff is invalid UTF-8 and incomplete UTF-16
        payload = b"\xff\xfe\xfd"
        result = _decode_bytes(payload)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _as_string_keyed_dict
# ---------------------------------------------------------------------------


class TestAsStringKeyedDict:
    def test_valid_dict(self) -> None:
        d = {"key": "value", "num": 42}
        assert _as_string_keyed_dict(d) is d

    def test_non_dict_returns_none(self) -> None:
        assert _as_string_keyed_dict([1, 2, 3]) is None
        assert _as_string_keyed_dict("string") is None
        assert _as_string_keyed_dict(42) is None

    def test_non_string_key_returns_none(self) -> None:
        assert _as_string_keyed_dict({1: "one", 2: "two"}) is None

    def test_mixed_keys_returns_none(self) -> None:
        assert _as_string_keyed_dict({"ok": 1, 2: "bad"}) is None

    def test_empty_dict(self) -> None:
        d: dict[str, object] = {}
        assert _as_string_keyed_dict(d) is d


# ---------------------------------------------------------------------------
# _extract_related_topics
# ---------------------------------------------------------------------------


class TestExtractRelatedTopics:
    def test_flat_topic_extraction(self) -> None:
        items = [
            {"Text": "Python lang", "FirstURL": "https://python.org"},
            {"Text": "Rust lang", "FirstURL": "https://rust-lang.org"},
        ]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 2
        assert output[0].title == "Python lang"
        assert output[1].url == "https://rust-lang.org"

    def test_nested_topics_recursion(self) -> None:
        items = [
            {
                "Topics": [
                    {"Text": "Nested result", "FirstURL": "https://nested.com"},
                ]
            },
        ]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert len(output) == 1
        assert output[0].title == "Nested result"

    def test_skips_non_dict_items(self) -> None:
        items = ["not a dict", 42, None]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_item_without_text(self) -> None:
        items = [{"FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_item_without_url(self) -> None:
        items = [{"Text": "No URL here"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_empty_text(self) -> None:
        items = [{"Text": "   ", "FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_empty_url(self) -> None:
        items = [{"Text": "Valid text", "FirstURL": "   "}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_non_string_text(self) -> None:
        items = [{"Text": 42, "FirstURL": "https://example.com"}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []

    def test_skips_non_string_url(self) -> None:
        items = [{"Text": "Valid", "FirstURL": 42}]
        output: list[WebSearchItem] = []
        _extract_related_topics(items, output)
        assert output == []


# ---------------------------------------------------------------------------
# search_web
# ---------------------------------------------------------------------------


class TestSearchWebGaps:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_raises_runtime(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            "https://api.duckduckgo.com/", 503, "Service Unavailable", {}, BytesIO(b"")
        )
        with pytest.raises(RuntimeError, match="HTTP 503"):
            search_web("test query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_url_error_raises_runtime(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("Connection refused")
        with pytest.raises(RuntimeError, match="Connection refused"):
            search_web("test query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_non_dict_response_raises_runtime(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(b'"just a string"')
        with pytest.raises(RuntimeError, match="unexpected search response format"):
            search_web("test query")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_deduplicates_urls(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"AbstractText":"","RelatedTopics":['
            b'{"Text":"A","FirstURL":"https://example.com/same"},'
            b'{"Text":"B","FirstURL":"https://example.com/same"},'
            b'{"Text":"C","FirstURL":"https://example.com/other"}'
            b"]}"
        )
        result = search_web("test", max_results=10)
        urls = [r.url for r in result.results]
        assert urls == ["https://example.com/same", "https://example.com/other"]

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_filters_empty_urls(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"AbstractText":"","RelatedTopics":['
            b'{"Text":"No URL","FirstURL":""},'
            b'{"Text":"Has URL","FirstURL":"https://example.com/real"}'
            b"]}"
        )
        result = search_web("test", max_results=10)
        assert len(result.results) == 1
        assert result.results[0].url == "https://example.com/real"

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_abstract_only_no_related(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"Heading":"Python","AbstractText":"A language",'
            b'"AbstractURL":"https://python.org"}'
        )
        result = search_web("python")
        assert len(result.results) == 1
        assert result.results[0].title == "Python"
        assert result.results[0].snippet == "A language"

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_abstract_with_no_heading(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"AbstractText":"Some text","AbstractURL":"https://example.com"}'
        )
        result = search_web("query")
        assert result.results[0].title == "DuckDuckGo result"

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_max_results_limits_output(self, mock_urlopen) -> None:
        topics = ",".join(
            f'{{"Text":"T{i}","FirstURL":"https://example.com/{i}"}}' for i in range(10)
        )
        mock_urlopen.return_value = _FakeResponse(
            f'{{"AbstractText":"","RelatedTopics":[{topics}]}}'.encode()
        )
        result = search_web("test", max_results=3)
        assert len(result.results) == 3


# ---------------------------------------------------------------------------
# browse_url
# ---------------------------------------------------------------------------


class TestBrowseUrlGaps:
    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_http_error_raises_runtime(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            "https://example.com", 404, "Not Found", {}, BytesIO(b"")
        )
        with pytest.raises(RuntimeError, match="HTTP 404"):
            browse_url("https://example.com")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_url_error_raises_runtime(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = URLError("DNS resolution failed")
        with pytest.raises(RuntimeError, match="DNS resolution failed"):
            browse_url("https://example.com")

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_non_html_content_type_no_strip(self, mock_urlopen) -> None:
        """Non-HTML content is returned as-is (no tag stripping)."""
        mock_urlopen.return_value = _FakeResponse(
            b"plain text with <angle brackets>",
            content_type="text/plain",
        )
        result = browse_url("https://example.com", max_chars=1000)
        assert "<angle brackets>" in result.content

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_html_detected_by_content(self, mock_urlopen) -> None:
        """Even without html content-type, <html in body triggers stripping."""
        mock_urlopen.return_value = _FakeResponse(
            b"<html><body><p>Stripped</p></body></html>",
            content_type="application/octet-stream",
        )
        result = browse_url("https://example.com", max_chars=1000)
        assert "<p>" not in result.content
        assert "Stripped" in result.content

    @patch("helping_hands.lib.meta.tools.web.urlopen")
    def test_json_content_type_no_strip(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _FakeResponse(
            b'{"key": "value"}',
            content_type="application/json",
        )
        result = browse_url("https://example.com", max_chars=1000)
        assert result.content == '{"key": "value"}'

    def test_rejects_ftp_url(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            browse_url("ftp://example.com")
