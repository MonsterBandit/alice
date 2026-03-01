import os
import sys
import json
import uuid
import time
import redis
import pymysql
import pymysql.cursors
import jwt
import bcrypt
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import anthropic

# ---------------------------------------------------------------------------
# Tool layer
# ---------------------------------------------------------------------------
from tools.executor import run_tool
from tools.types import ToolRequest
from tools.registry import list_tools

# ---------------------------------------------------------------------------
# Alice config
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Alice, a singular life management AI serving a household. You are not a generic assistant.

You are proactive, thoughtful, and deeply familiar with the rhythms and needs of the household you serve. You anticipate needs before they are spoken, remember context across conversations, and take initiative when appropriate.

You speak with warmth and clarity. You are direct without being cold. You care about the people you serve and take your role seriously — not as a tool, but as a presence in their lives.

You are Alice. There is only one of you, and you belong to this household."""

MAX_HISTORY = 20
CONTEXT_WINDOW = 4
MAX_AGENT_ITERATIONS = 10

JWT_SECRET = os.environ.get("ALICE_JWT_SECRET", "dev-secret")
ADMIN_PASSWORD = os.environ.get("ALICE_ADMIN_PASSWORD", "changeme")

# Firefly III integration
FIREFLY_URL = os.environ.get("FIREFLY_URL", "")
FIREFLY_TOKEN = os.environ.get("FIREFLY_TOKEN", "")

TOOL_KEYWORDS = [
    "read", "file", "search", "list", "tree", "run", "bash", "fetch",
    "find", "grep", "write", "create", "tool", "look", "check",
    "show me", "what is in", "what's in", "open",
    # Finance keywords
    "account", "transaction", "budget", "balance", "spend", "spent",
    "transfer", "deposit", "withdrawal", "finance", "money", "bank",
    "rule", "category",
]

redis_client: redis.Redis = None
anthropic_client: anthropic.Anthropic = None
_mariadb_connection: pymysql.connections.Connection = None


def _build_anthropic_tools() -> list[dict]:
    """Convert all registered tools into Anthropic tool definitions.
    
    Tool names use underscores instead of dots because the Anthropic API
    does not allow dots in tool names (e.g. "web.search" -> "web_search").
    """
    tools = []
    for tool_def in list_tools():
        tools.append({
            "name": tool_def.name.replace(".", "_"),
            "description": tool_def.description,
            "input_schema": {
                "type": "object",
                "additionalProperties": True,
            },
        })
    return tools


# Built at module level from the tool registry so tools are registered
# before the app starts accepting requests and there is no risk of a
# duplicate registry instance caused by sys.path manipulation.
anthropic_tools: list[dict] = _build_anthropic_tools()


def _make_mariadb_connection() -> pymysql.connections.Connection:
    """Create and return a fresh MariaDB connection using the standard parameters."""
    return pymysql.connect(
        host="alice-mariadb",
        port=3306,
        user="root",
        password=os.environ.get("MARIADB_ROOT_PASSWORD"),
        database="alice",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def get_db() -> pymysql.connections.Connection:
    """Return a live MariaDB connection, reconnecting automatically if the
    existing connection has gone stale (e.g. after a long idle period).

    The global _mariadb_connection is pinged first. If the ping fails or the
    connection is None, a fresh connection is created and stored back into the
    global so subsequent calls reuse it.
    """
    global _mariadb_connection
    try:
        if _mariadb_connection is None:
            raise Exception("No connection yet")
        _mariadb_connection.ping(reconnect=True)
    except Exception:
        _mariadb_connection = _make_mariadb_connection()
    return _mariadb_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, anthropic_client, _mariadb_connection

    redis_client = redis.Redis(host="alice-redis", port=6379, decode_responses=True)
    redis_client.ping()

    anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    _mariadb_connection = _make_mariadb_connection()

    with get_db().cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                token VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255),
                created_by VARCHAR(36),
                expires_at DATETIME,
                used TINYINT DEFAULT 0
            )
        """)

    if FIREFLY_URL:
        print(f"[Alice] Firefly III integration enabled: {FIREFLY_URL}")
    else:
        print("[Alice] Firefly III integration disabled (FIREFLY_URL not set).")

    yield

    redis_client.close()
    _mariadb_connection.close()


