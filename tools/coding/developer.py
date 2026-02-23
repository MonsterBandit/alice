import os
import subprocess
from datetime import datetime, timezone
from typing import Any

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Register tools
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="coding.run_bash",
    family=ToolFamily.CODING,
    description="Execute a bash command via subprocess. Args: command (str), working_dir (str, default /opt/alice).",
))

register_tool(ToolDef(
    name="coding.read_file",
    family=ToolFamily.CODING,
    description="Read any file from disk for code work. Args: path (str).",
))

register_tool(ToolDef(
    name="coding.write_file",
    family=ToolFamily.CODING,
    description="Write content to a file. Args: path (str), content (str).",
))

register_tool(ToolDef(
    name="coding.list_dir",
    family=ToolFamily.CODING,
    description="List the contents of a directory. Args: path (str).",
))

# ---------------------------------------------------------------------------
# Helpers
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

def run_bash(request: ToolRequest) -> ToolResult:
    """
    Execute a bash command via subprocess.
    Args:
        command (str)       — the shell command to run
        working_dir (str)   — working directory, default /opt/alice
    Returns:
        {stdout, stderr, exit_code}
    """
    tool_name = "coding.run_bash"
    command = request.args.get("command")
    if not command:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "Missing required arg: 'command'.")

    working_dir = request.args.get("working_dir", "/opt/alice")

    if not os.path.isdir(working_dir):
        return _make_err(
            tool_name,
            ToolFailureClass.INVALID_INPUT,
            f"working_dir does not exist or is not a directory: '{working_dir}'",
        )

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return _make_ok(
            tool_name,
            {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
            },
            notes=f"Command exited with code {proc.returncode}.",
        )
    except subprocess.TimeoutExpired:
        return _make_err(tool_name, ToolFailureClass.TIMEOUT, "Command timed out after 30 seconds.")
    except Exception as e:
        return _make_err(tool_name, ToolFailureClass.INTERNAL_ERROR, f"{type(e).__name__}: {e}")


def read_file(request: ToolRequest) -> ToolResult:
    """
    Read any file from disk.
    Args:
        path (str) — absolute or relative path to the file
    Returns:
        file content as a string
    """
    tool_name = "coding.read_file"
    path = request.args.get("path")
    if not path:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "Missing required arg: 'path'.")

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.NOT_FOUND, f"File not found: '{path}'")

    if not os.path.isfile(path):
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, f"Path is not a file: '{path}'")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return _make_ok(tool_name, content, notes=f"Read {len(content)} characters from '{path}'.")
    except Exception as e:
        return _make_err(tool_name, ToolFailureClass.INTERNAL_ERROR, f"{type(e).__name__}: {e}")


def write_file(request: ToolRequest) -> ToolResult:
    """
    Write content to a file, creating parent directories as needed.
    Args:
        path    (str) — destination file path
        content (str) — content to write
    Returns:
        {path, bytes_written}
    """
    tool_name = "coding.write_file"
    path = request.args.get("path")
    content = request.args.get("content")

    if not path:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "Missing required arg: 'path'.")
    if content is None:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "Missing required arg: 'content'.")

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        encoded = content.encode("utf-8")
        with open(path, "wb") as f:
            f.write(encoded)

        return _make_ok(
            tool_name,
            {"path": path, "bytes_written": len(encoded)},
            notes=f"Wrote {len(encoded)} bytes to '{path}'.",
        )
    except Exception as e:
        return _make_err(tool_name, ToolFailureClass.INTERNAL_ERROR, f"{type(e).__name__}: {e}")


def list_dir(request: ToolRequest) -> ToolResult:
    """
    List the contents of a directory.
    Args:
        path (str) — directory path
    Returns:
        list of entry dicts with keys: name, type (file|dir|other), size_bytes
    """
    tool_name = "coding.list_dir"
    path = request.args.get("path")
    if not path:
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, "Missing required arg: 'path'.")

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.NOT_FOUND, f"Path not found: '{path}'")

    if not os.path.isdir(path):
        return _make_err(tool_name, ToolFailureClass.INVALID_INPUT, f"Path is not a directory: '{path}'")

    try:
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full):
                kind = "file"
                size = os.path.getsize(full)
            elif os.path.isdir(full):
                kind = "dir"
                size = None
            else:
                kind = "other"
                size = None
            entries.append({"name": name, "type": kind, "size_bytes": size})

        return _make_ok(tool_name, entries, notes=f"Listed {len(entries)} entries in '{path}'.")
    except Exception as e:
        return _make_err(tool_name, ToolFailureClass.INTERNAL_ERROR, f"{type(e).__name__}: {e}")

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_HANDLERS = {
    "coding.run_bash": run_bash,
    "coding.read_file": read_file,
    "coding.write_file": write_file,
    "coding.list_dir": list_dir,
}


def dispatch(request: ToolRequest) -> ToolResult:
    handler = _HANDLERS.get(request.tool_name)
    if handler is None:
        return _make_err(
            request.tool_name,
            ToolFailureClass.INTERNAL_ERROR,
            f"No handler registered in developer.py for tool '{request.tool_name}'.",
        )
    return handler(request)
