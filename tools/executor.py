import time
from datetime import datetime, timezone
from typing import Optional

import tools.general.web       # side-effects: registers web.* GENERAL tools
import tools.general.local     # side-effects: registers local.* GENERAL tools
import tools.general.everyday  # side-effects: registers everyday.* GENERAL tools
import tools.finance.firefly   # side-effects: registers finance.* FINANCE tools
import tools.coding.developer  # side-effects: registers coding.* CODING tools
import tools.research.trusted  # side-effects: registers research.* RESEARCH tools

from .registry import ToolFamily, get_tool, is_tool_allowed
from .types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult


def _make_error_result(
    request: ToolRequest,
    failure_class: ToolFailureClass,
    failure_message: str,
    latency_ms: float,
) -> ToolResult:
    """
    Build a fully-populated ToolResult representing a clean failure.
    Never returns partial data — primary is always None on error.
    """
    return ToolResult(
        ok=False,
        tool_name=request.tool_name,
        primary=None,
        provenance=ToolProvenance(
            sources=[],
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            notes="Tool did not execute successfully.",
        ),
        failure_class=failure_class,
        failure_message=failure_message,
        latency_ms=latency_ms,
    )


def _route_to_family(family: ToolFamily, request: ToolRequest) -> ToolResult:
    """
    Route the request to the correct tool family handler.

    Within GENERAL, tool names are routed by prefix:
      - "web.*"       → tools.general.web.dispatch
      - "local.*"     → tools.general.local.dispatch
      - "everyday.*"  → tools.general.everyday.dispatch

    Within FINANCE:
      - all tools → tools.finance.firefly.dispatch

    Within CODING:
      - all tools → tools.coding.developer.dispatch

    Within RESEARCH:
      - all tools → tools.research.trusted.dispatch
    """
    if family == ToolFamily.GENERAL:
        if request.tool_name.startswith("web."):
            return tools.general.web.dispatch(request)
        if request.tool_name.startswith("local."):
            return tools.general.local.dispatch(request)
        if request.tool_name.startswith("everyday."):
            return tools.general.everyday.dispatch(request)
        raise NotImplementedError(
            f"No GENERAL handler found for tool '{request.tool_name}'. "
            "Expected a 'web.*', 'local.*', or 'everyday.*' prefix."
        )
    elif family == ToolFamily.RESEARCH:
        return tools.research.trusted.dispatch(request)
    elif family == ToolFamily.CODING:
        return tools.coding.developer.dispatch(request)
    elif family == ToolFamily.FINANCE:
        return tools.finance.firefly.dispatch(request)
    else:
        raise NotImplementedError(f"Unknown tool family '{family}' for tool '{request.tool_name}'.")


def run_tool(request: ToolRequest, enabled_tools: Optional[set[str]]) -> ToolResult:
    """
    Single entry point for all tool execution.

    - Validates the tool is registered and allowed.
    - Tracks latency across the full call.
    - Routes to the correct family handler.
    - Is fail-closed: any error produces a clean ToolResult with ok=False
      and primary=None. Partial results are never returned.
    """
    start = time.monotonic()

    # --- Authorization check ---
    if not is_tool_allowed(request.tool_name, enabled_tools):
        latency_ms = (time.monotonic() - start) * 1000
        return _make_error_result(
            request=request,
            failure_class=ToolFailureClass.NOT_ALLOWED,
            failure_message=(
                f"Tool '{request.tool_name}' is not allowed or not registered."
            ),
            latency_ms=latency_ms,
        )

    # --- Registry lookup ---
    tool_def = get_tool(request.tool_name)
    if tool_def is None:
        latency_ms = (time.monotonic() - start) * 1000
        return _make_error_result(
            request=request,
            failure_class=ToolFailureClass.INTERNAL_ERROR,
            failure_message=f"Tool '{request.tool_name}' passed auth but was not found in registry.",
            latency_ms=latency_ms,
        )

    # --- Execution ---
    try:
        result = _route_to_family(tool_def.family, request)
        result.latency_ms = (time.monotonic() - start) * 1000
        return result

    except NotImplementedError as e:
        latency_ms = (time.monotonic() - start) * 1000
        return _make_error_result(
            request=request,
            failure_class=ToolFailureClass.INTERNAL_ERROR,
            failure_message=str(e),
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        return _make_error_result(
            request=request,
            failure_class=ToolFailureClass.INTERNAL_ERROR,
            failure_message=f"Unexpected error during tool execution: {type(e).__name__}: {e}",
            latency_ms=latency_ms,
        )
