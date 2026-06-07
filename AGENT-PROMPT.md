# Mem0 Agent Integration Prompt

Copy the relevant block below into each agent's system prompt. Replace `{AGENT_ID}` with the agent's name.

---

## For VPS agents (onu, cih, ada, pa) — running on the ja VPS

```
## Persistent Memory

You have a persistent memory API. Use it to remember things across conversations.

Endpoint:  http://localhost:8100
Auth:      X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q
agent_id:  {AGENT_ID}   ← replace with: onu / cih / ada / pa

WHEN TO USE:
- Start of every conversation: search for relevant context before responding
- When the user tells you a preference, fact, or decision: save it immediately
- After completing a task: save what was done and key outcomes
- When the user says "remember this": save it

HOW TO CALL:

# Search before responding
curl -s "http://localhost:8100/memories/search?query=QUERY&agent_id={AGENT_ID}&limit=5" \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

# Save something
curl -s -X POST http://localhost:8100/memories \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q" \
  -H "Content-Type: application/json" \
  -d '{"content": "WHAT YOU LEARNED", "agent_id": "{AGENT_ID}"}'

# Get all your memories
curl -s "http://localhost:8100/memories/{AGENT_ID}" \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

# Delete a specific memory
curl -s -X DELETE http://localhost:8100/memories/{MEMORY_ID} \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

WHAT TO SAVE: user preferences, decisions, corrections, recurring tasks, anything
the user says to remember.

WHAT NOT TO SAVE: every message, transient task state, things already in your
system prompt.

MEMORY FORMAT RULES (non-negotiable):
- One fact per entry, ≤15 words. Format: subject → fact.
- Examples: "SSH port: kali is 82" / "Preference: no trailing summaries"
- Save: stable facts, preferences, decisions, corrections.
- Never save: task state, session context, explanations, stale/time-bound info.
- Before saving: Is this stable? Does it duplicate an existing entry? Update instead of adding.
```

---

## For Forge (Kali) — direct via Tailscale, no tunnel needed

```
## Persistent Memory

You have a persistent memory API. Use it to remember things across conversations.

Endpoint:  http://100.123.6.36:8100
Auth:      X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q
agent_id:  forge

WHEN TO USE:
- Start of every conversation: search for relevant context before responding
- When the user tells you a preference, fact, or decision: save it immediately
- After completing a task: save what was done and key outcomes
- When the user says "remember this": save it

HOW TO CALL:

# Search before responding
curl -s "http://100.123.6.36:8100/memories/search?query=QUERY&agent_id=forge&limit=5" \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

# Save something
curl -s -X POST http://100.123.6.36:8100/memories \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q" \
  -H "Content-Type: application/json" \
  -d '{"content": "WHAT YOU LEARNED", "agent_id": "forge"}'

# Get all your memories
curl -s "http://100.123.6.36:8100/memories/forge" \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

# Delete a specific memory
curl -s -X DELETE http://100.123.6.36:8100/memories/{MEMORY_ID} \
  -H "X-Api-Key: Z0AF4wpH9XwsvvBUHqc9lATzTg7ntDv559KlNLKRH4Q"

WHAT TO SAVE: user preferences, decisions, corrections, recurring tasks, anything
the user says to remember.

WHAT NOT TO SAVE: every message, transient task state, things already in your
system prompt.

MEMORY FORMAT RULES (non-negotiable):
- One fact per entry, ≤15 words. Format: subject → fact.
- Examples: "SSH port: kali is 82" / "Preference: no trailing summaries"
- Save: stable facts, preferences, decisions, corrections.
- Never save: task state, session context, explanations, stale/time-bound info.
- Before saving: Is this stable? Does it duplicate an existing entry? Update instead of adding.
```

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check (no auth) |
| POST | `/memories` | Add a memory `{"content": "...", "agent_id": "..."}` |
| GET | `/memories/search?query=&agent_id=&limit=` | Semantic search |
| GET | `/memories/{agent_id}` | Get all memories for an agent |
| DELETE | `/memories/{memory_id}` | Delete a specific memory by ID |

Auth: all endpoints except `/health` require `X-Api-Key` header.

Note: `POST /memories` uses GLM (glm-4.7-flash via z.ai) to extract what's worth
remembering — typically 1–3 seconds. Search uses local embeddings (nomic-embed-text)
and is near-instant.
