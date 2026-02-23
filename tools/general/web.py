"""
tools/general/web.py

Implements three GENERAL-family web tools:
  - web.search  : Search the web via Brave, falling back to Tavily.
  - web.fetch   : Fetch and clean a single URL.
  - web.read_site: BFS crawl of a single domain.

Importing this module automatically registers all three tools.
"""

import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
FETCH_MAX_CHARS = 50_000
CRAWL_EXCERPT_CHARS = 2_000
CRAWL_RATE_LIMIT_S = 0.5  # 500 ms between requests


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
    )


def _clean_html(html: str) -> tuple[str, str]:
    """
    Parse raw HTML, strip script/style tags, and return (title, cleaned_text).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove script and style elements
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    return title, cleaned


def _fetch_url(url: str, timeout: float = 15.0) -> tuple[str, str]:
    """
    Fetch a URL with httpx and return (title, cleaned_text).
    Raises httpx.HTTPError or other exceptions on failure.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AliceBot/1.0; +https://alice.local)"
        )
    }
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        title, text = _clean_html(response.text)
        return title, text


# ---------------------------------------------------------------------------
# Tool: web.search
# ---------------------------------------------------------------------------


def web_search(request: ToolRequest) -> ToolResult:
    """
    Search the web.

    Args (in request.args):
        q      (str) : Search query. Required.
        count  (int) : Number of results to return. Default 10.
    """
    tool_name = "web.search"
    q = request.args.get("q", "").strip()
    if not q:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'q' argument is required and must not be empty.")

    count = int(request.args.get("count", 10))
    results: list[dict] = []
    sources_used: list[str] = []
    notes: list[str] = []

    # --- Attempt 1: Brave Search ---
    brave_api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "")
    brave_ok = False

    if brave_api_key:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    BRAVE_SEARCH_URL,
                    headers={"X-Subscription-Token": brave_api_key},
                    params={"q": q, "count": count},
                )
                resp.raise_for_status()
                data = resp.json()

            web_results = data.get("web", {}).get("results", [])
            if web_results:
                for item in web_results:
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", ""),
                        }
                    )
                sources_used.append(BRAVE_SEARCH_URL)
                brave_ok = True
            else:
                notes.append("Brave returned no results; falling back to Tavily.")
        except Exception as exc:
            notes.append(f"Brave search failed ({type(exc).__name__}: {exc}); falling back to Tavily.")
    else:
        notes.append("BRAVE_SEARCH_API_KEY not set; falling back to Tavily.")

    # --- Attempt 2: Tavily fallback ---
    if not brave_ok:
        tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        if not tavily_api_key:
            return _make_err(
                tool_name,
                ToolFailureClass.UPSTREAM_ERROR,
                "Brave search unavailable and TAVILY_API_KEY is not set. Cannot perform search.",
            )
        try:
            from tavily import TavilyClient  # type: ignore

            client = TavilyClient(api_key=tavily_api_key)
            response = client.search(query=q, max_results=count)
            tavily_results = response.get("results", [])
            for item in tavily_results:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),
                    }
                )
            sources_used.append("https://api.tavily.com")
            notes.append("Results provided by Tavily fallback.")
        except Exception as exc:
            return _make_err(
                tool_name,
                ToolFailureClass.UPSTREAM_ERROR,
                f"Both Brave and Tavily search failed. Tavily error: {type(exc).__name__}: {exc}",
            )

    if not results:
        return _make_err(
            tool_name,
            ToolFailureClass.UPSTREAM_ERROR,
            "Search completed but returned no results from any provider.",
        )

    return _make_ok(
        tool_name=tool_name,
        primary=results,
        sources=sources_used,
        notes="; ".join(notes) if notes else None,
    )


# ---------------------------------------------------------------------------
# Tool: web.fetch
# ---------------------------------------------------------------------------


