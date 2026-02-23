# Legacy Tool Framework Summary

**Path:** `/opt/jarvis/governance/operational_knowledge/legacy_tool_framework_summary.md`
**Status:** Reference Only
**Authority:** Admin (Tim)
**Purpose:** Summary of the tooling that existed in the prior ISAC/Alice system, preserved as a reference when designing Alice's new tool framework. Nothing here is active. This is a pointer document only.

---

## Overview

The prior system organized tools into families, executed through a central **execution spine** (`brain/tools/executor.py`). Tools were registered in a **registry** (`brain/tools/registry.py`) with a `ToolFamily` enum and `ToolDef` dataclass. Execution was governed by a `ToolRequest` / `ToolResult` contract (`brain/tools/types.py`). All tool calls were auditable and provenance-tracked.

The key principle: **Alice never executed tools directly.** ISAC (the silent executor) ran approved tool calls. Alice proposed; ISAC executed; artifacts were logged.

---

## 1. Web Tools (`brain/tools/web_tools.py`)

### Purpose
Full governed web browsing — search, open, read, navigate, and extract content from the public web.

### Tools

| Tool Name | Description |
|---|---|
| `web.search` | DuckDuckGo HTML search. Accepts up to 4 queries, up to 10 results each. Supports optional domain allowlist pinning. Two-pass parser (DDG markup + generic anchor fallback). |
| `web.open` | Fetch and parse a URL. Supports HTML, plain text, XML, and PDF. Extracts title, text, and links. Stores result in an in-memory page store keyed by `ref_id`. Returns a text excerpt (first 800 chars). |
| `web.find` | Regex or substring search within a previously opened page (by `ref_id`). Returns hit excerpts with context window (±80 chars). |
| `web.click` | Follow a link from a previously opened page by `link_id`. Internally calls `web.open` on the target URL. Supports a `chain_budget` to limit click chains. |
| `web.screenshot_pdf` | Render a specific page of a previously opened PDF to a PNG image (base64). Uses PyMuPDF (fitz). |
| `web.read_site` | Bounded same-domain crawler. Discovers URLs via sitemap.xml first (best-effort), then BFS crawl. Configurable max pages (up to 200), max depth (up to 10), rate limiting, and per-page byte cap. Returns per-page text excerpts (first 3000 chars). |

### Guardrails
- Intent must be one of: `lookup`, `verify`, `compare`, `explain`, `locate-source`
- Risk tier must be 2 or 3
- Blocked file extensions: `.zip`, `.tar`, `.gz`, `.exe`, `.msi`, `.dmg`, `.apk`, `.iso`, etc.
- Allowed content types: `text/html`, `text/plain`, `application/pdf`, `application/xml`, `text/xml`
- All results include `ToolProvenance` (sources, retrieved_at, notes)
- In-memory page store is keyed by `(user_id, chat_id, ref_id)` — scoped per user/chat

### Budgets (defaults, raiseable with explicit Admin approval)

| Dimension | Default Cap |
|---|---|
| Queries per call | 4 |
| Results per query | 10 |
| Opens per call | 3 |
| Find hits | 20 |
| Read site max pages | 30 |
| Read site max depth | 3 |
| Rate limit | 500ms between fetches |

---

## 2. Local Read Tools (`brain/tools/local_read_tools.py`)

### Purpose
Read-only access to the local filesystem under `/opt/jarvis/**`. Fail-closed allowlist. No writes, no binary reads, no network I/O.

### Tools

| Tool Name | Description |
|---|---|
| `local.read_file` | Read an entire file (up to 5MB). UTF-8 only. Returns content, SHA-256, byte count. |
| `local.read_snippet` | Read a line range from a file (1-based, inclusive). Streaming read — does not load entire file. Max 800 lines or 512KB per snippet. Returns lines as a list. |
| `local.list_dir` | List directory contents (non-recursive). Sorted alphabetically. Returns name, type, size, mtime. Max 500 entries. |
| `local.tree` | BFS directory tree traversal. Configurable max depth (default 4) and max nodes (default 5000). Supports ignore globs (default: `.git`, `node_modules`, `__pycache__`, `.venv`). |
| `local.grep` | Regex or substring search across files in a directory tree. Configurable file globs (default: `*.py`, `*.md`, `*.html`, `*.yml`, `*.yaml`, `*.json`, `*.txt`). Max 2000 files considered, 200 hits returned. |

