"""
tools/finance/firefly.py

Firefly III finance tools for Alice.

Tools registered:
  finance.get_accounts        — list accounts (optionally filtered by type)
  finance.get_account         — get a single account by ID
  finance.create_account      — create a new account
  finance.get_transactions    — list transactions (optionally filtered)
  finance.create_transaction  — create a new transaction
  finance.search_transactions — full-text search over transactions
  finance.get_budgets         — list budgets with spend info
  finance.get_rule_groups     — list rule groups
  finance.create_rule_group   — create a new rule group
  finance.create_rule         — create a new rule inside a rule group
"""

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------

FIREFLY_URL = os.environ.get("FIREFLY_URL", "").rstrip("/")
FIREFLY_TOKEN = os.environ.get("FIREFLY_TOKEN", "")

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
            sources=[FIREFLY_URL] if FIREFLY_URL else [],
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
            notes=None,
        ),
        failure_class=failure_class,
        failure_message=message,
        latency_ms=0.0,
    )


def _check_config(tool_name: str) -> ToolResult | None:
    """Return an error ToolResult if FIREFLY_URL or FIREFLY_TOKEN are not set."""
    if not FIREFLY_URL:
        return _make_err(
            tool_name,
            ToolFailureClass.CONFIGURATION,
            "FIREFLY_URL environment variable is not set.",
        )
    if not FIREFLY_TOKEN:
        return _make_err(
            tool_name,
            ToolFailureClass.CONFIGURATION,
            "FIREFLY_TOKEN environment variable is not set.",
        )
    return None


def firefly_request(method: str, path: str, **kwargs) -> dict | list:
    """
    Make an authenticated request to the Firefly III API.

    Builds the full URL from FIREFLY_URL + "/api/v1" + path, sets the
    required auth and content-type headers, and raises on 4xx/5xx responses.

    Returns the parsed JSON response body.
    """
    url = FIREFLY_URL + "/api/v1" + path
    headers = {
        "Authorization": f"Bearer {FIREFLY_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # Merge any caller-supplied headers
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))

    with httpx.Client(timeout=30) as client:
        response = client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()


def _http_failure_class(exc: httpx.HTTPStatusError) -> ToolFailureClass:
    """Map an HTTP status code to a ToolFailureClass."""
    code = exc.response.status_code
    if code == 401 or code == 403:
        return ToolFailureClass.PERMISSION
    if code == 404:
        return ToolFailureClass.NOT_FOUND
    if code == 422:
        return ToolFailureClass.INVALID_INPUT
    if code >= 500:
        return ToolFailureClass.UPSTREAM
    return ToolFailureClass.UNKNOWN


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_accounts(request: ToolRequest) -> ToolResult:
    """
    Retrieve accounts from Firefly III.

    Args:
        type (str, optional): account type filter — "asset", "expense",
                              "revenue", or "liability".
    """
    tool_name = "finance.get_accounts"
    if err := _check_config(tool_name):
        return err

    params = {}
    account_type = request.args.get("type")
    if account_type:
        params["type"] = account_type

    try:
        data = firefly_request("GET", "/accounts", params=params)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    accounts = [
        {
            "id": item["id"],
            "name": item["attributes"].get("name"),
            "type": item["attributes"].get("type"),
            "current_balance": item["attributes"].get("current_balance"),
            "currency_code": item["attributes"].get("currency_code"),
        }
        for item in data.get("data", [])
    ]
    return _make_ok(tool_name, accounts)


def get_account(request: ToolRequest) -> ToolResult:
    """
    Retrieve a single account from Firefly III by ID.

    Args:
        account_id (str): the Firefly III account ID.
    """
    tool_name = "finance.get_account"
    if err := _check_config(tool_name):
        return err

    account_id = request.args.get("account_id")
    if not account_id:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "account_id is required.")

    try:
        data = firefly_request("GET", f"/accounts/{account_id}")
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    item = data.get("data", {})
    account = {
        "id": item.get("id"),
        "name": item["attributes"].get("name"),
        "type": item["attributes"].get("type"),
        "current_balance": item["attributes"].get("current_balance"),
        "currency_code": item["attributes"].get("currency_code"),
        "iban": item["attributes"].get("iban"),
        "notes": item["attributes"].get("notes"),
        "active": item["attributes"].get("active"),
    }
    return _make_ok(tool_name, account)


