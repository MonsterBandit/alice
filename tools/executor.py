import time
from datetime import datetime, timezone
from typing import Optional

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
    No implementations exist yet — each family raises NotImplementedError.
    """
    retrieved_at = datetime.now(timezone.utc).isoformat()

    if family == ToolFamily.GENERAL:
        raise NotImplementedError(f"GENERAL tool '{request.tool_name}' is not yet implemented.")
    elif family == ToolFamily.RESEARCH:
        raise NotImplementedError(f"RESEARCH tool '{request.tool_name}' is not yet implemented.")
    elif family == ToolFamily.CODING:
        raise NotImplementedError(f"CODING tool '{request.tool_name}' is not yet implemented.")
    elif family == ToolFamily.FINANCE:
        raise NotImplementedError(f"FINANCE tool '{request.tool_name}' is not yet implemented.")
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
