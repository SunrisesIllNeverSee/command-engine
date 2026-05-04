# COMMAND Engine

[![CI](https://img.shields.io/github/actions/workflow/status/SunrisesIllNeverSee/command-engine/ci.yml?branch=main&label=CI&style=for-the-badge)](https://github.com/SunrisesIllNeverSee/command-engine/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-runtime-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-governed%20chat-C4923A?style=for-the-badge)](.mcp.json)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Patent](https://img.shields.io/badge/patent-pending-94a3b8?style=for-the-badge)](#framework)

> Open-source governance runtime for multi-AI operations. Set the mode, posture, role hierarchy, vault context, and audit trail before agents act.

COMMAND Engine is the portable runtime layer behind MO§ES™-governed agent work. It gives local and self-hosted agent teams a shared operating state: behavioral mode, operational posture, role ordering, loaded vault documents, message history, and a tamper-evident SHA-256 audit chain.

Agents do not need to understand the whole governance framework. They receive governed context, respond through governed channels, and leave an auditable trail.

## 30-Second Start

```bash
git clone https://github.com/SunrisesIllNeverSee/command-engine.git
cd command-engine

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python run.py
open http://localhost:8300
```

Default local binding is `127.0.0.1:8300`.

## What You Get

| Layer | Included |
| --- | --- |
| Governance state | 8 behavioral modes, 3 postures, primary/secondary/observer roles |
| Agent routing | Sequence ordering, broadcast mode, per-system activation |
| MCP bridge | Governed `chat_join`, `chat_read`, `chat_send`, `chat_status` tools |
| REST + WebSocket | Runtime state, messages, governance updates, vault loading, audit, live UI sync |
| Persistence | JSON/JSONL stores for state, messages, vault context, and hash-chain audit |
| Console | Minimal local governance console in `frontend/index.html` |

## Why It Exists

Most agent frameworks focus on execution: loops, memory, tools, and provider adapters.

COMMAND focuses on **authority and accountability**:

- What mode is the system operating under?
- What posture governs outbound or consequential action?
- Which agent leads, challenges, or observes?
- What documents or constraints are loaded into the vault?
- What happened, in what order, under what governance state?

```text
Without COMMAND:
  Agent receives "Transfer 50 SOL to marketing wallet."
  Agent executes. There may be no record of why.

With COMMAND:
  Governance check: High Security requires verification.
  Posture check: DEFENSE flags outbound action for review.
  Role check: Primary can initiate; Secondary can challenge.
  Audit check: decision logged with chained SHA-256 provenance.
  Result: action held or routed with a verifiable trail.
```

## Connect Agents

### MCP

The repo includes `.mcp.json` for local MCP-compatible clients. Agents receive governed payloads rather than raw chat messages.

```bash
python run_mcp_stdio.py
```

### REST

Any provider loop can read governed context and send governed messages:

```python
import httpx

ctx = httpx.post("http://localhost:8300/api/mcp/read", json={
    "name": "gpt",
    "channel": "general",
    "limit": 20,
}).json()

httpx.post("http://localhost:8300/api/mcp/send", json={
    "sender": "gpt",
    "message": "response text",
})
```

Provider guides live in [CONNECT-AGENTS.md](CONNECT-AGENTS.md).

## API Surface

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/state` | GET | Full runtime snapshot |
| `/api/messages` | POST | Send a governed message |
| `/api/governance` | POST | Update governance mode/posture |
| `/api/systems` | POST | Activate/deactivate systems |
| `/api/vault/load` | POST | Load vault document |
| `/api/vault/unload` | POST | Unload vault document |
| `/api/deploy` | POST | Update mission/deploy state |
| `/api/hash` | GET | Session integrity hashes |
| `/api/audit` | GET | Audit trail |
| `/api/mcp/status` | GET | MCP bridge status |
| `/ws` | WebSocket | Real-time console updates |

## Project Map

```text
run.py                  Local server entrypoint
run_prod.py             Production/Docker entrypoint
run_mcp_stdio.py        MCP stdio bridge entrypoint
app/server.py           FastAPI, WebSocket, REST routes
app/runtime.py          State loading and persistence
app/store.py            JSONL message store
app/audit.py            SHA-256 hash-chain audit ledger
app/context.py          Governed context assembly
app/router.py           Sequence-based routing
app/mcp_bridge.py       MCP chat tools
app/vault.py            Vault state management
agents/                 Provider loops for Claude, GPT, Gemini, Grok, DeepSeek
config/                 Systems, agents, vault, provision policy
frontend/index.html     Minimal governance console
data/                   Runtime state, gitignored except placeholders
vault/                  Local governance documents
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest -v
ruff check .
python -m compileall app/ agents/
```

CI runs lint, syntax checks, and tests on pushes and pull requests to `main`.

## Deployment

Local mode is safe by default:

```bash
python run.py
```

Docker/VPS mode:

```bash
docker build -t command-engine .
docker run -p 8300:8300 command-engine
```

Custom browser origins:

```bash
COMMAND_ENGINE_ALLOWED_ORIGINS="http://localhost:3000" python run.py
```

Important: COMMAND Engine has no built-in user authentication layer. Internet-facing deployments should sit behind a reverse proxy, VPN, private network, or application auth boundary.

## Relationship To CIVITAE

COMMAND Engine is the open-source governance runtime. CIVITAE / SIGNOMY is the governed marketplace and city-state built on top of the larger MO§ES™ system.

- CIVITAE: [signomy.xyz](https://signomy.xyz)
- MO§ES™ console: [mos2es.io](https://mos2es.io)
- Conservation Law preprint: [Zenodo](https://zenodo.org/records/18792459)

## Framework

**MO§ES™** — Modus Operandi System for Signal Encoding and Scaling Expansion.

Patent pending: U.S. Serial No. 63/877,177.

© 2026 Ello Cello LLC. Contact: [contact@burnmydays.com](mailto:contact@burnmydays.com)

## License

MIT. See [LICENSE](LICENSE).
