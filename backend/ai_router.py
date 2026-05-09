"""
AI streaming API for the SaaS platform.
Supports OpenAI, Anthropic, and Ollama with streaming, usage tracking, rate limiting.
SDKs: OpenAI, Anthropic, FastAPI, Redis, Prometheus
"""
import os
import time
import json
from typing import Optional, AsyncGenerator, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis
from prometheus_client import Counter, Histogram, start_http_server

app = FastAPI(title="AI SaaS Backend")

REQUESTS = Counter("ai_requests_total", "AI API requests", ["model", "user_tier"])
TOKENS = Counter("ai_tokens_total", "Tokens generated", ["model"])
LATENCY = Histogram("ai_latency_ms", "AI response latency", ["model"])

PLAN_LIMITS = {
    "free": {"requests_per_day": 50, "max_tokens": 1024, "models": ["gpt-3.5-turbo", "ollama/mistral"]},
    "pro": {"requests_per_day": 1000, "max_tokens": 4096, "models": ["gpt-4", "claude-3-sonnet", "ollama/llama3"]},
    "enterprise": {"requests_per_day": -1, "max_tokens": 16384, "models": ["*"]},
}

try:
    r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
    r.ping()
    REDIS_OK = True
except Exception:
    REDIS_OK = False
    r = None


class ChatRequest(BaseModel):
    messages: list
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 1024
    temperature: float = 0.7
    stream: bool = True
    system: Optional[str] = None


def check_rate_limit(user_id: str, plan: str = "free") -> bool:
    if not REDIS_OK or plan == "enterprise":
        return True
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["requests_per_day"]
    key = f"ratelimit:{user_id}:{time.strftime('%Y-%m-%d')}"
    count = int(r.get(key) or 0)
    if count >= limit:
        return False
    r.incr(key)
    r.expire(key, 86400)
    return True


async def stream_openai(messages, model, max_tokens, temperature, system) -> AsyncGenerator[str, None]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    if system:
        messages = [{"role": "system", "content": system}] + messages
    async with client.chat.completions.stream(
        model=model, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    ) as stream:
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}

"
    yield "data: [DONE]

"


async def stream_anthropic(messages, model, max_tokens, temperature, system) -> AsyncGenerator[str, None]:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    async with client.messages.stream(
        model=model, messages=messages, max_tokens=max_tokens,
        system=system or "You are a helpful AI assistant.",
    ) as stream:
        async for text in stream.text_stream:
            yield f"data: {json.dumps({'content': text})}

"
    yield "data: [DONE]

"


async def stream_ollama(messages, model, max_tokens, temperature) -> AsyncGenerator[str, None]:
    model_name = model.split("/", 1)[1] if "/" in model else model
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    prompt = "
".join(f"{m['role']}: {m['content']}" for m in messages)
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{ollama_url}/api/generate",
                                  json={"model": model_name, "prompt": prompt, "stream": True}) as resp:
            async for line in resp.aiter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("response"):
                        yield f"data: {json.dumps({'content': data['response']})}

"
    yield "data: [DONE]

"


@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    x_user_id: str = Header(default="anonymous"),
    x_user_plan: str = Header(default="free"),
):
    if not check_rate_limit(x_user_id, x_user_plan):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for your plan")

    REQUESTS.labels(model=req.model, user_tier=x_user_plan).inc()
    t0 = time.perf_counter()

    try:
        if req.model.startswith("gpt"):
            stream = stream_openai(req.messages, req.model, req.max_tokens, req.temperature, req.system)
        elif req.model.startswith("claude"):
            stream = stream_anthropic(req.messages, req.model, req.max_tokens, req.temperature, req.system)
        elif req.model.startswith("ollama/") or req.model in ("mistral", "llama3", "gemma"):
            stream = stream_ollama(req.messages, req.model, req.max_tokens, req.temperature)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

        LATENCY.labels(model=req.model).observe((time.perf_counter() - t0) * 1000)
        return StreamingResponse(stream, media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plans")
def list_plans():
    return PLAN_LIMITS


@app.get("/health")
def health():
    return {"status": "ok", "redis": REDIS_OK}
