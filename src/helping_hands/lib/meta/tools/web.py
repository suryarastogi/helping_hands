"""Web browsing and search helpers for tool-enabled hands."""

from __future__ import annotations

__all__ = [
    "DEFAULT_BROWSE_MAX_CHARS",
    "DEFAULT_SEARCH_MAX_RESULTS",
    "WebBrowseResult",
    "WebSearchItem",
    "WebSearchResult",
    "browse_url",
    "search_web",
]

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import unescape
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from helping_hands.lib.validation import require_non_empty_string, require_positive_int

logger = logging.getLogger(__name__)

DEFAULT_BROWSE_MAX_CHARS = 12000
"""Default maximum characters returned when browsing a web page."""

DEFAULT_SEARCH_MAX_RESULTS = 5
"""Default maximum number of results returned by web search."""


@dataclass(frozen=True)
class WebSearchItem:
    """One web search hit.

    Attributes:
        title: Display title of the search result.
        url: Canonical URL of the result page.
        snippet: Short text excerpt describing the result.
    """

    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class WebSearchResult:
    """Structured web search result collection.

    Attributes:
        query: Normalised search query that was executed.
        results: Deduplicated search hits, up to ``max_results``.
    """

    query: str
    results: list[WebSearchItem]


@dataclass(frozen=True)
class WebBrowseResult:
    """Fetched web page content.

    Attributes:
        url: Requested URL (after whitespace trimming and scheme validation).
        final_url: URL after any redirects.
        status_code: HTTP status code, or ``None`` if unavailable.
        content: Extracted plain-text content (HTML tags stripped).
        truncated: Whether the content was cut to ``max_chars``.
    """

    url: str
    final_url: str
    status_code: int | None
    content: str
    truncated: bool


_DEFAULT_USER_AGENT = (
    "helping_hands/0.1 (+https://github.com/suryarastogi/helping_hands)"
)

_DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"
"""Base URL for the DuckDuckGo Instant Answer API."""

_DEFAULT_WEB_TIMEOUT_S = 20
"""Default timeout in seconds for web search and browse requests."""

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
"""Compiled regex matching ``<script>``, ``<style>``, and ``<noscript>`` blocks."""

_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
"""Compiled regex matching any HTML tag."""

_HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
"""Compiled regex matching runs of horizontal whitespace."""

_BLANK_LINES_RE = re.compile(r"\n\s*\n+")
"""Compiled regex matching multiple consecutive blank lines."""

_ENCODING_FALLBACK_CHAIN = ("utf-8", "utf-16", "latin-1")
"""Ordered encodings tried when decoding web response bytes.

UTF-8 is tried first (most common), then UTF-16, then latin-1 which accepts
all byte values and therefore always succeeds.
"""


def _raise_url_error(
    exc: HTTPError | URLError,
    *,
    operation: str,
) -> None:
    """Convert a :class:`~urllib.error.HTTPError` or :class:`~urllib.error.URLError` to a :class:`RuntimeError`.

    Args:
        exc: The caught URL/HTTP exception.
        operation: Short label for the failed operation (e.g. ``"search"``
            or ``"browse"``), used in log and error messages.

    Raises:
        RuntimeError: Always raised with a human-readable message.
    """
    if isinstance(exc, HTTPError):
        logger.debug("%s request HTTP error: %s", operation, exc, exc_info=True)
        raise RuntimeError(
            f"{operation} request failed with HTTP {exc.code}: {exc.reason}"
        ) from exc
    logger.debug("%s request URL error: %s", operation, exc, exc_info=True)
    raise RuntimeError(f"{operation} request failed: {exc.reason}") from exc


def _require_http_url(url: str) -> str:
    """Validate and normalise a URL to an HTTP/HTTPS scheme.

    Args:
        url: Raw URL string (leading/trailing whitespace is stripped).

    Returns:
        The stripped URL if it uses ``http`` or ``https`` and includes a host.

    Raises:
        TypeError: If *url* is not a string.
        ValueError: If the URL is empty, uses a non-HTTP scheme, or lacks a
            host component.
    """
    candidate = require_non_empty_string(url, "url")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http or https")
    if not parsed.netloc:
        raise ValueError("url must include host")
    return candidate


