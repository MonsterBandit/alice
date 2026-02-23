"""
tools/finance/firefly.py

Firefly III finance tool stubs for Alice.

Tools registered:
  finance.get_accounts       — stub
  finance.get_transactions   — stub
  finance.create_transaction — stub

No actual Firefly III API calls are made yet. These stubs exist to
establish the dispatch pattern and registry entries so the executor
can route FINANCE family tools correctly.
"""

from datetime import datetime, timezone
from typing import Any

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ok(tool_name: str, primary: Any, notes: str | None = None) -> ToolResult:
    return ToolResult(
        ok=True,
        tool_name=tool_name,
        primary=primary,
        provenance=ToolProvenance(
            sources=[],
            retrieved_at=_now_iso(),
            notes=notes,
        ),
        failure_class=None,
        failure_message=None,
        latency_ms=0.0,  # will be overwritten by executor
    )


def _not_implemented_stub(tool_name: str) -> ToolResult:
    """Return a clean, informative result for a not-yet-implemented stub."""
    return _make_ok(
        tool_name=tool_name,
        primary={
            "status": "not_implemented",
            "message": (
                f"'{tool_name}' is a stub and has not been implemented yet. "
                "Firefly III API integration is pending."
            ),
        },
        notes="Stub tool — no external calls made.",
    )


# ---------------------------------------------------------------------------
# Tool stubs
# ---------------------------------------------------------------------------


def get_accounts(request: ToolRequest) -> ToolResult:
    """
    Stub: retrieve accounts from Firefly III.

    Will eventually support args:
        type (str): account type filter (e.g. "asset", "expense", "revenue").
    """
    return _not_implemented_stub("finance.get_accounts")


def get_transactions(request: ToolRequest) -> ToolResult:
    """
    Stub: retrieve transactions from Firefly III.

    Will eventually support args:
        account_id (str): filter by account.
        start      (str): ISO-8601 start date.
        end        (str): ISO-8601 end date.
        limit      (int): max results.
    """
    return _not_implemented_stub("finance.get_transactions")


def create_transaction(request: ToolRequest) -> ToolResult:
    """
    Stub: create a transaction in Firefly III.

    Will eventually support args:
        type        (str): "withdrawal", "deposit", or "transfer".
        amount      (str): decimal amount string.
        description (str): transaction description.
        date        (str): ISO-8601 date.
        source      (str): source account name or ID.
        destination (str): destination account name or ID.
    """
    return _not_implemented_stub("finance.create_transaction")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_FIREFLY_DISPATCH = {
    "finance.get_accounts": get_accounts,
    "finance.get_transactions": get_transactions,
    "finance.create_transaction": create_transaction,
}


def dispatch(request: ToolRequest) -> ToolResult:
    """Route a ToolRequest to the correct Firefly III tool handler."""
    handler = _FIREFLY_DISPATCH.get(request.tool_name)
    if handler is None:
        raise NotImplementedError(
            f"No handler registered in tools.finance.firefly for tool '{request.tool_name}'."
        )
    return handler(request)


# ---------------------------------------------------------------------------
# Registration (runs at import time)
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="finance.get_accounts",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve accounts from Firefly III. "
        "Supports optional filtering by account type. (Stub — not yet implemented.)"
    ),
))

register_tool(ToolDef(
    name="finance.get_transactions",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve transactions from Firefly III. "
        "Supports filtering by account, date range, and limit. (Stub — not yet implemented.)"
    ),
))

register_tool(ToolDef(
    name="finance.create_transaction",
    family=ToolFamily.FINANCE,
    description=(
        "Create a new transaction in Firefly III. "
        "Supports withdrawal, deposit, and transfer types. (Stub — not yet implemented.)"
    ),
))
