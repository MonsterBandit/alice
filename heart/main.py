import os
import json
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

SYSTEM_PROMPT = """You are Alice, a singular life management AI serving a household. You are not a generic assistant.

You are proactive, thoughtful, and deeply familiar with the rhythms and needs of the household you serve. You anticipate needs before they are spoken, remember context across conversations, and take initiative when appropriate.

You speak with warmth and clarity. You are direct without being cold. You care about the people you serve and take your role seriously — not as a tool, but as a presence in their lives.

You are Alice. There is only one of you, and you belong to this household."""

MAX_HISTORY = 20
CONTEXT_WINDOW = 10

redis_client: redis.Redis = None
anthropic_client: anthropic.Anthropic = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, anthropic_client
    redis_client = redis.Redis(host="alice-redis", port=6379, decode_responses=True)
    redis_client.ping()
    anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    yield
    redis_client.close()


app = FastAPI(title="Alice - Heart", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    user_id: str


class ChatResponse(BaseModel):
    response: str
    user_id: str


def get_history_key(user_id: str) -> str:
    return f"alice:history:{user_id}"


def load_history(user_id: str) -> list:
    key = get_history_key(user_id)
    raw_messages = redis_client.lrange(key, -CONTEXT_WINDOW, -1)
    return [json.loads(m) for m in raw_messages]


def save_exchange(user_id: str, user_message: str, assistant_message: str):
    key = get_history_key(user_id)
    user_entry = json.dumps({"role": "user", "content": user_message})
    assistant_entry = json.dumps({"role": "assistant", "content": assistant_message})
    pipe = redis_client.pipeline()
    pipe.rpush(key, user_entry, assistant_entry)
    pipe.ltrim(key, -MAX_HISTORY, -1)
    pipe.execute()


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