def _decode_bytes(payload: bytes) -> str:
    """Decode bytes trying UTF-8, UTF-16, then latin-1 (which accepts all byte values)."""
    for encoding in _ENCODING_FALLBACK_CHAIN:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    # latin-1 accepts all byte values so we always return above, but keep
    # a safe fallback for defensive completeness.
    return payload.decode("utf-8", errors="replace")  # pragma: no cover


def _strip_html(raw_html: str) -> str:
    """Remove HTML markup and collapse whitespace to produce plain text.

    Strips ``<script>``, ``<style>``, and ``<noscript>`` blocks entirely,
    removes remaining tags, unescapes HTML entities, and normalises
    whitespace.

    Args:
        raw_html: Raw HTML source string.

    Returns:
        Cleaned plain-text content with collapsed whitespace.
    """
    text = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    text = _HTML_TAG_RE.sub(" ", text)
    text = unescape(text)
    text = _HORIZONTAL_WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text.replace("\r", "\n"))
    return text.strip()


def _as_string_keyed_dict(value: object) -> dict[str, object] | None:
    """Narrow an arbitrary value to a string-keyed dict, or return None.

    Args:
        value: Any Python object to check.

    Returns:
        The same dict cast to ``dict[str, object]`` if *value* is a dict
        with all-string keys, otherwise ``None``.
    """
    if not isinstance(value, dict):
        return None
    if any(not isinstance(key, str) for key in value):
        return None
    return cast(dict[str, object], value)


def _extract_related_topics(
    items: Sequence[object], output: list[WebSearchItem]
) -> None:
    """Recursively extract search hits from DuckDuckGo RelatedTopics.

    DuckDuckGo nests topics in sub-lists (``Topics`` key); this function
    flattens them into a single output list.

    Args:
        items: Sequence of topic dicts (or nested sub-topic lists) from the
            DuckDuckGo API response.
        output: Mutable list to which extracted ``WebSearchItem`` instances
            are appended in-place.
    """
    for item in items:
        record = _as_string_keyed_dict(item)
        if record is None:
            continue
        topics = record.get("Topics")
        if isinstance(topics, list):
            _extract_related_topics(topics, output)
            continue
        raw_text = record.get("Text")
        raw_url = record.get("FirstURL")
        if isinstance(raw_text, str) and isinstance(raw_url, str):
            text = raw_text.strip()
            url = raw_url.strip()
            if text and url:
                output.append(WebSearchItem(title=text, url=url, snippet=text))


def search_web(
    query: str,
    *,
    max_results: int = DEFAULT_SEARCH_MAX_RESULTS,
    timeout_s: int = _DEFAULT_WEB_TIMEOUT_S,
) -> WebSearchResult:
    """Run a lightweight web search using DuckDuckGo's JSON endpoint."""
    normalized_query = require_non_empty_string(query, "query")
    require_positive_int(max_results, "max_results")
    require_positive_int(timeout_s, "timeout_s")

    params = urlencode(
        {
            "q": normalized_query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
    )
    url = f"{_DUCKDUCKGO_API_URL}?{params}"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _DEFAULT_USER_AGENT},
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            payload = response.read()
    except (HTTPError, URLError) as exc:
        _raise_url_error(exc, operation="search")
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
    max_chars: int = DEFAULT_BROWSE_MAX_CHARS,
    timeout_s: int = _DEFAULT_WEB_TIMEOUT_S,
) -> WebBrowseResult:
    """Fetch and text-extract a web page for tool consumption."""
    normalized_url = _require_http_url(url)
    require_positive_int(max_chars, "max_chars")
    require_positive_int(timeout_s, "timeout_s")

    request = Request(normalized_url, headers={"User-Agent": _DEFAULT_USER_AGENT})
    try:
        with urlopen(request, timeout=timeout_s) as response:
            payload = response.read()
            final_url = response.geturl()
            status = response.status
            content_type = str(response.headers.get("Content-Type", "")).lower()
    except (HTTPError, URLError) as exc:
        _raise_url_error(exc, operation="browse")

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
