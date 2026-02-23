from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ToolFamily(Enum):
    GENERAL = "GENERAL"
    RESEARCH = "RESEARCH"
    CODING = "CODING"
    FINANCE = "FINANCE"


@dataclass
class ToolDef:
    name: str
    family: ToolFamily
    description: str


# Internal registry store: tool_name -> ToolDef
_REGISTRY: dict[str, ToolDef] = {}


def register_tool(tool_def: ToolDef) -> None:
    """Register a tool definition by name. Raises if name is already registered."""
    if tool_def.name in _REGISTRY:
        raise ValueError(f"Tool '{tool_def.name}' is already registered.")
    _REGISTRY[tool_def.name] = tool_def


def get_tool(tool_name: str) -> Optional[ToolDef]:
    """Look up a tool by name. Returns None if not found."""
    return _REGISTRY.get(tool_name)


def list_tools() -> list[ToolDef]:
    """Return all registered tools."""
    return list(_REGISTRY.values())


def is_tool_allowed(tool_name: str, enabled_tools: Optional[set[str]]) -> bool:
    """
    Return True if the tool is allowed to run.

    - If enabled_tools is None, all registered tools are allowed.
    - If enabled_tools is provided (even if empty), default deny:
      only tools explicitly listed are allowed.
    - A tool must also be registered to be allowed.
    """
    if tool_name not in _REGISTRY:
        return False
    if enabled_tools is None:
        return True
    return tool_name in enabled_tools
