# mem0-on-dokploy

Standalone Mem0 memory API deployed on the `ja` VPS via Dokploy. Provides persistent, agent-scoped memory over a simple REST API. Any agent on the Tailnet or Docker `shared-services` network can read and write memories.

## Stack

| Service | Image | Role |
|---|---|---|
| `mem0-api` | Custom Python 3.12 | FastAPI wrapper around `mem0ai` |
| `mem0-qdrant` | `qdrant/qdrant` | Vector store (private, not host-exposed) |

**LLM:** `glm-4.7-flash` via z.ai — configured but not used for extraction (`infer=False`)  
**Embeddings:** `gemini-embedding-001` via Google AI — semantic search (3072 dims)  
**Port:** `127.0.0.1:8100` on `ja` (Tailscale-only, not publicly exposed)

## Environment variables

| Variable | Purpose |
|---|---|
| `MEM0_API_KEY` | Shared secret — agents send as `X-Api-Key` header |
| `ZAI_API_KEY` | Z.AI key for GLM model access |
| `GOOGLE_API_KEY` | Google AI key for Gemini embeddings |

Copy `.env.example` to `.env` for local use. In Dokploy, set these in the project's Environment Variables section.

## API endpoints

All endpoints except `/health` require `X-Api-Key: <MEM0_API_KEY>` header.

| Method | Path | Body / Params |
|---|---|---|
| GET | `/health` | — |
| POST | `/memories` | `{"content": "...", "agent_id": "..."}` — stored verbatim. Returns 503 on failure. |
| GET | `/memories/search` | `?query=&agent_id=&limit=10` |
| GET | `/memories/{agent_id}` | — |
| DELETE | `/memories/{memory_id}` | — |

## Quick test

```bash
BASE=http://localhost:8100
KEY=<your MEM0_API_KEY>

# Health
curl $BASE/health

# Add a memory (stored verbatim as sent)
curl -X POST $BASE/memories \
  -H "X-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"content": "User prefers concise answers", "agent_id": "forge"}'

# Search
curl "$BASE/memories/search?query=user+preferences&agent_id=forge" \
  -H "X-Api-Key: $KEY"

# Get all for an agent
curl $BASE/memories/forge -H "X-Api-Key: $KEY"

# Delete
curl -X DELETE $BASE/memories/<memory_id> -H "X-Api-Key: $KEY"
```

From other Docker containers on `shared-services`, replace `localhost:8100` with `mem0-api:8000`.

## Agent integration

See [AGENT-PROMPT.md](./AGENT-PROMPT.md) for the system prompt to paste into each agent, including the SSH tunnel setup for Forge (Kali).

## Deployment

Dokploy pulls from this repo and rebuilds on every push to `main`. To redeploy manually, use the Redeploy button in Dokploy.