def create_account(request: ToolRequest) -> ToolResult:
    """
    Create a new account in Firefly III.

    Args:
        name (str): account name.
        type (str): account type (e.g. "asset", "expense", "revenue").
        currency_code (str, optional): defaults to "GBP".
        opening_balance (str, optional): opening balance amount.
        opening_balance_date (str, optional): YYYY-MM-DD date for opening balance.
        iban (str, optional): IBAN for the account.
        notes (str, optional): free-text notes.
    """
    tool_name = "finance.create_account"
    if err := _check_config(tool_name):
        return err

    name = request.args.get("name")
    account_type = request.args.get("type")
    if not name:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "name is required.")
    if not account_type:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "type is required.")

    payload: dict[str, Any] = {
        "name": name,
        "type": account_type,
        "currency_code": request.args.get("currency_code", "GBP"),
    }
    for optional_field in ("opening_balance", "opening_balance_date", "iban", "notes"):
        value = request.args.get(optional_field)
        if value is not None:
            payload[optional_field] = value

    try:
        data = firefly_request("POST", "/accounts", json=payload)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    item = data.get("data", {})
    created = {
        "id": item.get("id"),
        "name": item["attributes"].get("name"),
        "type": item["attributes"].get("type"),
    }
    return _make_ok(tool_name, created)


def get_transactions(request: ToolRequest) -> ToolResult:
    """
    Retrieve transactions from Firefly III.

    Args:
        account_id (str, optional): filter by account ID.
        start (str, optional): ISO-8601 / YYYY-MM-DD start date.
        end (str, optional): ISO-8601 / YYYY-MM-DD end date.
        type (str, optional): transaction type filter.
        limit (int, optional): max results, default 50.
    """
    tool_name = "finance.get_transactions"
    if err := _check_config(tool_name):
        return err

    account_id = request.args.get("account_id")
    limit = int(request.args.get("limit", 50))

    params: dict[str, Any] = {"limit": limit}
    for field in ("start", "end", "type"):
        value = request.args.get(field)
        if value:
            params[field] = value

    path = f"/accounts/{account_id}/transactions" if account_id else "/transactions"

    try:
        data = firefly_request("GET", path, params=params)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    transactions = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        # Firefly III wraps splits inside a "transactions" list on the journal
        splits = attrs.get("transactions", [{}])
        split = splits[0] if splits else {}
        transactions.append({
            "id": item.get("id"),
            "date": split.get("date") or attrs.get("date"),
            "description": split.get("description") or attrs.get("description"),
            "amount": split.get("amount"),
            "type": split.get("type") or attrs.get("type"),
            "source": split.get("source_name"),
            "destination": split.get("destination_name"),
            "category": split.get("category_name"),
            "budget": split.get("budget_name"),
            "tags": split.get("tags", []),
        })
    return _make_ok(tool_name, transactions)


def create_transaction(request: ToolRequest) -> ToolResult:
    """
    Create a new transaction in Firefly III.

    Args:
        type (str): "withdrawal", "deposit", or "transfer".
        date (str): YYYY-MM-DD date.
        amount (str): decimal amount string.
        description (str): transaction description.
        source_id (str, optional): source account ID.
        source_name (str, optional): source account name.
        destination_id (str, optional): destination account ID.
        destination_name (str, optional): destination account name.
        category_name (str, optional): category name.
        budget_name (str, optional): budget name.
        tags (list, optional): list of tag strings.
        notes (str, optional): free-text notes.
    """
    tool_name = "finance.create_transaction"
    if err := _check_config(tool_name):
        return err

    for required in ("type", "date", "amount", "description"):
        if not request.args.get(required):
            return _make_err(
                tool_name,
                ToolFailureClass.INVALID_INPUT,
                f"'{required}' is required.",
            )

    split: dict[str, Any] = {
        "type": request.args["type"],
        "date": request.args["date"],
        "amount": str(request.args["amount"]),
        "description": request.args["description"],
    }
    for optional_field in (
        "source_id", "source_name",
        "destination_id", "destination_name",
        "category_name", "budget_name",
        "tags", "notes",
    ):
        value = request.args.get(optional_field)
        if value is not None:
            split[optional_field] = value

    payload = {
        "apply_rules": True,
        "transactions": [split],
    }

    try:
        data = firefly_request("POST", "/transactions", json=payload)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    item = data.get("data", {})
    attrs = item.get("attributes", {})
    splits = attrs.get("transactions", [{}])
    first = splits[0] if splits else {}
    created = {
        "id": item.get("id"),
        "date": first.get("date"),
        "description": first.get("description"),
        "amount": first.get("amount"),
        "type": first.get("type"),
    }
    return _make_ok(tool_name, created)


