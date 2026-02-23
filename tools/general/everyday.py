"""
tools/general/everyday.py

Everyday utility tools for Alice:
  - everyday.get_datetime   : current date/time/day/timezone
  - everyday.set_reminder   : store a reminder to reminders.json
  - everyday.get_reminders  : retrieve all pending reminders
  - everyday.write_draft    : produce a structured draft (email, message, note, etc.)
  - everyday.summarize      : return a concise summary of provided text
"""

import json
import os
import re
import textwrap
from datetime import datetime, timezone, timedelta
from typing import Any

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REMINDERS_PATH = "/opt/alice/brain/memory/files/reminders.json"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_ok(
    tool_name: str,
    primary: Any,
    notes: str | None = None,
) -> ToolResult:
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
        latency_ms=0.0,
    )


def _make_err(
    tool_name: str,
    failure_class: ToolFailureClass,
    message: str,
) -> ToolResult:
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


def _load_reminders() -> list[dict]:
    """Load reminders from disk. Returns empty list if file missing or corrupt."""
    if not os.path.exists(REMINDERS_PATH):
        return []
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _save_reminders(reminders: list[dict]) -> None:
    """Persist reminders list to disk, creating directories as needed."""
    os.makedirs(os.path.dirname(REMINDERS_PATH), exist_ok=True)
    with open(REMINDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=2, ensure_ascii=False)


def _parse_when(when: str) -> str:
    """
    Parse a 'when' string into an ISO-8601 UTC datetime string.

    Accepts:
      - ISO datetime strings (passed through after parsing)
      - Relative expressions: "in N minutes/hours/days"

    Returns the resolved ISO string, or raises ValueError on failure.
    """
    when_stripped = when.strip()

    # Try relative: "in N minutes/hours/days"
    relative_pattern = re.compile(
        r"^in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)$",
        re.IGNORECASE,
    )
    match = relative_pattern.match(when_stripped)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        now = datetime.now(timezone.utc)
        if unit.startswith("minute"):
            target = now + timedelta(minutes=amount)
        elif unit.startswith("hour"):
            target = now + timedelta(hours=amount)
        else:
            target = now + timedelta(days=amount)
        return target.isoformat()

    # Try ISO datetime parse (with or without timezone)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(when_stripped, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue

    raise ValueError(
        f"Could not parse 'when' value: '{when}'. "
        "Use ISO format (e.g. '2025-06-01T09:00:00') or relative (e.g. 'in 30 minutes')."
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_datetime(request: ToolRequest) -> ToolResult:
    """Return current date, time, day of week, and timezone (UTC)."""
    tool_name = "everyday.get_datetime"
    now = datetime.now(timezone.utc)
    result = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": "UTC",
        "iso": now.isoformat(),
    }
    return _make_ok(tool_name, result, notes="All times are in UTC.")


def set_reminder(request: ToolRequest) -> ToolResult:
    """
    Store a reminder in reminders.json.

    Required args:
      - message (str): the reminder text
      - when    (str): ISO datetime or relative expression like "in 30 minutes"
    """
    tool_name = "everyday.set_reminder"

    message = request.args.get("message", "").strip()
    when_raw = request.args.get("when", "").strip()

    if not message:
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            "Missing required argument: 'message'.",
        )
    if not when_raw:
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            "Missing required argument: 'when'.",
        )

    try:
        when_iso = _parse_when(when_raw)
    except ValueError as e:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, str(e))

    reminder = {
        "id": f"reminder_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "message": message,
        "when": when_iso,
        "created_at": _now_iso(),
        "status": "pending",
    }

    try:
        reminders = _load_reminders()
        reminders.append(reminder)
        _save_reminders(reminders)
    except OSError as e:
        return _make_err(
            tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            f"Failed to save reminder: {e}",
        )

    return _make_ok(
        tool_name,
        {
            "confirmation": f"Reminder set for {when_iso}.",
            "reminder": reminder,
        },
        notes=f"Stored in {REMINDERS_PATH}.",
    )


def get_reminders(request: ToolRequest) -> ToolResult:
    """Return all reminders from reminders.json."""
    tool_name = "everyday.get_reminders"

    try:
        reminders = _load_reminders()
    except OSError as e:
        return _make_err(
            tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            f"Failed to read reminders: {e}",
        )

    return _make_ok(
        tool_name,
        {"reminders": reminders, "count": len(reminders)},
        notes=f"Loaded from {REMINDERS_PATH}.",
    )


