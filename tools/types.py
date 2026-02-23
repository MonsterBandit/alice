from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolFailureClass(Enum):
    BAD_INPUT = "BAD_INPUT"
    NOT_ALLOWED = "NOT_ALLOWED"
    TIMEOUT = "TIMEOUT"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ToolProvenance:
    sources: list[str]
    retrieved_at: str
    notes: Optional[str] = None


@dataclass
class ToolRequest:
    tool_name: str
    args: dict
    purpose: str
    user_id: str
    task_id: Optional[str] = None


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    primary: Any
    provenance: ToolProvenance
    failure_class: Optional[ToolFailureClass] = None
    failure_message: Optional[str] = None
    latency_ms: float = 0.0
