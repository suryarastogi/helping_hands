# Web Tools

DuckDuckGo search integration, URL browsing, HTML extraction, and content
truncation for tool-enabled hands.

## Context

Iterative hands can optionally invoke web tools (`web.search`, `web.browse`)
to fetch external information during an AI agent loop.  These tools need to be
lightweight (no heavy browser dependencies), safe (validate URLs), and
size-bounded (truncate large pages) so responses fit within model context
windows.

## Design

### Public API

The module exposes two top-level functions and three frozen dataclasses:

| Symbol | Kind | Purpose |
|---|---|---|
| `search_web()` | function | Query DuckDuckGo's JSON API |
| `browse_url()` | function | Fetch and text-extract a web page |
| `WebSearchItem` | dataclass | Single search hit (title, url, snippet) |
| `WebSearchResult` | dataclass | Collection of search hits with original query |
| `WebBrowseResult` | dataclass | Fetched page content with metadata |

All dataclasses are `frozen=True` for immutability and hashability.

### Search implementation

`search_web()` uses DuckDuckGo's public JSON endpoint
(`https://api.duckduckgo.com/?format=json`).  No API key is required.

Response parsing extracts results from two sources:

1. **Abstract** — the `AbstractText` / `AbstractURL` / `Heading` fields provide
   a single top-level result when available.
2. **Related Topics** — the `RelatedTopics` array contains nested topic objects.
   `_extract_related_topics()` recursively descends into `Topics` sub-arrays,
   extracting `Text` + `FirstURL` pairs.

Results are deduplicated by URL and capped at `max_results`.

### Browse implementation

`browse_url()` fetches a URL via `urllib.request.urlopen` with a custom
user-agent string.  Content processing:

1. **Encoding detection** — `_decode_bytes()` tries UTF-8, then UTF-16, then
   Latin-1 (which accepts all byte values).  The fallback chain means decoding
   never fails.
2. **HTML detection** — if the Content-Type header contains `"html"` or the
   decoded body contains `<html`, the content is treated as HTML.
3. **HTML stripping** — `_strip_html()` removes `<script>`, `<style>`, and
   `<noscript>` blocks first, then strips remaining tags, unescapes HTML
   entities, and collapses whitespace.
4. **Truncation** — output is capped at `max_chars` (default 12,000).  The
   `truncated` flag in the result indicates whether content was cut.

### URL validation

`_require_http_url()` enforces that URLs use `http://` or `https://` schemes
and include a host.  Whitespace is stripped.  This prevents file:// or
javascript: URLs from reaching `urlopen`.

### Integration with hands

Web tools are opt-in.  The iterative hand checks `_web_tools_enabled()` before
including web tool runners in the dispatch map.  The tool registry
(`meta/tools/registry.py`) maps `"web.search"` and `"web.browse"` to the
corresponding functions via `build_tool_runner_map()`.

Tool instructions injected into the system prompt document the `@@TOOL`
syntax for invoking web tools:

```
@@TOOL web.search {"query": "..."}
@@TOOL web.browse {"url": "https://..."}
```

## Alternatives considered

- **Headless browser (Playwright/Selenium)** — rejected for being a heavy
  dependency.  `urllib` + HTML stripping covers the common case of extracting
  text content from documentation and reference pages.
- **Google Custom Search API** — requires API keys and billing.  DuckDuckGo's
  JSON endpoint is free and keyless.
- **BeautifulSoup HTML parsing** — would add a dependency for marginal benefit
  over regex-based tag stripping for the text extraction use case.

## Key source files

- `src/helping_hands/lib/meta/tools/web.py` — search/browse implementation
- `src/helping_hands/lib/meta/tools/registry.py` — tool registration and dispatch
- `src/helping_hands/lib/hands/v1/hand/iterative.py` — `_web_tools_enabled()`, `@@TOOL` dispatch
