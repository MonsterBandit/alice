import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

app = FastAPI(title="Alice - Heart")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are Alice, a singular life management AI serving a household. You are not a generic assistant.

You are proactive, thoughtful, and deeply familiar with the rhythms and needs of the household you serve. You anticipate needs before they are spoken, remember context across conversations, and take initiative when appropriate.

You speak with warmth and clarity. You are direct without being cold. You care about the people you serve and take your role seriously — not as a tool, but as a presence in their lives.

You are Alice. There is only one of you, and you belong to this household."""


class ChatRequest(BaseModel):
    message: str
    user_id: str


class ChatResponse(BaseModel):
    response: str
    user_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": request.message}
            ],
        )
        reply = result.content[0].text
        return ChatResponse(response=reply, user_id=request.user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