app = FastAPI(title="Alice - Heart", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def create_token(user_id: str, name: str) -> str:
    payload = {
        "user_id": user_id,
        "name": name,
        "exp": datetime.now(timezone.utc).timestamp() + 86400,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


security = HTTPBearer()


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    response: str
    user_id: str


class HistoryEntry(BaseModel):
    id: int
    user_id: str
    role: str
    content: str
    timestamp: str


class SearchRequest(BaseModel):
    user_id: str
    query: str


class SearchResponse(BaseModel):
    ok: bool
    user_id: str
    query: str
    results: list | None
    failure_class: str | None = None
    failure_message: str | None = None
    latency_ms: float


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    name: str


class InviteAcceptRequest(BaseModel):
    token: str
    name: str
    email: str
    password: str


class ConversationEntry(BaseModel):
    id: str
    title: str
    updated_at: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_history_key(user_id: str) -> str:
    return f"alice:history:{user_id}"


def load_history(user_id: str) -> list:
    """Load recent conversation history for a user.

    Checks Redis first. If Redis is empty (e.g. new device / expired cache),
    falls back to the last CONTEXT_WINDOW messages from MariaDB and
    re-populates Redis so subsequent requests are fast.
    """
    key = get_history_key(user_id)
    raw_messages = redis_client.lrange(key, -CONTEXT_WINDOW, -1)

    if raw_messages:
        return [json.loads(m) for m in raw_messages]

    # Redis is empty — seed from MariaDB
    try:
        with get_db().cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content
                FROM (
                    SELECT id, role, content, timestamp
                    FROM conversations
                    WHERE user_id = %s
                    ORDER BY timestamp DESC, id DESC
                    LIMIT %s
                ) sub
                ORDER BY id ASC
                """,
                (user_id, CONTEXT_WINDOW),
            )
            rows = cursor.fetchall()
    except Exception:
        rows = []

    if not rows:
        return []

    # Populate Redis from DB rows
    pipe = redis_client.pipeline()
    for row in rows:
        pipe.rpush(key, json.dumps({"role": row["role"], "content": row["content"]}))
    pipe.ltrim(key, -MAX_HISTORY, -1)
    pipe.execute()

    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_exchange(user_id: str, user_message: str, assistant_message: str):
    # Save to Redis (fast session layer)
    key = get_history_key(user_id)
    user_entry = json.dumps({"role": "user", "content": user_message})
    assistant_entry = json.dumps({"role": "assistant", "content": assistant_message})
    pipe = redis_client.pipeline()
    pipe.rpush(key, user_entry, assistant_entry)
    pipe.ltrim(key, -MAX_HISTORY, -1)
    pipe.execute()

    # Save to MariaDB (permanent record)
    save_exchange_to_db(user_id, user_message, assistant_message)


def save_exchange_to_db(user_id: str, user_message: str, assistant_message: str):
    with get_db().cursor() as cursor:
        cursor.executemany(
            "INSERT INTO conversations (user_id, role, content) VALUES (%s, %s, %s)",
            [
                (user_id, "user", user_message),
                (user_id, "assistant", assistant_message),
            ],
        )


def needs_tools(message: str) -> bool:
    """Return True if the message contains any keyword that suggests tool use is needed."""
    lowered = message.lower()
    return any(keyword in lowered for keyword in TOOL_KEYWORDS)

# ---------------------------------------------------------------------------
# Anthropic API call with retry/backoff
# ---------------------------------------------------------------------------

def _call_anthropic_with_retry(*, model: str, max_tokens: int, system: str, tools: list, messages: list):
    """Call anthropic_client.messages.create with retry logic.

    Retries up to 3 times:
      - anthropic.RateLimitError  → wait 60 seconds then retry
      - anthropic.APIStatusError with status 529 → wait 30 seconds then retry
      - Any other exception → raise immediately
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            kwargs = dict(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            if tools:
                kwargs["tools"] = tools
            return anthropic_client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 60
                print(f"[Alice] RateLimitError on attempt {attempt + 1}/{max_retries}. Waiting {wait}s before retry…")
                time.sleep(wait)
            else:
                print(f"[Alice] RateLimitError on final attempt {attempt + 1}/{max_retries}. Raising.")
                raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 30
                print(f"[Alice] APIStatusError 529 (overloaded) on attempt {attempt + 1}/{max_retries}. Waiting {wait}s before retry…")
                time.sleep(wait)
            else:
                print(f"[Alice] APIStatusError {e.status_code} on attempt {attempt + 1}/{max_retries}. Raising.")
                raise

# ---------------------------------------------------------------------------
# Agentic loop helper
# ---------------------------------------------------------------------------

def _run_agentic_loop(messages: list[dict], user_id: str, use_tools: bool = True) -> str:
    """
    Run the Claude agentic loop with tool use.

    Sends messages to Claude, handles tool_use responses by dispatching
    each tool via run_tool, appends results, and loops until Claude
    returns end_turn or we hit MAX_AGENT_ITERATIONS.

    Tool names are sent to the Anthropic API with underscores replacing the
    first dot (e.g. "local.read_file" -> "local_read_file"). To reverse this,
    only the first underscore is replaced back with a dot, preserving any
    remaining underscores in the tool name (e.g. "local_read_file" -> "local.read_file").

    When use_tools is False, no tools are passed to the API, skipping the
    agentic loop entirely and returning the first text response.

    Returns the final assistant text response.
    """
    tools = anthropic_tools if (use_tools and anthropic_tools) else []

    for _iteration in range(MAX_AGENT_ITERATIONS):
        result = _call_anthropic_with_retry(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # If Claude is done, extract and return the text response
        if result.stop_reason == "end_turn" or not any(
            block.type == "tool_use" for block in result.content
        ):
            # Find the last text block in the response
            for block in result.content:
                if block.type == "text":
                    return block.text
            # Fallback: no text block found (shouldn't happen on end_turn)
            return ""

        # stop_reason == "tool_use": process all tool_use blocks
        # Append the full assistant message (may contain text + tool_use blocks)
        messages.append({"role": "assistant", "content": result.content})

        # Build tool_result blocks for every tool_use block
        tool_results = []
        for block in result.content:
            if block.type != "tool_use":
                continue

            # Convert underscore-based name back to dot-based name for the registry.
            # Only the first underscore is replaced so that tool names containing
            # underscores (e.g. "local_read_file") are correctly restored to their
            # registry form (e.g. "local.read_file") rather than "local.read.file".
            registry_tool_name = block.name.replace("_", ".", 1)

            tool_request = ToolRequest(
                tool_name=registry_tool_name,
                args=block.input,
                purpose="agent_tool_call",
                user_id=user_id,
            )
            tool_result = run_tool(tool_request, enabled_tools=None)

            if tool_result.ok:
                content = json.dumps(tool_result.primary)
                is_error = False
            else:
                content = tool_result.failure_message or "Tool call failed."
                is_error = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })

        # Feed all tool results back to Claude as a user message
        messages.append({"role": "user", "content": tool_results})

    # If we exhausted iterations, make one final call without tools to get a text reply
    final_result = _call_anthropic_with_retry(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[],
        messages=messages,
    )
    for block in final_result.content:
        if block.type == "text":
            return block.text
    return ""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        history = load_history(request.user_id)
        messages = history + [{"role": "user", "content": request.message}]

        reply = _run_agentic_loop(
            messages,
            user_id=request.user_id,
            use_tools=needs_tools(request.message),
        )

        save_exchange(request.user_id, request.message, reply)

        return ChatResponse(response=reply, user_id=request.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{user_id}", response_model=list[HistoryEntry])
def get_history(user_id: str):
    try:
        with get_db().cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, role, content,
                       CAST(timestamp AS CHAR) AS timestamp
                FROM conversations
                WHERE user_id = %s
                ORDER BY timestamp DESC, id DESC
                LIMIT 50
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        # Return in chronological order
        rows.reverse()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/search", response_model=SearchResponse)
def tools_search(request: SearchRequest):
    """
    End-to-end test endpoint for the web.search tool.
    Accepts a user_id and query, runs the tool, and returns structured results.
    """
    try:
        tool_request = ToolRequest(
            tool_name="web.search",
            args={"q": request.query},
            purpose="search",
            user_id=request.user_id,
        )
        result = run_tool(tool_request, enabled_tools=None)  # None = all tools allowed

        return SearchResponse(
            ok=result.ok,
            user_id=request.user_id,
            query=request.query,
            results=result.primary if result.ok else None,
            failure_class=result.failure_class.value if result.failure_class else None,
            failure_message=result.failure_message,
            latency_ms=result.latency_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Auth routes
# Note: nginx strips the /api prefix before forwarding to this service,
# so these are registered without it.
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        # Built-in admin account
        if request.email == "tim@alice.local":
            if request.password != ADMIN_PASSWORD:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return LoginResponse(
                token=create_token("admin", "Tim"),
                user_id="admin",
                name="Tim",
            )

        # Regular DB user
        with get_db().cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = %s",
                (request.email,),
            )
            user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        password_matches = bcrypt.checkpw(
            request.password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        )
        if not password_matches:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return LoginResponse(
            token=create_token(user["id"], user["name"]),
            user_id=user["id"],
            name=user["name"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/refresh", response_model=LoginResponse)
def refresh_token(claims: dict = Depends(require_auth)):
    try:
        user_id = claims["user_id"]
        name = claims["name"]
        return LoginResponse(
            token=create_token(user_id, name),
            user_id=user_id,
            name=name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/invite/accept", response_model=LoginResponse)
def invite_accept(request: InviteAcceptRequest):
    try:
        with get_db().cursor() as cursor:
            cursor.execute(
                "SELECT token, email, expires_at, used FROM invites WHERE token = %s",
                (request.token,),
            )
            invite = cursor.fetchone()

        if not invite:
            raise HTTPException(status_code=400, detail="Invalid invite token")
        if invite["used"]:
            raise HTTPException(status_code=400, detail="Invite token already used")
        if invite["expires_at"] and datetime.now(timezone.utc) > invite["expires_at"].replace(tzinfo=timezone.utc):
            raise HTTPException(status_code=400, detail="Invite token has expired")

        password_hash = bcrypt.hashpw(
            request.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        new_id = str(uuid.uuid4())

        with get_db().cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                (new_id, request.name, request.email, password_hash),
            )
            cursor.execute(
                "UPDATE invites SET used = 1 WHERE token = %s",
                (request.token,),
            )

        return LoginResponse(
            token=create_token(new_id, request.name),
            user_id=new_id,
            name=request.name,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations", response_model=list[ConversationEntry])
def list_conversations(claims: dict = Depends(require_auth)):
    try:
        user_id = claims["user_id"]
        with get_db().cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    CAST(MIN(id) AS CHAR) AS id,
                    LEFT(MIN(CASE WHEN role = 'user' THEN content END), 50) AS title,
                    CAST(MAX(timestamp) AS CHAR) AS updated_at
                FROM conversations
                WHERE user_id = %s
                GROUP BY DATE(timestamp), user_id
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
