import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult
import tools.general.web as web_module

# ---------------------------------------------------------------------------
# Register tools
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="research.fetch_trusted",
    family=ToolFamily.RESEARCH,
    description=(
        "Fetch a URL and return its content only if the domain is in the trusted sources list. "
        "Args: url (str)."
    ),
))

register_tool(ToolDef(
    name="research.search_trusted",
    family=ToolFamily.RESEARCH,
    description=(
        "Run a web search and return only results from trusted domains. "
        "Args: q (str)."
    ),
))

# ---------------------------------------------------------------------------
# Trusted domain loading
# ---------------------------------------------------------------------------

_TRUSTED_SOURCES_PATH = "/opt/alice/heart/soul/trusted_sources.md"
_trusted_domains: list[str] | None = None


def _load_trusted_domains() -> list[str]:
    """
    Parse /opt/alice/heart/soul/trusted_sources.md and return a list of
    lowercase domain strings.

    The parser accepts lines in any of these forms (ignoring markdown noise):
        - https://example.com
        - example.com
        - * example.com
        - | example.com | ... |
    Any token that looks like a domain (contains a dot, no spaces) is kept.
    """
    global _trusted_domains
    if _trusted_domains is not None:
        return _trusted_domains

    try:
        with open(_TRUSTED_SOURCES_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        _trusted_domains = []
        return _trusted_domains

    domains: list[str] = []
    # Strip URLs down to their netloc; also capture bare domain tokens.
    url_pattern = re.compile(r'https?://([^\s/,|>)\]]+)', re.IGNORECASE)
    bare_domain_pattern = re.compile(r'\b([a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z]{2,})+)\b', re.IGNORECASE)

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Prefer explicit URLs first
        for m in url_pattern.finditer(line):
            domain = m.group(1).lower().lstrip("www.")
            if domain and domain not in domains:
                domains.append(domain)
        # Also pick up bare domains
        for m in bare_domain_pattern.finditer(line):
            domain = m.group(1).lower().lstrip("www.")
            if domain and domain not in domains:
                domains.append(domain)

    _trusted_domains = domains
    return _trusted_domains


def _is_trusted(url: str) -> bool:
    """Return True if the URL's hostname matches a trusted domain."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        hostname = hostname.lower().lstrip("www.")
    except Exception:
        return False

    trusted = _load_trusted_domains()
    for domain in trusted:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False

# ---------------------------------------------------------------------------
# Helpers
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
        latency_ms=0.0,
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
        latency_ms=0.0,
    )

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def fetch_trusted(request: ToolRequest) -> ToolResult:
    """
    Fetch a URL only if its domain is in the trusted sources list.
    Args:
        url (str) — the URL to fetch
    Returns:
        {url, title, text} on success, NOT_ALLOWED error if domain is untrusted.
    """
    tool_name = "research.fetch_trusted"
    url = request.args.get("url")
    if not url:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "Missing required arg: 'url'.")

    if not _is_trusted(url):
        return _make_err(
            tool_name,
            ToolFailureClass.NOT_ALLOWED,
            f"Domain of URL '{url}' is not in the trusted sources list.",
        )

    # Delegate actual fetching to web.web_fetch
    fetch_request = ToolRequest(
        tool_name="web.fetch",
        args={"url": url},
        purpose="internal",
        user_id="system",
    )
    fetch_result = web_module.dispatch(fetch_request)

    if not fetch_result.ok:
        return _make_err(
            tool_name,
            fetch_result.failure_class or ToolFailureClass.INTERNAL_ERROR,
            fetch_result.failure_message or "web.fetch returned an error.",
        )

    primary = fetch_result.primary or {}
    return _make_ok(
        tool_name,
        {
            "url": url,
            "title": primary.get("title", ""),
            "text": primary.get("text", ""),
        },
        sources=[url],
        notes="Fetched from trusted domain.",
    )


def search_trusted(request: ToolRequest) -> ToolResult:
    """
    Run a web search and filter results to only trusted domains.
    Args:
        q (str) — search query
    Returns:
        list of result dicts from trusted domains only.
    """
    tool_name = "research.search_trusted"
    q = request.args.get("q")
    if not q:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "Missing required arg: 'q'.")

    search_request = ToolRequest(
        tool_name="web.search",
        args={"q": q},
        purpose="internal",
        user_id="system",
    )
    search_result = web_module.dispatch(search_request)

    if not search_result.ok:
        return _make_err(
            tool_name,
            search_result.failure_class or ToolFailureClass.INTERNAL_ERROR,
            search_result.failure_message or "web.search returned an error.",
        )

    raw_results = search_result.primary or []
    if not isinstance(raw_results, list):
        return _make_err(
            tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            "web.search returned unexpected primary type (expected list).",
        )

    trusted_results = [r for r in raw_results if _is_trusted(r.get("url", ""))]
    trusted_sources = [r.get("url", "") for r in trusted_results]

    return _make_ok(
        tool_name,
        trusted_results,
        sources=trusted_sources,
        notes=(
            f"Filtered {len(raw_results)} search results to {len(trusted_results)} "
            "from trusted domains."
        ),
    )

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_HANDLERS = {
    "research.fetch_trusted": fetch_trusted,
    "research.search_trusted": search_trusted,
}


def dispatch(request: ToolRequest) -> ToolResult:
    handler = _HANDLERS.get(request.tool_name)
    if handler is None:
        return _make_err(
            request.tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            f"No handler registered in trusted.py for tool '{request.tool_name}'.",
        )
    return handler(request)
