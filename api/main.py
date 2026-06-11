import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from mem0 import Memory
from pydantic import BaseModel

_API_KEY = os.environ["MEM0_API_KEY"]
_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0",
            "host": os.environ.get("QDRANT_HOST", "qdrant"),
            "port": int(os.environ.get("QDRANT_PORT", 6333)),
            "embedding_model_dims": 3072,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "glm-4.7-flash",
            "api_key": os.environ["ZAI_API_KEY"],
            "openai_base_url": _ZAI_BASE_URL,
        },
    },
    "embedder": {
        "provider": "gemini",
        "config": {
            "model": "models/gemini-embedding-001",
            "embedding_dims": 3072,
            "api_key": os.environ["GOOGLE_API_KEY"],
        },
    },
}

memory: Memory | None = None


async def _wait_for_qdrant(host: str, port: int, timeout: int = 60) -> None:
    """Block until Qdrant responds to /healthz. Avoids leaking Gemini
    clients in Memory.from_config() retry loops when Qdrant isn't ready."""
    url = f"http://{host}:{port}/healthz"
    async with httpx.AsyncClient(timeout=3) as client:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return
            except (httpx.ConnectError, httpx.ReadError):
                pass
            await asyncio.sleep(2)
        raise RuntimeError(f"Qdrant at {url} not healthy after {timeout}s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory
    # Wait for Qdrant first — avoids retry-loop hammering of Gemini client
    qdrant_host = os.environ.get("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.environ.get("QDRANT_PORT", 6333))
    await _wait_for_qdrant(qdrant_host, qdrant_port)

    for attempt in range(6):
        try:
            memory = Memory.from_config(_config)
            break
        except Exception as exc:
            if attempt == 5:
                raise RuntimeError(f"Startup failed after 6 retries: {exc}") from exc
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