def search_transactions(request: ToolRequest) -> ToolResult:
    """
    Full-text search over transactions in Firefly III.

    Args:
        query (str): search query string.
        limit (int, optional): max results, default 25.
    """
    tool_name = "finance.search_transactions"
    if err := _check_config(tool_name):
        return err

    query = request.args.get("query")
    if not query:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "query is required.")

    limit = int(request.args.get("limit", 25))
    params = {"query": query, "limit": limit}

    try:
        data = firefly_request("GET", "/search/transactions", params=params)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    transactions = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        splits = attrs.get("transactions", [{}])
        split = splits[0] if splits else {}
        transactions.append({
            "id": item.get("id"),
            "date": split.get("date") or attrs.get("date"),
            "description": split.get("description") or attrs.get("description"),
            "amount": split.get("amount"),
            "type": split.get("type") or attrs.get("type"),
            "source": split.get("source_name"),
            "destination": split.get("destination_name"),
            "category": split.get("category_name"),
            "budget": split.get("budget_name"),
            "tags": split.get("tags", []),
        })
    return _make_ok(tool_name, transactions)


def get_budgets(request: ToolRequest) -> ToolResult:
    """
    Retrieve budgets from Firefly III, including spend information.
    """
    tool_name = "finance.get_budgets"
    if err := _check_config(tool_name):
        return err

    try:
        data = firefly_request("GET", "/budgets")
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    budgets = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        # Spend info lives inside a nested list when budget limits are set
        spent_list = attrs.get("spent", [])
        spent = spent_list[0].get("sum") if spent_list else None
        limit_list = attrs.get("auto_budget_amount") or attrs.get("budget_limits", [])
        amount = None
        if isinstance(limit_list, list) and limit_list:
            amount = limit_list[0].get("amount")
        elif isinstance(limit_list, str):
            amount = limit_list

        budgets.append({
            "id": item.get("id"),
            "name": attrs.get("name"),
            "amount": amount,
            "spent": spent,
            "period": attrs.get("auto_budget_period"),
        })
    return _make_ok(tool_name, budgets)


def get_rule_groups(request: ToolRequest) -> ToolResult:
    """
    Retrieve all rule groups from Firefly III.
    """
    tool_name = "finance.get_rule_groups"
    if err := _check_config(tool_name):
        return err

    try:
        data = firefly_request("GET", "/rule-groups")
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    groups = [
        {
            "id": item.get("id"),
            "title": item["attributes"].get("title"),
            "description": item["attributes"].get("description"),
            "active": item["attributes"].get("active"),
        }
        for item in data.get("data", [])
    ]
    return _make_ok(tool_name, groups)


def create_rule_group(request: ToolRequest) -> ToolResult:
    """
    Create a new rule group in Firefly III.

    Args:
        title (str): rule group title.
        description (str, optional): rule group description.
    """
    tool_name = "finance.create_rule_group"
    if err := _check_config(tool_name):
        return err

    title = request.args.get("title")
    if not title:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "title is required.")

    payload: dict[str, Any] = {"title": title}
    description = request.args.get("description")
    if description:
        payload["description"] = description

    try:
        data = firefly_request("POST", "/rule-groups", json=payload)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    item = data.get("data", {})
    created = {
        "id": item.get("id"),
        "title": item["attributes"].get("title"),
    }
    return _make_ok(tool_name, created)


