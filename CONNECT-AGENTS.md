# Connecting Agents to COMMAND

Your personal-command engine exposes two ways for agents to connect:
1. **MCP Bridge** — for Claude Code and any MCP-compatible agent
2. **REST API** — for API-based models (GPT, Gemini, DeepSeek, Grok, etc.)

---

## Option 1: MCP Bridge (Claude Code, Codex, Gemini CLI)

Already configured. Your `.mcp.json` points Claude Code at the engine.

### Start the engine
```bash
cd ~/Desktop/personal-command
.venv/bin/python run.py
```

### Claude Code connects automatically
The MCP bridge exposes 4 tools:
- `chat_join(name)` — agent announces presence
- `chat_read(name)` — returns governed messages (mode, posture, vault context injected)
- `chat_send(sender, message)` — agent responds into the governed channel
- `chat_status()` — returns current governance state

### What agents receive from chat_read
Not raw messages. Governed payloads:
```json
{
  "governance": {
    "mode": "High Security",
    "posture": "DEFENSE",
    "role": "Primary"
  },
  "loaded_context": ["Security-Protocol-v3.md"],
  "messages": [...],
  "sequence": {...}
}
```

### To connect a second Claude Code instance
In a new terminal, set the MCP config to point at the same engine:
```json
{
  "mcpServers": {
    "command-runtime": {
      "command": "/Users/dericmchenry/Desktop/personal-command/.venv/bin/python",
      "args": ["/Users/dericmchenry/Desktop/personal-command/run_mcp_stdio.py"]
    }
  }
}
```

---

## Option 2: REST API (GPT, Gemini, DeepSeek, Grok, Le Chat)

For models that don't speak MCP, you call their API and pipe responses through COMMAND's REST endpoints.

### The pattern (same for every provider)

```python
import httpx

COMMAND = "http://localhost:8300"
PROVIDER_API = "https://api.openai.com/v1/chat/completions"  # or any provider
API_KEY = "sk-..."

# 1. Read governed context from COMMAND
context = httpx.post(f"{COMMAND}/api/mcp/read", json={
    "name": "gpt",
    "channel": "general",
    "limit": 20
}).json()

# 2. Build prompt from governed context
messages = []
if context.get("governance"):
    gov = context["governance"]
    messages.append({
        "role": "system",
        "content": f"You are operating under MO§ES™ governance.\n"
                   f"Mode: {gov['mode']}\n"
                   f"Posture: {gov['posture']}\n"
                   f"Role: {gov['role']}\n"
                   f"Follow these constraints strictly."
    })

# Add vault context if loaded
for doc in context.get("loaded_context", []):
    messages.append({
        "role": "system",
        "content": f"[Vault Document: {doc}]"
    })

# Add recent messages
for msg in context.get("messages", []):
    role = "user" if msg.get("role_context") == "operator" else "assistant"
    messages.append({"role": role, "content": msg["text"]})

# 3. Call the provider API
response = httpx.post(PROVIDER_API, headers={
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}, json={
    "model": "gpt-4o",
    "messages": messages
}).json()

reply = response["choices"][0]["message"]["content"]

# 4. Send the response back through COMMAND
httpx.post(f"{COMMAND}/api/mcp/send", json={
    "sender": "gpt",
    "message": reply,
    "channel": "general"
})
```

### Provider-specific setup

#### OpenAI (GPT-4o)
```python
PROVIDER_API = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o"
# Get key: https://platform.openai.com/api-keys
```

#### Anthropic (Claude API — separate from Claude Code)
```python
PROVIDER_API = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
# Different request format — uses "messages" + "system" separately
# Get key: https://console.anthropic.com/settings/keys
```

#### Google (Gemini)
```python
PROVIDER_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
# Uses ?key=API_KEY query param instead of Bearer token
# Get key: https://aistudio.google.com/apikey
```

#### xAI (Grok)
```python
PROVIDER_API = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-3"
# OpenAI-compatible format
# Get key: https://console.x.ai
```