### Guardrails
- Allowlist: `/opt/jarvis/**` only
- Deny-by-default: `/opt/jarvis/brain-data/**` (requires explicit `allow_brain_data=True`)
- No binary files (NUL byte detection)
- UTF-8 only
- Path resolution handles the `/opt/jarvis/brain` → `/app` container mount mapping
- All results include `ToolProvenance`

### Budgets (env-configurable)

| Dimension | Default Cap | Env Var |
|---|---|---|
| File read | 5MB | `ISAC_LOCAL_READ_MAX_BYTES` |
| Snippet lines | 800 | `ISAC_LOCAL_SNIPPET_MAX_LINES` |
| Snippet bytes | 512KB | `ISAC_LOCAL_SNIPPET_MAX_BYTES` |
| List entries | 500 | `ISAC_LOCAL_LIST_MAX_ENTRIES` |
| Tree nodes | 5000 | `ISAC_LOCAL_TREE_MAX_NODES` |
| Grep files | 2000 | `ISAC_LOCAL_GREP_MAX_FILES` |
| Grep hits | 200 | `ISAC_LOCAL_GREP_MAX_HITS` |

---

## 3. Finance Tools — FRTK v1 (`governance/operational_knowledge/frtk_v1.md`)

### Purpose
Finance reasoning toolkit. **Execution was BLOCKED during LAP (Locked Activation Period).** Firefly III is the system of record.

### Status
- LAP Skeleton — Inert
- No tool execution permitted
- No filesystem or network I/O
- No memory or identity learning

### Planned Capabilities (not yet active)
- Phased ingestion of financial data
- Normalization and correction playbooks
- Audit trail generation
- Adapters emitting request specs for future finance actions (no direct execution)

### System of Record
- **Firefly III** — all writes require explicit Admin unblocking and governance approval

### Notes for New Framework
- Finance execution must remain blocked until explicitly unblocked by Admin
- Any finance tool must be gated behind a separate governance check
- All finance actions must be auditable and reversible where possible

---

## 4. Coding Tools — CRTK v1 (`governance/operational_knowledge/crtk_v1.md`)

### Purpose
Coding reasoning toolkit. **Execution was BLOCKED during LAP.** Produces proposals and verification plans only — no direct execution.

### Status
- LAP Skeleton — Inert
- No tool execution (no calls into the toolbelt or execution spine)
- No file or network I/O
- No memory or identity learning
- No finance logic

### Components

| Component | Path | Description |
|---|---|---|
| Manifest | `brain/toolkits/crtk/manifest.py` | Inventory of coding tools and contracts |
| Entry point | `brain/toolkits/crtk/crtk.py` | `crtk_propose` function |
| Adapters | `brain/toolkits/crtk/adapters/*` | Request spec emitters (non-executing) |
| Playbooks | `brain/toolkits/crtk/propose/*`, `review/*`, `verify/*`, `explain/*` | Rubrics and templates |

### Relationship to Toolbelt
- Callable tools live under `/opt/jarvis/brain/tools/*`
- CRTK describes or requests those tools via non-executing request specs only
- Actual execution goes through the canonical execution spine

### Notes for New Framework
- CRTK's propose/review/verify/explain structure is worth preserving
- The separation between "propose a plan" and "execute a plan" is a core safety pattern
- Adapters as request-spec emitters (not executors) is the right abstraction

---

## 5. Utility Tools (`brain/tools/utility_tools.py`)

### Purpose
Miscellaneous utility operations. Details not fully exposed in the shared summaries, but the module exists and is dispatched through the same execution spine.

### Notes for New Framework
- Utility tools should remain a catch-all family for operations that don't fit web, local read, finance, or coding categories
- Examples likely include: timestamp generation, formatting, hashing, text manipulation

---

## 6. Execution Spine (`brain/tools/executor.py`)

