import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from mem0 import Memory
from pydantic import BaseModel

_API_KEY = os.environ["MEM0_API_KEY"]
_ZAI_API_KEY = os.environ["ZAI_API_KEY"]
_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0",
            "host": os.environ.get("QDRANT_HOST", "qdrant"),
            "port": int(os.environ.get("QDRANT_PORT", 6333)),
            "embedding_model_dims": 2048,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "glm-4-flash",
            "api_key": _ZAI_API_KEY,
            "openai_base_url": _ZAI_BASE_URL,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "embedding-3",
            "api_key": _ZAI_API_KEY,
            "openai_base_url": _ZAI_BASE_URL,
        },
    },
}

memory: Memory | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory
    for attempt in range(10):
        try:
            memory = Memory.from_config(_config)
            break
        except Exception as exc:
            if attempt == 9:
                raise RuntimeError(f"Qdrant unavailable after 10 retries: {exc}") from exc
            await asyncio.sleep(3)
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
