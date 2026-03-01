"""Web browsing and search helpers for tool-enabled hands."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import unescape
from typing import cast
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class WebSearchItem:
    """One web search hit."""

    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class WebSearchResult:
    """Structured web search result collection."""

    query: str
    results: list[WebSearchItem]


@dataclass(frozen=True)
class WebBrowseResult:
    """Fetched web page content."""

    url: str
    final_url: str
    status_code: int | None
    content: str
    truncated: bool


_DEFAULT_USER_AGENT = (
    "helping_hands/0.1 (+https://github.com/suryarastogi/helping_hands)"
)


def _require_http_url(url: str) -> str:
    """Validate that *url* uses ``http``/``https`` and has a host."""
    candidate = url.strip()
    if not candidate:
        raise ValueError("url must be non-empty")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http or https")
    if not parsed.netloc:
        raise ValueError("url must include host")
    return candidate


def _decode_bytes(payload: bytes) -> str:
    """Decode *payload* trying UTF-8, UTF-16, then Latin-1 in order."""
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _strip_html(raw_html: str) -> str:
    """Remove HTML tags, scripts, and styles; return cleaned plain text."""
    text = re.sub(
        r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>",
        " ",
        raw_html,
    )
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text.replace("\r", "\n"))
    return text.strip()


def _as_string_keyed_dict(value: object) -> dict[str, object] | None:
    """Return *value* as a ``dict[str, object]`` if it is one, else ``None``."""
    if not isinstance(value, dict):
        return None
    if any(not isinstance(key, str) for key in value):
        return None
    return cast(dict[str, object], value)


def _extract_related_topics(
    items: Sequence[object], output: list[WebSearchItem]
) -> None:
    """Recursively extract DuckDuckGo related-topic entries into *output*."""
    for item in items:
        record = _as_string_keyed_dict(item)
        if record is None:
            continue
        topics = record.get("Topics")
        if isinstance(topics, list):
            _extract_related_topics(topics, output)
            continue
        text = record.get("Text")
        url = record.get("FirstURL")
        if (
            isinstance(text, str)
            and isinstance(url, str)
            and text.strip()
            and url.strip()
        ):
            output.append(
                WebSearchItem(title=text.strip(), url=url.strip(), snippet=text.strip())
            )


def search_web(
    query: str,
    *,
    max_results: int = 5,
    timeout_s: int = 20,
) -> WebSearchResult:
    """Run a lightweight web search using DuckDuckGo's JSON endpoint."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must be non-empty")
    if max_results <= 0:
        raise ValueError("max_results must be > 0")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")

    params = urlencode(
        {
            "q": normalized_query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
    )
    url = f"https://api.duckduckgo.com/?{params}"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _DEFAULT_USER_AGENT},
    )
    with urlopen(request, timeout=timeout_s) as response:
        payload = response.read()
    data = json.loads(_decode_bytes(payload))
    record = _as_string_keyed_dict(data)
    if record is None:
        raise RuntimeError("unexpected search response format")

    results: list[WebSearchItem] = []
    abstract_text = record.get("AbstractText")
    abstract_url = record.get("AbstractURL")
    heading = record.get("Heading")
    if isinstance(abstract_text, str) and abstract_text.strip():
        results.append(
            WebSearchItem(
                title=str(heading or "DuckDuckGo result").strip(),
                url=str(abstract_url or "").strip(),
                snippet=abstract_text.strip(),
            )
        )

    related = record.get("RelatedTopics")
    if isinstance(related, list):
        _extract_related_topics(related, results)

    deduped: list[WebSearchItem] = []
    seen_urls: set[str] = set()
    for item in results:
        if not item.url or item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        deduped.append(item)
        if len(deduped) >= max_results:
            break

    return WebSearchResult(query=normalized_query, results=deduped)


def browse_url(
    url: str,
    *,
    max_chars: int = 12000,
    timeout_s: int = 20,
) -> WebBrowseResult:
    """Fetch and text-extract a web page for tool consumption."""
    normalized_url = _require_http_url(url)
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")

    request = Request(normalized_url, headers={"User-Agent": _DEFAULT_USER_AGENT})
    with urlopen(request, timeout=timeout_s) as response:
        payload = response.read()
        final_url = response.geturl()
        status = getattr(response, "status", None)
        content_type = str(response.headers.get("Content-Type", "")).lower()

    decoded = _decode_bytes(payload)
    if "html" in content_type or "<html" in decoded.lower():
        extracted = _strip_html(decoded)
    else:
        extracted = decoded.strip()

    truncated = False
    if len(extracted) > max_chars:
        extracted = extracted[:max_chars]
        truncated = True

    return WebBrowseResult(
        url=normalized_url,
        final_url=final_url,
        status_code=status,
        content=extracted,
        truncated=truncated,
    )
