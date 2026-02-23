"""
tools/general/local.py

Local filesystem read tools for Alice.

Tools registered:
  local.read_file  — read a single file, UTF-8, max 5 MB
  local.list_dir   — list directory contents (non-recursive), max 500 entries
  local.tree       — BFS directory tree, configurable depth/nodes
  local.grep       — substring search across files in a directory
"""

import hashlib
import os
import re
from collections import deque
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any

from tools.registry import ToolDef, ToolFamily, register_tool
from tools.types import ToolFailureClass, ToolProvenance, ToolRequest, ToolResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_READ_BYTES = 5 * 1024 * 1024
_MAX_LIST_ENTRIES = 500
_DEFAULT_TREE_MAX_DEPTH = 4
_DEFAULT_TREE_MAX_NODES = 5000
_TREE_IGNORE_DIRS = {".git", "__pycache__", "node_modules"}
_DEFAULT_GREP_GLOBS = ["*.py", "*.md", "*.yml", "*.yaml", "*.json", "*.txt"]
_DEFAULT_GREP_MAX_FILES = 2000
_DEFAULT_GREP_MAX_HITS = 200

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
        failure_class=None,
        failure_message=None,
        latency_ms=0.0,  # will be overwritten by executor
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
        latency_ms=0.0,  # will be overwritten by executor
    )


def _resolve_path(raw: str) -> str:
    """Resolve and normalise a path."""
    return os.path.realpath(os.path.abspath(raw))


def _is_binary(path: str, sample_bytes: int = 8192) -> bool:
    """Heuristic: treat a file as binary if it contains a null byte in the first sample."""
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(sample_bytes)
        return b"\x00" in chunk
    except OSError:
        return True


# ---------------------------------------------------------------------------
# Tool: local.read_file
# ---------------------------------------------------------------------------


def read_file(request: ToolRequest) -> ToolResult:
    """
    Read a single file and return its content as a UTF-8 string.

    Required args:
        path (str): absolute or relative path to the file.

    Returns primary dict:
        content    (str) — file text
        byte_count (int) — raw byte size
        sha256     (str) — hex digest of raw bytes
    """
    tool_name = "local.read_file"

    path_raw = request.args.get("path")
    if not path_raw:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'path' argument is required.")

    path = _resolve_path(str(path_raw))

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path does not exist: {path}")

    if not os.path.isfile(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path is not a file: {path}")

    try:
        stat = os.stat(path)
    except OSError as exc:
        return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, f"Cannot stat file: {exc}")

    byte_count = stat.st_size
    if byte_count > _MAX_READ_BYTES:
        return _make_err(
            tool_name,
            ToolFailureClass.BAD_INPUT,
            f"File is too large ({byte_count} bytes). Maximum allowed is {_MAX_READ_BYTES} bytes (5 MB).",
        )

    if _is_binary(path):
        return _make_err(
            tool_name,
            ToolFailureClass.BAD_INPUT,
            f"File appears to be binary and cannot be read as UTF-8: {path}",
        )

    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, f"Cannot read file: {exc}")

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _make_err(
            tool_name,
            ToolFailureClass.PARSE_ERROR,
            f"File is not valid UTF-8: {exc}",
        )

    sha256 = hashlib.sha256(raw).hexdigest()

    return _make_ok(
        tool_name,
        primary={
            "content": content,
            "byte_count": byte_count,
            "sha256": sha256,
        },
        sources=[f"file://{path}"],
        notes=f"Read {byte_count} bytes from {path}.",
    )


# ---------------------------------------------------------------------------
# Tool: local.list_dir
# ---------------------------------------------------------------------------


