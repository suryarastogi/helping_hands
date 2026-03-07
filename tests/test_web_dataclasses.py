"""Tests for web.py dataclass construction and _decode_bytes edge cases."""

from __future__ import annotations

import pytest

from helping_hands.lib.meta.tools.web import (
    WebBrowseResult,
    WebSearchItem,
    WebSearchResult,
    _decode_bytes,
)

# ===================================================================
# WebSearchItem — frozen dataclass construction
# ===================================================================


class TestWebSearchItemConstruction:
    def test_basic_construction(self) -> None:
        item = WebSearchItem(title="T", url="https://a.com", snippet="S")
        assert item.title == "T"
        assert item.url == "https://a.com"
        assert item.snippet == "S"

    def test_frozen_immutability(self) -> None:
        item = WebSearchItem(title="T", url="https://a.com", snippet="S")
        with pytest.raises(AttributeError):
            item.title = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = WebSearchItem(title="T", url="https://a.com", snippet="S")
        b = WebSearchItem(title="T", url="https://a.com", snippet="S")
        assert a == b

    def test_inequality_different_fields(self) -> None:
        a = WebSearchItem(title="T", url="https://a.com", snippet="S")
        b = WebSearchItem(title="T", url="https://b.com", snippet="S")
        assert a != b

    def test_hashable_for_set(self) -> None:
        a = WebSearchItem(title="T", url="https://a.com", snippet="S")
        b = WebSearchItem(title="T", url="https://a.com", snippet="S")
        assert len({a, b}) == 1


# ===================================================================
# WebSearchResult — frozen dataclass construction
# ===================================================================


class TestWebSearchResultConstruction:
    def test_basic_construction(self) -> None:
        items = [WebSearchItem(title="T", url="https://a.com", snippet="S")]
        result = WebSearchResult(query="test", results=items)
        assert result.query == "test"
        assert len(result.results) == 1

    def test_empty_results(self) -> None:
        result = WebSearchResult(query="nothing", results=[])
        assert result.results == []
        assert result.query == "nothing"

    def test_frozen_immutability(self) -> None:
        result = WebSearchResult(query="q", results=[])
        with pytest.raises(AttributeError):
            result.query = "changed"  # type: ignore[misc]


# ===================================================================
# WebBrowseResult — frozen dataclass construction
# ===================================================================


class TestWebBrowseResultConstruction:
    def test_basic_construction(self) -> None:
        result = WebBrowseResult(
            url="https://a.com",
            final_url="https://a.com/redirect",
            status_code=200,
            content="Hello",
            truncated=False,
        )
        assert result.url == "https://a.com"
        assert result.final_url == "https://a.com/redirect"
        assert result.status_code == 200
        assert result.content == "Hello"
        assert result.truncated is False

    def test_none_status_code(self) -> None:
        result = WebBrowseResult(
            url="https://a.com",
            final_url="https://a.com",
            status_code=None,
            content="text",
            truncated=False,
        )
        assert result.status_code is None

    def test_truncated_flag(self) -> None:
        result = WebBrowseResult(
            url="https://a.com",
            final_url="https://a.com",
            status_code=200,
            content="x" * 100,
            truncated=True,
        )
        assert result.truncated is True

    def test_frozen_immutability(self) -> None:
        result = WebBrowseResult(
            url="https://a.com",
            final_url="https://a.com",
            status_code=200,
            content="c",
            truncated=False,
        )
        with pytest.raises(AttributeError):
            result.content = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        kwargs = dict(
            url="https://a.com",
            final_url="https://a.com",
            status_code=200,
            content="c",
            truncated=False,
        )
        assert WebBrowseResult(**kwargs) == WebBrowseResult(**kwargs)


# ===================================================================
# _decode_bytes — edge cases
# ===================================================================


class TestDecodeBytesEdgeCases:
    def test_empty_bytes(self) -> None:
        assert _decode_bytes(b"") == ""

    def test_pure_ascii(self) -> None:
        assert _decode_bytes(b"ascii text 123") == "ascii text 123"

    def test_utf8_with_bom(self) -> None:
        bom = b"\xef\xbb\xbf"
        result = _decode_bytes(bom + b"hello")
        assert "hello" in result

    def test_utf8_multibyte(self) -> None:
        text = "cafe\u0301 \u2603 \U0001f600"
        assert _decode_bytes(text.encode("utf-8")) == text

    def test_utf16_with_bom(self) -> None:
        text = "hello world"
        encoded = text.encode("utf-16")  # includes BOM
        result = _decode_bytes(encoded)
        assert result == text

    def test_latin1_high_bytes(self) -> None:
        raw = bytes(range(128, 256))
        result = _decode_bytes(raw)
        assert isinstance(result, str)
        assert len(result) > 0