def create_rule(request: ToolRequest) -> ToolResult:
    """
    Create a new rule in Firefly III.

    Args:
        title (str): rule title.
        rule_group_id (str): ID of the rule group to add this rule to.
        triggers (list): list of trigger objects, each with at least
                         {"type": "...", "value": "..."}.
        actions (list): list of action objects, each with at least
                        {"type": "...", "value": "..."}.
        trigger_moment (str, optional): "store-journal" (default) or
                                        "update-journal".
        strict (bool, optional): if True, ALL triggers must match. Default False.
        stop_processing (bool, optional): stop processing further rules on match.
                                          Default False.
    """
    tool_name = "finance.create_rule"
    if err := _check_config(tool_name):
        return err

    for required in ("title", "rule_group_id", "triggers", "actions"):
        if not request.args.get(required):
            return _make_err(
                tool_name,
                ToolFailureClass.INVALID_INPUT,
                f"'{required}' is required.",
            )

    payload: dict[str, Any] = {
        "title": request.args["title"],
        "rule_group_id": str(request.args["rule_group_id"]),
        "trigger": request.args.get("trigger_moment", "store-journal"),
        "strict": bool(request.args.get("strict", False)),
        "stop_processing": bool(request.args.get("stop_processing", False)),
        "active": True,
        "triggers": request.args["triggers"],
        "actions": request.args["actions"],
    }

    try:
        data = firefly_request("POST", "/rules", json=payload)
    except httpx.HTTPStatusError as e:
        return _make_err(tool_name, _http_failure_class(e), str(e))
    except httpx.RequestError as e:
        return _make_err(tool_name, ToolFailureClass.NETWORK, str(e))

    item = data.get("data", {})
    created = {
        "id": item.get("id"),
        "title": item["attributes"].get("title"),
    }
    return _make_ok(tool_name, created)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_FIREFLY_DISPATCH = {
    "finance.get_accounts": get_accounts,
    "finance.get_account": get_account,
    "finance.create_account": create_account,
    "finance.get_transactions": get_transactions,
    "finance.create_transaction": create_transaction,
    "finance.search_transactions": search_transactions,
    "finance.get_budgets": get_budgets,
    "finance.get_rule_groups": get_rule_groups,
    "finance.create_rule_group": create_rule_group,
    "finance.create_rule": create_rule,
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
        "Optional arg: type (str) — filter by account type: "
        "'asset', 'expense', 'revenue', or 'liability'."
    ),
))

register_tool(ToolDef(
    name="finance.get_account",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve a single account from Firefly III by ID. "
        "Required arg: account_id (str)."
    ),
))

register_tool(ToolDef(
    name="finance.create_account",
    family=ToolFamily.FINANCE,
    description=(
        "Create a new account in Firefly III. "
        "Required args: name (str), type (str). "
        "Optional args: currency_code (str, default 'GBP'), opening_balance (str), "
        "opening_balance_date (str YYYY-MM-DD), iban (str), notes (str)."
    ),
))

register_tool(ToolDef(
    name="finance.get_transactions",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve transactions from Firefly III. "
        "Optional args: account_id (str), start (str YYYY-MM-DD), "
        "end (str YYYY-MM-DD), type (str), limit (int, default 50)."
    ),
))

register_tool(ToolDef(
    name="finance.create_transaction",
    family=ToolFamily.FINANCE,
    description=(
        "Create a new transaction in Firefly III. "
        "Required args: type (str: 'withdrawal'|'deposit'|'transfer'), "
        "date (str YYYY-MM-DD), amount (str), description (str). "
        "Optional args: source_id, source_name, destination_id, destination_name, "
        "category_name, budget_name, tags (list), notes (str)."
    ),
))

register_tool(ToolDef(
    name="finance.search_transactions",
    family=ToolFamily.FINANCE,
    description=(
        "Search transactions in Firefly III using a full-text query. "
        "Required arg: query (str). "
        "Optional arg: limit (int, default 25)."
    ),
))

register_tool(ToolDef(
    name="finance.get_budgets",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve all budgets from Firefly III, including spend and period information."
    ),
))

register_tool(ToolDef(
    name="finance.get_rule_groups",
    family=ToolFamily.FINANCE,
    description=(
        "Retrieve all rule groups from Firefly III. "
        "Returns a list of {id, title, description, active}."
    ),
))

register_tool(ToolDef(
    name="finance.create_rule_group",
    family=ToolFamily.FINANCE,
    description=(
        "Create a new rule group in Firefly III. "
        "Required arg: title (str). "
        "Optional arg: description (str)."
    ),
))

register_tool(ToolDef(
    name="finance.create_rule",
    family=ToolFamily.FINANCE,
    description=(
        "Create a new rule in Firefly III. "
        "Required args: title (str), rule_group_id (str), "
        "triggers (list of {type, value} objects), "
        "actions (list of {type, value} objects). "
        "Optional args: trigger_moment (str, default 'store-journal'), "
        "strict (bool, default false), stop_processing (bool, default false)."
    ),
))