def list_dir(request: ToolRequest) -> ToolResult:
    """
    List the immediate contents of a directory (non-recursive).

    Required args:
        path (str): directory to list.

    Returns primary dict:
        path    (str)        — resolved directory path
        entries (list[dict]) — up to 500 entries, each:
            name  (str)
            type  ("file" | "dir" | "symlink" | "other")
            size  (int | None)  — bytes for files; None for dirs/other
            mtime (str)         — ISO-8601 UTC modification time
    """
    tool_name = "local.list_dir"

    path_raw = request.args.get("path")
    if not path_raw:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'path' argument is required.")

    path = _resolve_path(str(path_raw))

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path does not exist: {path}")

    if not os.path.isdir(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path is not a directory: {path}")

    try:
        raw_entries = os.scandir(path)
    except OSError as exc:
        return _make_err(tool_name, ToolFailureClass.UPSTREAM_ERROR, f"Cannot list directory: {exc}")

    entries = []
    truncated = False

    with raw_entries:
        for entry in raw_entries:
            if len(entries) >= _MAX_LIST_ENTRIES:
                truncated = True
                break

            try:
                stat = entry.stat(follow_symlinks=False)
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

                if entry.is_symlink():
                    etype = "symlink"
                    size = None
                elif entry.is_file(follow_symlinks=False):
                    etype = "file"
                    size = stat.st_size
                elif entry.is_dir(follow_symlinks=False):
                    etype = "dir"
                    size = None
                else:
                    etype = "other"
                    size = None

            except OSError:
                mtime = _now_iso()
                etype = "other"
                size = None

            entries.append(
                {
                    "name": entry.name,
                    "type": etype,
                    "size": size,
                    "mtime": mtime,
                }
            )

    entries.sort(key=lambda e: (e["type"] != "dir", e["name"].lower()))

    notes = f"Listed {len(entries)} entries in {path}."
    if truncated:
        notes += f" Result truncated at {_MAX_LIST_ENTRIES} entries."

    return _make_ok(
        tool_name,
        primary={
            "path": path,
            "entries": entries,
        },
        sources=[f"file://{path}"],
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Tool: local.tree
# ---------------------------------------------------------------------------


def tree(request: ToolRequest) -> ToolResult:
    """
    BFS directory tree walk.

    Required args:
        path (str): root directory.

    Optional args:
        max_depth (int): default 4. Maximum depth below root (root = depth 0).
        max_nodes (int): default 5000. Stop after this many path entries.

    Returns primary dict:
        root      (str)       — resolved root path
        paths     (list[str]) — relative paths from root, BFS order
        truncated (bool)      — True if max_nodes or max_depth cut the walk short
    """
    tool_name = "local.tree"

    path_raw = request.args.get("path")
    if not path_raw:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'path' argument is required.")

    path = _resolve_path(str(path_raw))

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path does not exist: {path}")

    if not os.path.isdir(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path is not a directory: {path}")

    try:
        max_depth = int(request.args.get("max_depth", _DEFAULT_TREE_MAX_DEPTH))
        max_nodes = int(request.args.get("max_nodes", _DEFAULT_TREE_MAX_NODES))
    except (TypeError, ValueError) as exc:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Invalid numeric argument: {exc}")

    if max_depth < 0:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'max_depth' must be >= 0.")
    if max_nodes < 1:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'max_nodes' must be >= 1.")

    collected: list[str] = []
    truncated = False

    # BFS queue: (absolute_path, depth)
    queue: deque[tuple[str, int]] = deque()
    queue.append((path, 0))

    while queue:
        current, depth = queue.popleft()

        if len(collected) >= max_nodes:
            truncated = True
            break

        # Record this node (skip the root itself — it's captured in `root`)
        if current != path:
            rel = os.path.relpath(current, path)
            collected.append(rel)

        if depth >= max_depth:
            continue

        if not os.path.isdir(current):
            continue

        try:
            children = sorted(
                os.scandir(current),
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
            )
        except OSError:
            continue

        for child in children:
            if child.is_dir(follow_symlinks=False) and child.name in _TREE_IGNORE_DIRS:
                continue
            queue.append((child.path, depth + 1))

    notes = f"Tree of {path}: {len(collected)} nodes collected."
    if truncated:
        notes += f" Truncated at {max_nodes} nodes."

    return _make_ok(
        tool_name,
        primary={
            "root": path,
            "paths": collected,
            "truncated": truncated,
        },
        sources=[f"file://{path}"],
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Tool: local.grep
# ---------------------------------------------------------------------------


def grep(request: ToolRequest) -> ToolResult:
    """
    Search for a substring pattern across files in a directory.

    Required args:
        path    (str): directory to search.
        pattern (str): substring to search for.

    Optional args:
        globs     (list[str] | str): file glob patterns to include.
                  Default: ["*.py","*.md","*.yml","*.yaml","*.json","*.txt"].
                  Comma-separated string is accepted.
        max_files (int): maximum number of files to search. Default 2000.
        max_hits  (int): maximum number of hits to return. Default 200.

    Returns primary dict:
        path           (str)        — resolved search root
        pattern        (str)        — pattern used
        hits           (list[dict]) — up to max_hits hits, each:
            file        (str) — relative path from search root
            line_number (int) — 1-based
            line        (str) — line text (trailing newline stripped)
        truncated      (bool)       — True if hit limit was reached
        files_searched (int)        — number of files actually searched
    """
    tool_name = "local.grep"

    path_raw = request.args.get("path")
    if not path_raw:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'path' argument is required.")

    pattern_raw = request.args.get("pattern")
    if not pattern_raw:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'pattern' argument is required.")

    path = _resolve_path(str(path_raw))

    if not os.path.exists(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path does not exist: {path}")

    if not os.path.isdir(path):
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Path is not a directory: {path}")

    # --- Parse globs ---
    globs_raw = request.args.get("globs", _DEFAULT_GREP_GLOBS)
    if isinstance(globs_raw, str):
        globs = [g.strip() for g in globs_raw.split(",") if g.strip()]
    elif isinstance(globs_raw, list):
        globs = [str(g).strip() for g in globs_raw if str(g).strip()]
    else:
        globs = list(_DEFAULT_GREP_GLOBS)

    if not globs:
        globs = list(_DEFAULT_GREP_GLOBS)

    # --- Parse limits ---
    try:
        max_files = int(request.args.get("max_files", _DEFAULT_GREP_MAX_FILES))
        max_hits = int(request.args.get("max_hits", _DEFAULT_GREP_MAX_HITS))
    except (TypeError, ValueError) as exc:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Invalid numeric argument: {exc}")

    if max_files < 1:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'max_files' must be >= 1.")
    if max_hits < 1:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, "'max_hits' must be >= 1.")

    # --- Compile pattern as literal substring search via regex ---
    try:
        compiled = re.compile(re.escape(str(pattern_raw)))
    except re.error as exc:
        return _make_err(tool_name, ToolFailureClass.BAD_INPUT, f"Failed to compile pattern: {exc}")

    # --- Collect candidate files ---
    candidate_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(path):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in _TREE_IGNORE_DIRS]

        for filename in filenames:
            if any(fnmatch(filename, g) for g in globs):
                candidate_files.append(os.path.join(dirpath, filename))

            if len(candidate_files) >= max_files:
                break

        if len(candidate_files) >= max_files:
            break

    # --- Search files ---
    hits: list[dict] = []
    truncated = False
    files_searched = 0

    for filepath in candidate_files:
        if truncated:
            break

        if _is_binary(filepath):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="strict") as fh:
                lines = fh.readlines()
        except (OSError, UnicodeDecodeError):
            continue

        files_searched += 1

        for lineno, line in enumerate(lines, start=1):
            if compiled.search(line):
                hits.append(
                    {
                        "file": os.path.relpath(filepath, path),
                        "line_number": lineno,
                        "line": line.rstrip("\n\r"),
                    }
                )
                if len(hits) >= max_hits:
                    truncated = True
                    break

    notes = (
        f"Searched {files_searched} file(s) under {path} for pattern '{pattern_raw}'. "
        f"Found {len(hits)} hit(s)."
    )
    if truncated:
        notes += f" Truncated at {max_hits} hits."

    return _make_ok(
        tool_name,
        primary={
            "path": path,
            "pattern": pattern_raw,
            "hits": hits,
            "truncated": truncated,
            "files_searched": files_searched,
        },
        sources=[f"file://{path}"],
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_LOCAL_DISPATCH = {
    "local.read_file": read_file,
    "local.list_dir": list_dir,
    "local.tree": tree,
    "local.grep": grep,
}


def dispatch(request: ToolRequest) -> ToolResult:
    """Route a ToolRequest to the correct local tool handler."""
    handler = _LOCAL_DISPATCH.get(request.tool_name)
    if handler is None:
        raise NotImplementedError(
            f"No handler registered in tools.general.local for tool '{request.tool_name}'."
        )
    return handler(request)


# ---------------------------------------------------------------------------
# Registration (runs at import time)
# ---------------------------------------------------------------------------

register_tool(ToolDef(
    name="local.read_file",
    family=ToolFamily.GENERAL,
    description=(
        "Read a single local file and return its UTF-8 content, byte count, and SHA-256 hash. "
        "Maximum file size: 5 MB. Binary files are rejected."
    ),
))

register_tool(ToolDef(
    name="local.list_dir",
    family=ToolFamily.GENERAL,
    description=(
        "List the immediate (non-recursive) contents of a local directory. "
        "Returns name, type, size, and mtime for up to 500 entries."
    ),
))

register_tool(ToolDef(
    name="local.tree",
    family=ToolFamily.GENERAL,
    description=(
        "Walk a local directory tree using BFS and return a list of relative paths. "
        "Configurable max_depth (default 4) and max_nodes (default 5000). "
        "Ignores .git, __pycache__, and node_modules."
    ),
))

register_tool(ToolDef(
    name="local.grep",
    family=ToolFamily.GENERAL,
    description=(
        "Search for a substring pattern across files in a local directory. "
        "Configurable file globs, max_files (default 2000), and max_hits (default 200). "
        "Returns file path, line number, and line content for each hit."
    ),
))
