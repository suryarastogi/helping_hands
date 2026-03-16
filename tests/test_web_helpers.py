"""Tests for internal helper functions in helping_hands.lib.meta.tools.web."""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools.web import (
    _as_string_keyed_dict,
    _decode_bytes,
    _require_http_url,
    _strip_html,
)


class TestRequireHttpUrl:
    def test_accepts_http(self) -> None:
        assert _require_http_url("http://example.com") == "http://example.com"

    def test_accepts_https(self) -> None:
        assert _require_http_url("https://example.com") == "https://example.com"

    def test_strips_whitespace(self) -> None:
        assert _require_http_url("  https://example.com  ") == "https://example.com"

    def test_rejects_ftp(self) -> None:
        with pytest.raises(ValueError, match="http or https"):
            _require_http_url("ftp://example.com")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            _require_http_url("")

    def test_rejects_no_host(self) -> None:
        with pytest.raises(ValueError, match="host"):
            _require_http_url("http://")


class TestDecodeBytes:
    def test_utf8(self) -> None:
        assert _decode_bytes(b"hello") == "hello"

    def test_utf16(self) -> None:
        text = "unicode test"
        assert _decode_bytes(text.encode("utf-16")) == text

    def test_latin1_fallback(self) -> None:
        raw = bytes([0xE9, 0xE8, 0xEA])  # latin-1 accented chars
        result = _decode_bytes(raw)
        assert isinstance(result, str)
        assert len(result) == 3


class TestStripHtml:
    def test_removes_script_tags(self) -> None:
        html = "<html><script>alert('xss')</script><body>hello</body></html>"
        assert "alert" not in _strip_html(html)
        assert "hello" in _strip_html(html)

    def test_removes_style_tags(self) -> None:
        html = "<html><style>.red{color:red}</style><p>text</p></html>"
        assert "color" not in _strip_html(html)
        assert "text" in _strip_html(html)

    def test_unescapes_entities(self) -> None:
        assert "&" in _strip_html("<p>&amp;</p>")

    def test_normalizes_whitespace(self) -> None:
        html = "<p>a</p>   <p>b</p>"
        result = _strip_html(html)
        assert "  " not in result  # no double spaces


class TestAsStringKeyedDict:
    def test_accepts_valid_dict(self) -> None:
        d = {"key": "value", "num": 42}
        assert _as_string_keyed_dict(d) == d

    def test_rejects_non_dict(self) -> None:
        assert _as_string_keyed_dict([1, 2, 3]) is None
        assert _as_string_keyed_dict("string") is None

    def test_rejects_non_string_keys(self) -> None:
        assert _as_string_keyed_dict({1: "value"}) is None

    def test_empty_dict_accepted(self) -> None:
        assert _as_string_keyed_dict({}) == {}
