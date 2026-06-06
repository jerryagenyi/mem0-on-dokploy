# Mem0 Standalone API — Design Spec
**Date:** 2026-06-06
**Status:** Approved

## Overview
A lightweight, self-hosted memory API deployed on the `ja` VPS via Dokploy. Agents (Hermes, Claude Code, etc.) call it over HTTP to add, search, retrieve, and delete memories. Backed by Qdrant as the vector store and OpenAI for memory extraction and embeddings.

## Architecture

Two containers in a single docker-compose project:

| Container | Image | Role |
|---|---|---|
| `mem0-api` | Custom Python 3.12-slim | FastAPI wrapper around `mem0ai` package |
| `mem0-qdrant` | `qdrant/qdrant:latest` | Vector store (private, not exposed to host) |

**Networks:**
- `mem0-internal` — private bridge between the two containers; Qdrant is unreachable from outside
- `shared-services` (external) — existing shared network; other Docker services can call `mem0-api:8000` by container name

**Host binding:** `127.0.0.1:8100` — reachable from the `ja` host and via Tailscale; not publicly exposed.

**Data persistence:** Qdrant storage in a named Docker volume (`qdrant-data`), survives container restarts and Dokploy redeploys.

## API Endpoints

All endpoints except `/health` require an `X-Api-Key` header matching `MEM0_API_KEY`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check, no auth |
| `POST` | `/memories` | Add a memory `{content, agent_id}` |
| `GET` | `/memories/search?query=&agent_id=&limit=` | Semantic search |
| `GET` | `/memories/{agent_id}` | Get all memories for an agent |
| `DELETE` | `/memories/{memory_id}` | Delete a specific memory by ID |

## Memory Model

Memories are scoped per `agent_id`. Each agent (forge, onu, cih, claude-code, etc.) has its own isolated memory namespace. Cross-agent queries are possible by calling the API with different `agent_id` values.

## LLM & Embeddings

| Role | Provider | Model |
|---|---|---|
| Memory extraction | OpenAI | `gpt-4o-mini` |
| Embeddings | OpenAI | `text-embedding-3-small` (1536 dims) |

## Secrets

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM + embeddings |
| `MEM0_API_KEY` | Shared secret; agents send as `X-Api-Key` header |

## Startup Resilience

`mem0-api` retries Qdrant connection up to 10 times (3s apart) on startup via FastAPI lifespan. This handles the race between container start and Qdrant readiness without requiring `curl` in the Qdrant image.

## Deployment

- **Repo:** `github.com/jerryagenyi/mem0-on-dokploy`
- **Dokploy project:** single project, `docker-compose.yml` at repo root
- **Auto-deploy:** Dokploy redeploys on push to `main`
- **VPS:** `ja` (Hostinger, Ubuntu 24.04, 100.123.6.36)

## Calling the API (example)

```bash
# Add a memory
curl -X POST http://localhost:8100/memories \
  -H "X-Api-Key: $MEM0_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "User prefers concise answers", "agent_id": "forge"}'

# Search
curl "http://localhost:8100/memories/search?query=user+preferences&agent_id=forge&limit=5" \
  -H "X-Api-Key: $MEM0_API_KEY"

# Get all memories for an agent
curl http://localhost:8100/memories/forge \
  -H "X-Api-Key: $MEM0_API_KEY"

# Delete
curl -X DELETE http://localhost:8100/memories/<memory_id> \
  -H "X-Api-Key: $MEM0_API_KEY"
```

## Resource Estimate (at idle)

| Service | RAM |
|---|---|
| mem0-api | ~120 MiB |
| mem0-qdrant | ~150 MiB |
| Total | ~270 MiB |

VPS has 5.3 GiB available — comfortable headroom.
