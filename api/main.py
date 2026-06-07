import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from mem0 import Memory
from pydantic import BaseModel

_API_KEY = os.environ["MEM0_API_KEY"]
_OLLAMA_BASE_URL = f"http://{os.environ.get('OLLAMA_HOST', 'ollama')}:{os.environ.get('OLLAMA_PORT', '11434')}"

_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0",
            "host": os.environ.get("QDRANT_HOST", "qdrant"),
            "port": int(os.environ.get("QDRANT_PORT", 6333)),
            "embedding_model_dims": 768,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "gemma2:2b",
            "ollama_base_url": _OLLAMA_BASE_URL,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": _OLLAMA_BASE_URL,
        },
    },
}

memory: Memory | None = None

_MODELS = ["gemma2:2b", "nomic-embed-text"]


async def _ensure_models() -> None:
    """Pull Ollama models via REST API if not already cached."""
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.get(f"{_OLLAMA_BASE_URL}/api/tags")
        cached = {m.get("name", "") for m in resp.json().get("models", [])}
        for model in _MODELS:
            if not any(c.startswith(model.split(":")[0]) for c in cached):
                async with client.stream(
                    "POST", f"{_OLLAMA_BASE_URL}/api/pull", json={"name": model}
                ) as r:
                    async for _ in r.aiter_lines():
                        pass  # drain stream, model downloads in background


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory
    for attempt in range(60):
        try:
            await _ensure_models()
            memory = Memory.from_config(_config)
            break
        except Exception as exc:
            if attempt == 59:
                raise RuntimeError(f"Startup failed after 60 retries: {exc}") from exc
            await asyncio.sleep(5)
    yield


app = FastAPI(title="Mem0 API", lifespan=lifespan)


def _auth(x_api_key: str = Header(...)):
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class AddRequest(BaseModel):
    content: str
    agent_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/memories", dependencies=[Depends(_auth)])
def add_memory(req: AddRequest):
    return memory.add(req.content, agent_id=req.agent_id)


# /memories/search must be defined before /memories/{agent_id} so FastAPI
# matches the literal path before the parameterised one.
@app.get("/memories/search", dependencies=[Depends(_auth)])
def search(query: str, agent_id: str, limit: int = 10):
    return memory.search(query, filters={"agent_id": agent_id}, limit=limit)


@app.get("/memories/{agent_id}", dependencies=[Depends(_auth)])
def get_all(agent_id: str):
    return memory.get_all(filters={"agent_id": agent_id})


@app.delete("/memories/{memory_id}", dependencies=[Depends(_auth)])
def delete_memory(memory_id: str):
    memory.delete(memory_id)
    return {"deleted": memory_id}