def web_fetch(request: ToolRequest) -> ToolResult:
    """
    Fetch and clean a single web page.

    Args (in request.args):
        url (str): The URL to fetch. Required.
    """
    tool_name = "web.fetch"
    url = request.args.get("url", "").strip()
    if not url:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'url' argument is required and must not be empty.")

    try:
        title, text = _fetch_url(url)
    except httpx.TimeoutException:
        return _make_err(tool_name, ToolFailureClass.TIMEOUT, f"Request to '{url}' timed out.")
    except httpx.HTTPStatusError as exc:
        return _make_err(
            tool_name,
            ToolFailureClass.UPSTREAM_ERROR,
            f"HTTP {exc.response.status_code} fetching '{url}'.",
        )
    except Exception as exc:
        return _make_err(
            tool_name,
            ToolFailureClass.UPSTREAM_ERROR,
            f"Failed to fetch '{url}': {type(exc).__name__}: {exc}",
        )

    capped_text = text[:FETCH_MAX_CHARS]
    notes = None
    if len(text) > FETCH_MAX_CHARS:
        notes = f"Content truncated to {FETCH_MAX_CHARS} characters."

    return _make_ok(
        tool_name=tool_name,
        primary={"title": title, "text": capped_text},
        sources=[url],
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Tool: web.read_site
# ---------------------------------------------------------------------------


def web_read_site(request: ToolRequest) -> ToolResult:
    """
    BFS crawl of a single domain.

    Args (in request.args):
        url        (str): Seed URL. Required.
        max_pages  (int): Maximum number of pages to crawl. Default 10.
        max_depth  (int): Maximum BFS depth from seed. Default 3.
    """
    tool_name = "web.read_site"
    seed_url = request.args.get("url", "").strip()
    if not seed_url:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'url' argument is required and must not be empty.")

    max_pages = int(request.args.get("max_pages", 10))
    max_depth = int(request.args.get("max_depth", 3))

    parsed_seed = urlparse(seed_url)
    allowed_netloc = parsed_seed.netloc

    if not allowed_netloc:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Could not determine domain from seed URL '{seed_url}'.")

    visited: set[str] = set()
    # Queue entries: (url, depth)
    queue: deque[tuple[str, int]] = deque()
    queue.append((seed_url, 0))
    pages: list[dict] = []
    crawled_urls: list[str] = []

    while queue and len(pages) < max_pages:
        current_url, depth = queue.popleft()

        if current_url in visited:
            continue
        visited.add(current_url)

        # Rate limit
        if crawled_urls:  # skip delay before the very first request
            time.sleep(CRAWL_RATE_LIMIT_S)

        try:
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; AliceBot/1.0; +https://alice.local)"
                    )
                }
                resp = client.get(current_url, headers=headers)
                resp.raise_for_status()
                html = resp.text
        except Exception:
            # Skip pages that fail; don't abort the whole crawl
            continue

        _, text = _clean_html(html)
        excerpt = text[:CRAWL_EXCERPT_CHARS]

        pages.append({"url": current_url, "excerpt": excerpt})
        crawled_urls.append(current_url)

        # Enqueue same-domain links if we haven't hit max depth
        if depth < max_depth:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                absolute = urljoin(current_url, href)
                parsed = urlparse(absolute)
                # Only follow http/https links on the same domain
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.netloc != allowed_netloc:
                    continue
                # Strip fragment
                clean = parsed._replace(fragment="").geturl()
                if clean not in visited:
                    queue.append((clean, depth + 1))

    if not pages:
        return _make_err(
            tool_name,
            ToolFailureClass.UPSTREAM_ERROR,
            f"Crawl of '{seed_url}' yielded no accessible pages.",
        )

    return _make_ok(
        tool_name=tool_name,
        primary=pages,
        sources=crawled_urls,
        notes=f"Crawled {len(pages)} page(s) within domain '{allowed_netloc}'.",
    )


# ---------------------------------------------------------------------------
# Registration — runs automatically on import
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="web.search",
    family=ToolFamily.GENERAL,
    description=(
        "Search the web for a query. Uses Brave Search with Tavily as fallback. "
        "Args: q (str, required), count (int, default 10). "
        "Returns a list of {title, url, snippet} dicts."
    ),
))

register_tool(ToolDef(
    name="web.fetch",
    family=ToolFamily.GENERAL,
    description=(
        "Fetch and clean a single web page. Strips scripts/styles and returns plain text. "
        "Args: url (str, required). "
        "Returns {title, text} with text capped at 50,000 characters."
    ),
))

register_tool(ToolDef(
    name="web.read_site",
    family=ToolFamily.GENERAL,
    description=(
        "BFS crawl of a single domain starting from a seed URL. "
        "Args: url (str, required), max_pages (int, default 10), max_depth (int, default 3). "
        "Returns a list of {url, excerpt} dicts with 2,000-character excerpts."
    ),
))