### Purpose
Central dispatcher for all tool calls. Receives a `ToolRequest`, routes to the appropriate tool family, enforces governance context, and returns a `ToolResult`.

### Key Patterns
- `run_tool(req, enabled_tools, governance_ctx)` — single entry point
- `enabled_tools: Optional[Set[str]]` — allowlist of permitted tool names for this call
- `governance_ctx` — governance context passed through for audit and enforcement
- All tool calls are async

### Notes for New Framework
- Single entry point is the right pattern — never call tool implementations directly
- `enabled_tools` allowlist is a critical safety mechanism — default deny
- Governance context should be threaded through every call for auditability

---

## 7. Tool Registry (`brain/tools/registry.py`)

### Key Types
- `ToolFamily(str, Enum)` — families: likely `WEB`, `LOCAL_READ`, `FINANCE`, `CODING`, `UTILITY`
- `ToolDef(frozen dataclass)` — name, family, description, schema
- `is_known_tool(tool_name)` — existence check
- `is_tool_allowed(tool_name, enabled_tools)` — allowlist check

### Notes for New Framework
- Registry pattern is essential — tools must be declared before they can be called
- `is_tool_allowed` with an explicit `enabled_tools` set is the right default-deny pattern
- `ToolDef` should include a schema for input validation

---

## 8. Tool Contract Types (`brain/tools/types.py`)

### Key Types

| Type | Description |
|---|---|
| `ToolRequest` | Input to any tool call. Fields: `tool_name`, `args`, `purpose`, `task_id`, `step_id`, `user_id`, `chat_id` |
| `ToolResult` | Output of any tool call. Fields: `ok`, `tool_name`, `primary`, `provenance`, `failure_class`, `failure_message`, `started_at`, `ended_at`, `latency_ms` |
| `ToolProvenance` | Audit trail. Fields: `sources`, `retrieved_at`, `notes` |
| `ToolFailureClass(str, Enum)` | Failure taxonomy: `TOOL_BAD_INPUT`, `TOOL_NOT_ALLOWED`, `TOOL_TIMEOUT`, `TOOL_UPSTREAM_ERROR`, `TOOL_PARSE_ERROR`, `TOOL_INTERNAL_ERROR` |

### Notes for New Framework
- `ToolRequest` / `ToolResult` contract is clean and worth preserving exactly
- `ToolProvenance` on every result is non-negotiable for auditability
- `ToolFailureClass` taxonomy is comprehensive — reuse it
- `latency_ms` on every result is good operational hygiene

---

## 9. Task Ledger (`brain/tools/task_ledger.py`)

### Purpose
Persistent task and artifact tracking. Tasks have a title and optional resume hint. Artifacts are attached to tasks with a type, optional path, optional metadata JSON, and optional step ID.

### Notes for New Framework
- Task ledger is the right pattern for long-running or multi-step operations
- Artifacts should be stored before execution (plan) and after (result) for full auditability
- Step IDs allow sub-task granularity within a task

---

## 10. OKD Execution Model (`governance/operational_knowledge/okd_execution_v1.md`)

### Purpose
Governed observation and reasoning framework. Defines the full lifecycle for any observation task Alice performs.

### Key Patterns Worth Preserving

1. **Propose → Preview → Execute → Review → Certify** lifecycle
2. **Observation Plan artifact** stored before execution (intent, queries, scope budget, risk tier)
3. **Expansion Log artifact** during execution (all reformulations, retries, scope expansions)
4. **Update Brief artifact** after execution (facts with citations, inferences labeled, conflicts, uncertainties)
5. **Hard disclosure rules** — all expansions, retries, reformulations must be disclosed
6. **Fail-closed semantics** — partial results not returned on failure
7. **Default caps** (4 queries, 6 opens, depth 2, 2 retries per action) raiseable only with explicit Admin approval

### Notes for New Framework
- The OKD lifecycle is the right model for any multi-step observation task
- Artifacts must be stored at each phase — not just at the end
- Disclosure is not optional — it is a hard requirement
- Fail-closed is the only acceptable failure mode

---

*Last updated: 2026-02-01 | Owner: Admin (Tim)*
