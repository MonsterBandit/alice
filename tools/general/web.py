from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_tool(ToolDef(name="web.search", family=ToolFamily.GENERAL, description="Search the web using DuckDuckGo."))
register_tool(ToolDef(name="web.fetch", family=ToolFamily.GENERAL, description="Fetch and return the raw content of a URL."))
register_tool(ToolDef(name="web.read_site", family=ToolFamily.GENERAL, description="Fetch a URL and return cleaned readable text."))

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ok(tool_name: str, primary: Any, sources: list[str], notes: str | None = None) -> ToolResult:
    return ToolResult(
        ok=True,
        tool_name=tool_name,
        primary=primary,
        provenance=ToolProvenance(
            sources=sources,
            retrieved_at=_now_iso(),
            notes=notes,
        ),
        failure_class=None,
        failure_message=None,
        latency_ms=0.0,  # will be overwritten by executor
    )


def _make_err(tool_name: str, failure_class: ToolFailureClass, message: str) -> ToolResult:
    return ToolResult(
        ok=False,
        tool_name=tool_name,
        primary=None,
        provenance=ToolProvenance(
            sources=[],
            retrieved_at=_now_iso(),
            notes="Tool did not execute successfully.",
        ),
        failure_class=failure_class,
        failure_message=message,
        latency_ms=0.0,  # will be overwritten by executor
    )


def _clean_html(html: str) -> tuple[str, str]:
    """Return (title, readable_text) from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return title, text


def _fetch_url(url: str, timeout: float = 15.0) -> tuple[str, str]:
    """Return (final_url, html). Raises httpx.HTTPError on failure."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AliceBot/1.0)"}
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return str(response.url), response.text

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def web_search(request: ToolRequest) -> ToolResult:
    query = (request.args or {}).get("query", "").strip()
    if not query:
        return _make_err("web.search", ToolFailureClass.BAD_INPUT, "Missing required param: 'query'.")

    search_url = f"https://html.duckduckgo.com/html/?q={httpx.URL('').copy_with(params={'q': query}).params}"

    try:
        final_url, html = _fetch_url(search_url)
    except httpx.HTTPError as e:
        return _make_err("web.search", ToolFailureClass.NETWORK_ERROR, f"Search request failed: {e}")

    soup = BeautifulSoup(html, "html.parser")
    results = []
    for result in soup.select(".result"):
        title_tag = result.select_one(".result__title a")
        snippet_tag = result.select_one(".result__snippet")
        url_tag = result.select_one(".result__url")
        if title_tag:
            results.append({
                "title": title_tag.get_text(strip=True),
                "url": url_tag.get_text(strip=True) if url_tag else "",
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
            })

    if not results:
        return _make_err("web.search", ToolFailureClass.NO_RESULTS, f"No results found for query: '{query}'.")

    return _make_ok("web.search", results, sources=[final_url], notes=f"Query: {query}")


def web_fetch(request: ToolRequest) -> ToolResult:
    url = (request.args or {}).get("url", "").strip()
    if not url:
        return _make_err("web.fetch", ToolFailureClass.BAD_INPUT, "Missing required param: 'url'.")

    try:
        final_url, html = _fetch_url(url)
    except httpx.HTTPError as e:
        return _make_err("web.fetch", ToolFailureClass.NETWORK_ERROR, f"Fetch failed for '{url}': {e}")

    return _make_ok("web.fetch", html, sources=[final_url])


def web_read_site(request: ToolRequest) -> ToolResult:
    url = (request.args or {}).get("url", "").strip()
    if not url:
        return _make_err("web.read_site", ToolFailureClass.BAD_INPUT, "Missing required param: 'url'.")

    try:
        final_url, html = _fetch_url(url)
    except httpx.HTTPError as e:
        return _make_err("web.read_site", ToolFailureClass.NETWORK_ERROR, f"Fetch failed for '{url}': {e}")

    title, text = _clean_html(html)
    return _make_ok("web.read_site", {"title": title, "text": text}, sources=[final_url])

# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_HANDLERS = {
    "web.search": web_search,
    "web.fetch": web_fetch,
    "web.read_site": web_read_site,
}


def dispatch(request: ToolRequest) -> ToolResult:
    """
    Route a ToolRequest to the correct web tool handler by tool_name.
    Raises NotImplementedError for unknown tool names so the executor
    can catch it and return a clean error result.
    """
    handler = _HANDLERS.get(request.tool_name)
    if handler is None:
        raise NotImplementedError(
            f"No handler registered in tools.general.web for tool '{request.tool_name}'."
        )
    return handler(request)