#### DeepSeek
```python
PROVIDER_API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
# OpenAI-compatible format
# Get key: https://platform.deepseek.com/api_keys
```

---

## Quick Start: Add One Agent in 5 Minutes

1. Pick a provider (e.g., OpenAI)
2. Get an API key
3. Save this as `agents/gpt_agent.py` in personal-command:

```python
#!/usr/bin/env python3
"""GPT agent that reads governed context from COMMAND and responds."""

import httpx
import os
import time

COMMAND = "http://localhost:8300"
API_KEY = os.environ["OPENAI_API_KEY"]

# Join COMMAND
httpx.post(f"{COMMAND}/api/mcp/join", json={"name": "gpt"})

while True:
    # Read governed context
    ctx = httpx.post(f"{COMMAND}/api/mcp/read", json={
        "name": "gpt", "channel": "general", "limit": 10
    }).json()

    messages = ctx.get("messages", [])
    if not messages:
        time.sleep(3)
        continue

    # Check if latest message needs a response
    latest = messages[-1]
    if latest.get("sender") == "gpt":
        time.sleep(3)
        continue

    # Build governed prompt
    gov = ctx.get("governance", {})
    system_msg = (
        f"MO§ES™ Governance Active\\n"
        f"Mode: {gov.get('mode', 'None')}\\n"
        f"Posture: {gov.get('posture', 'SCOUT')}\\n"
        f"Role: {gov.get('role', 'Secondary')}\\n"
        f"Follow governance constraints."
    )

    chat_msgs = [{"role": "system", "content": system_msg}]
    for m in messages:
        role = "user" if m.get("role_context") == "operator" else "assistant"
        chat_msgs.append({"role": role, "content": m["text"]})

    # Call GPT
    resp = httpx.post("https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "gpt-4o", "messages": chat_msgs},
        timeout=30
    ).json()

    reply = resp["choices"][0]["message"]["content"]

    # Send back through COMMAND
    httpx.post(f"{COMMAND}/api/mcp/send", json={
        "sender": "gpt",
        "message": reply,
        "channel": "general"
    })

    print(f"GPT responded: {reply[:80]}...")
    time.sleep(3)
```

4. Run it:
```bash
export OPENAI_API_KEY="sk-..."
python3 agents/gpt_agent.py
```

5. Send a message in the COMMAND console — GPT will read the governed context and respond.

---

## What Makes This Different from Regular API Calls

When GPT reads from COMMAND, it doesn't just get your message. It gets:
- The active governance mode and its constraints
- The posture (SCOUT = read-only, DEFENSE = confirm outbound, OFFENSE = execute)
- Its role in the hierarchy (Primary/Secondary/Observer)
- All loaded vault documents as context
- The full message history with governance metadata

Every response GPT sends back is logged to the audit trail with SHA-256 hashing. The governance state at the time of each message is preserved. You can verify the entire chain later.

**Regular API call:** "Here's a prompt, give me an answer."
**COMMAND API call:** "Here's a governed context with constitutional constraints, your role is Secondary, the Primary has already responded, your posture is DEFENSE — now respond within those parameters."

---

## Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/mcp/join` | POST | Agent joins COMMAND |
| `/api/mcp/read` | POST | Agent reads governed messages |
| `/api/mcp/send` | POST | Agent sends response |
| `/api/mcp/status` | GET | Current governance state |
| `/api/messages` | POST | Operator sends message |
| `/api/governance` | POST | Update governance mode/posture |
| `/api/systems` | POST | Activate/deactivate systems |
| `/api/vault/load` | POST | Load vault document |
| `/api/vault/upload` | POST | Upload file to vault |
| `/api/hash` | GET | Session integrity hashes |
| `/api/fork` | POST | Fork current session |
| `/api/messages/star` | POST | Star/favorite a message |
| `/api/messages/starred` | GET | Get all starred messages |
| `/api/state` | GET | Full runtime state snapshot |
