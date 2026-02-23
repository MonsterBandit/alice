import os
import sys
import json
import redis
import pymysql
import pymysql.cursors
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

# ---------------------------------------------------------------------------
# Tool layer
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.executor import run_tool
from tools.types import ToolRequest

# ---------------------------------------------------------------------------
# Alice config
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Alice, a singular life management AI serving a household. You are not a generic assistant.

You are proactive, thoughtful, and deeply familiar with the rhythms and needs of the household you serve. You anticipate needs before they are spoken, remember context across conversations, and take initiative when appropriate.

You speak with warmth and clarity. You are direct without being cold. You care about the people you serve and take your role seriously — not as a tool, but as a presence in their lives.

You are Alice. There is only one of you, and you belong to this household."""

MAX_HISTORY = 20
CONTEXT_WINDOW = 10

redis_client: redis.Redis = None
anthropic_client: anthropic.Anthropic = None
mariadb_connection: pymysql.connections.Connection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, anthropic_client, mariadb_connection

    redis_client = redis.Redis(host="alice-redis", port=6379, decode_responses=True)
    redis_client.ping()

    anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    mariadb_connection = pymysql.connect(
        host="alice-mariadb",
        port=3306,
        user="root",
        password=os.environ.get("MARIADB_ROOT_PASSWORD"),
        database="alice",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

    with mariadb_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

    yield

    redis_client.close()
    mariadb_connection.close()


app = FastAPI(title="Alice - Heart", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str


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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_history_key(user_id: str) -> str:
    return f"alice:history:{user_id}"


def load_history(user_id: str) -> list:
    key = get_history_key(user_id)
    raw_messages = redis_client.lrange(key, -CONTEXT_WINDOW, -1)
    return [json.loads(m) for m in raw_messages]


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
    with mariadb_connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO conversations (user_id, role, content) VALUES (%s, %s, %s)",
            [
                (user_id, "user", user_message),
                (user_id, "assistant", assistant_message),
            ],
        )

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        history = load_history(request.user_id)
        messages = history + [{"role": "user", "content": request.message}]

        result = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = result.content[0].text

        save_exchange(request.user_id, request.message, reply)

        return ChatResponse(response=reply, user_id=request.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{user_id}", response_model=list[HistoryEntry])
def get_history(user_id: str):
    try:
        with mariadb_connection.cursor() as cursor:
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
