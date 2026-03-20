# COMMAND Engine

> The governance runtime for multi-AI operations. Open source. Patent-pending framework.

Every AI agent operating today executes without constraints. No behavioral rules. No audit trail. No chain of command. COMMAND Engine changes that.

Set a governance mode. Set a posture. Assign roles. Every action is checked, every response is audited, every decision is hash-chained. The agents don't need to understand the framework — they just carry it.

**Built on MO§ES™** — Modus Operandi System for Signal Encoding and Scaling Expansion.

---

## 30-Second Start

```bash
# Clone
git clone https://github.com/SunrisesIllNeverSee/command-engine.git
cd command-engine

# Install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run
.venv/bin/python run.py

# Open
open http://localhost:8300
```

That's it. Governance is active.

---

## What You Get

### Governance Engine
- **8 behavioral modes** — High Security, High Integrity, Creative, Research, Problem Solving, Self Growth, IDK, Unrestricted
- **3 operational postures** — SCOUT (read-only), DEFENSE (confirm outbound), OFFENSE (execute)
- **Role hierarchy** — Primary leads, Secondary challenges, Observer oversees
- **SHA-256 audit chain** — every action logged, tamper-evident, hash-chained

### Multi-AI Operations
- **6 pre-configured systems** — Claude, GPT, Gemini, Grok, DeepSeek, Le Chat
- **Sequence ordering** — Primary responds first, then Secondary, then Observer
- **Broadcast mode** — signal all active systems simultaneously
- **Per-system role assignment** — each system gets a role and sequence position

### MCP Bridge
- **4 governed tools** — `chat_join`, `chat_read`, `chat_send`, `chat_status`
- **Governed payloads** — agents don't get raw messages, they get constitutional context
- **Cursor tracking** — each agent reads only new messages, minimizing token costs
- **Any MCP-compatible agent** connects automatically

### Persistence
- **JSONL message store** — survives restarts
- **Atomic state writes** — governance, systems, vault, deploy all persisted
- **Audit ledger** — append-only, never modified, hash-chained

### REST API
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/state` | GET | Full runtime snapshot |
| `/api/messages` | POST | Send a governed message |
| `/api/governance` | POST | Update governance mode/posture |
| `/api/systems` | POST | Activate/deactivate systems |
| `/api/vault/load` | POST | Load vault document |
| `/api/vault/unload` | POST | Unload vault document |
| `/api/deploy` | POST | Update deploy mission |
| `/api/hash` | GET | Session integrity hashes |
| `/api/audit` | GET | Audit trail |
| `/api/mcp/status` | GET | MCP bridge status |
| `/ws` | WebSocket | Real-time updates |

---

## Connect an AI Agent

### Via MCP (Claude Code, Codex, Gemini CLI)
Already configured in `.mcp.json`. Agents get governed payloads automatically.

### Via REST API (any provider)
```python
import httpx

# Read governed context
ctx = httpx.post("http://localhost:8300/api/mcp/read", json={
    "name": "gpt", "channel": "general", "limit": 20
}).json()

# ctx includes: governance mode, posture, role, vault docs, messages
# Build your provider prompt from this governed context
# Send response back:
httpx.post("http://localhost:8300/api/mcp/send", json={
    "sender": "gpt", "message": "response text"
})
```

See [CONNECT-AGENTS.md](CONNECT-AGENTS.md) for full provider setup guides (OpenAI, Anthropic, Google, xAI, DeepSeek).

---

## Project Structure

```
command-engine/
├── run.py                 Entry point — starts server on port 8300
├── run_mcp_stdio.py       MCP bridge entry point
├── requirements.txt       3 dependencies: fastapi, uvicorn, mcp
├── app/
│   ├── server.py          FastAPI + WebSocket + REST endpoints
│   ├── models.py          Pydantic models (governance, systems, messages, deploy)
│   ├── runtime.py         State management + persistence
│   ├── store.py           JSONL message persistence
│   ├── audit.py           SHA-256 hash chain audit ledger
│   ├── context.py         Governed context assembly (the IP)
│   ├── router.py          Sequence-based routing
│   ├── mcp_bridge.py      MCP tools (chat_join/read/send/status)
│   ├── vault.py           Vault state management
│   └── moses_core/        Governance enforcement core
├── config/
│   ├── systems.json       AI systems roster
│   ├── agents.json        Agent definitions
│   ├── vault.json         Vault document manifest
│   └── provision.json     Provision policy + registry
├── agents/
│   ├── base_agent.py      Shared agent loop + governed prompt builder
│   ├── gpt_agent.py       OpenAI GPT agent
│   ├── claude_agent.py    Anthropic Claude API agent
│   ├── gemini_agent.py    Google Gemini agent
│   ├── grok_agent.py      xAI Grok agent
│   └── deepseek_agent.py  DeepSeek agent
├── frontend/
│   └── index.html         Minimal governance console
├── data/                  Runtime state (auto-created, gitignored)
└── vault/                 Governance documents
```

---

## What Makes This Different

Other agent frameworks give you execution: loops, memory, tool calling.

COMMAND Engine gives you **governance**: what agents CAN and CANNOT do, who responds first, what context they operate under, and a cryptographic proof of every decision.

```
Without COMMAND:
  Agent receives "Transfer 50 SOL to marketing wallet."
  Agent transfers 50 SOL. Done. No record of why.

With COMMAND:
  → Governance check: High Security mode requires verification
  → Posture check: DEFENSE posture flags outbound for review
  → Role check: Primary can initiate — Secondary validation required
  → Audit: Decision logged with SHA-256 hash, governance state preserved
  → Result: Transfer held pending review. Full tamper-evident trail.
```

---

## The Full COMMAND Console

This open-source engine powers the governance runtime. For the full operator cockpit — seat registry, wave cascade pricing, themed UI, deploy missions, agent provision, multi-channel conversations, session forking, and more — see the commercial product:

**[COMMAND · powered by MO§ES™](https://mos2es.io)**

---

## Framework

**MO§ES™** — Modus Operandi System for Signal Encoding and Scaling Expansion

- Patent Pending: Serial No. 63/877,177
- Preprint: [Zenodo](https://zenodo.org/records/18792459)
- Live Console: [mos2es.io](https://mos2es.io)

© 2026 Ello Cello LLC | [contact@burnmydays.com](mailto:contact@burnmydays.com)

## License

MIT — see [LICENSE](LICENSE)
