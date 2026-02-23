import os
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
    tool_name = "web.search"
    q = request.args.get("q", "").strip()
    if not q:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'q' argument is required.")
    count = int(request.args.get("count", 10))
    results = []
    sources_used = []
    notes = []
    brave_api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    brave_ok = False
    if brave_api_key:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get("https://api.search.brave.com/res/v1/web/search", headers={"X-Subscription-Token": brave_api_key}, params={"q": q, "count": count})
                resp.raise_for_status()
                data = resp.json()
            web_results = data.get("web", {}).get("results", [])
            if web_results:
                for item in web_results:
                    results.append({"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("description", "")})
                sources_used.append("https://api.search.brave.com")
                brave_ok = True
            else:
                notes.append("Brave returned no results; falling back to Tavily.")
        except Exception as exc:
            notes.append(f"Brave failed ({exc}); falling back to Tavily.")
    else:
        notes.append("BRAVE_SEARCH_API_KEY not set; falling back to Tavily.")
    if not brave_ok:
        tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        if not tavily_api_key:
            return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, "Both Brave and Tavily unavailable.")
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_api_key)
            response = client.search(query=q, max_results=count)
            for item in response.get("results", []):
                results.append({"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("content", "")})
            sources_used.append("https://api.tavily.com")
            notes.append("Results from Tavily fallback.")
        except Exception as exc:
            return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, f"Both search providers failed. Tavily: {exc}")
    if not results:
        return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, "No results from any provider.")
    return _make_ok(tool_name=tool_name, primary=results, sources=sources_used, notes="; ".join(notes) if notes else None)


def web_fetch(request: ToolRequest) -> ToolResult:
    url = (request.args or {}).get("url", "").strip()
    if not url:
        return _make_err("web.fetch", ToolFailureClass.BAD_INPUT, "Missing required param: 'url'.")

    try:
        final_url, html = _fetch_url(url)
    except httpx.HTTPError as e:
        return _make_err("web.fetch", ToolFailureClass.UPSTREAM_ERROR, f"Fetch failed for '{url}': {e}")

    return _make_ok("web.fetch", html, sources=[final_url])


def web_read_site(request: ToolRequest) -> ToolResult:
    url = (request.args or {}).get("url", "").strip()
    if not url:
        return _make_err("web.read_site", ToolFailureClass.BAD_INPUT, "Missing required param: 'url'.")

    try:
        final_url, html = _fetch_url(url)
    except httpx.HTTPError as e:
        return _make_err("web.read_site", ToolFailureClass.UPSTREAM_ERROR, f"Fetch failed for '{url}': {e}")

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