def write_draft(request: ToolRequest) -> ToolResult:
    """
    Produce a structured draft based on type and a content brief.

    Required args:
      - type          (str): e.g. "email", "message", "note"
      - content_brief (str): description of what the draft should say
    """
    tool_name = "everyday.write_draft"

    draft_type = request.args.get("type", "").strip().lower()
    brief = request.args.get("content_brief", "").strip()

    if not draft_type:
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            "Missing required argument: 'type'.",
        )
    if not brief:
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            "Missing required argument: 'content_brief'.",
        )

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if draft_type == "email":
        draft = textwrap.dedent(f"""\
            Subject: [Subject based on brief]

            Hi [Recipient],

            I hope this message finds you well.

            {brief}

            Please don't hesitate to reach out if you have any questions or need further information.

            Best regards,
            [Your Name]
        """)

    elif draft_type == "message":
        draft = textwrap.dedent(f"""\
            Hey,

            {brief}

            Let me know what you think!

            — [Your Name]
        """)

    elif draft_type == "note":
        draft = textwrap.dedent(f"""\
            Note — {now_str}

            {brief}
        """)

    else:
        # Generic fallback for any other type
        draft = textwrap.dedent(f"""\
            [{draft_type.capitalize()} — {now_str}]

            {brief}
        """)

    return _make_ok(
        tool_name,
        {"type": draft_type, "draft": draft},
        notes=f"Draft type: '{draft_type}'. Template-based output; review before sending.",
    )


def summarize(request: ToolRequest) -> ToolResult:
    """
    Return a concise summary of the provided text.

    Required args:
      - text (str): the text to summarize
    """
    tool_name = "everyday.summarize"

    text = request.args.get("text", "").strip()

    if not text:
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            "Missing required argument: 'text'.",
        )

    # Split into sentences on '.', '!', or '?'
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = [s.strip() for s in sentence_endings.split(text) if s.strip()]

    total = len(sentences)

    if total == 0:
        summary = text[:300]
    elif total <= 3:
        # Short text: return as-is
        summary = " ".join(sentences)
    else:
        # Keep roughly the first third of sentences, minimum 3
        keep = max(3, total // 3)
        summary = " ".join(sentences[:keep])
        if not summary.endswith((".", "!", "?")):
            summary += "."
        summary += f" [Summary of {total} sentences; {total - keep} omitted.]"

    return _make_ok(
        tool_name,
        {"summary": summary, "original_length": len(text), "summary_length": len(summary)},
        notes="Extractive summary using leading sentences.",
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_DISPATCH_TABLE = {
    "everyday.get_datetime": get_datetime,
    "everyday.set_reminder": set_reminder,
    "everyday.get_reminders": get_reminders,
    "everyday.write_draft": write_draft,
    "everyday.summarize": summarize,
}


def dispatch(request: ToolRequest) -> ToolResult:
    handler = _DISPATCH_TABLE.get(request.tool_name)
    if handler is None:
        return _make_err(
            request.tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            f"No handler found for tool '{request.tool_name}' in everyday dispatch.",
        )
    return handler(request)


# ---------------------------------------------------------------------------
# Registration (side-effects on import)
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="everyday.get_datetime",
    family=ToolFamily.GENERAL,
    description="Returns the current date, time, day of week, and timezone (UTC).",
))

register_tool(ToolDef(
    name="everyday.set_reminder",
    family=ToolFamily.GENERAL,
    description=(
        "Stores a reminder in reminders.json. "
        "Args: message (str), when (str — ISO datetime or relative like 'in 30 minutes')."
    ),
))

register_tool(ToolDef(
    name="everyday.get_reminders",
    family=ToolFamily.GENERAL,
    description="Returns all pending reminders from reminders.json.",
))

register_tool(ToolDef(
    name="everyday.write_draft",
    family=ToolFamily.GENERAL,
    description=(
        "Produces a structured draft. "
        "Args: type (str, e.g. 'email', 'message', 'note'), content_brief (str)."
    ),
))

register_tool(ToolDef(
    name="everyday.summarize",
    family=ToolFamily.GENERAL,
    description="Returns a concise summary of the provided text. Args: text (str).",
))
