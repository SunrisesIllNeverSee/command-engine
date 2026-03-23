from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .audit import AuditSpine
from .context import ContextAssembler
from .mcp_bridge import MCPBridge
from .models import (
    DeployUpdate,
    GovernanceUpdate,
    MCPReadRequest,
    MCPSendRequest,
    MessageCreate,
    SystemUpdate,
    VaultSelection,
)
from .router import SequenceRouter
from .runtime import RuntimeState
from .store import MessageStore


class ConnectionHub:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_json(event)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


def create_app(root: Path | None = None) -> FastAPI:
    root = root or Path(__file__).resolve().parents[1]
    store = MessageStore(root / "data" / "messages.jsonl")
    audit = AuditSpine(root / "data" / "audit.jsonl")
    runtime = RuntimeState(root=root, store=store, audit=audit)
    router = SequenceRouter()
    assembler = ContextAssembler(router)
    mcp_bridge = MCPBridge(runtime, assembler)
    hub = ConnectionHub()

    app = FastAPI(title="COMMAND Runtime", version="0.1.0")
    app.state.store = store
    app.state.audit = audit
    app.state.runtime = runtime
    app.state.router = router
    app.state.mcp_bridge = mcp_bridge
    app.state.connection_hub = hub
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            o.strip()
            for o in os.environ.get(
                "COMMAND_ENGINE_ALLOWED_ORIGINS",
                "http://localhost:8300,http://127.0.0.1:8300",
            ).split(",")
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    frontend_dir = root / "frontend"
    # Serve sub-directories the original console expects
    if (frontend_dir / "config").is_dir():
        app.mount("/config", StaticFiles(directory=frontend_dir / "config"), name="config")
    if (frontend_dir / "popups").is_dir():
        app.mount("/popups", StaticFiles(directory=frontend_dir / "popups"), name="popups")
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    # Serve favicon and apple-touch-icon at root level
    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(frontend_dir / "favicon.ico")

    @app.get("/apple-touch-icon.png")
    async def apple_touch_icon() -> FileResponse:
        return FileResponse(frontend_dir / "apple-touch-icon.png")

    def current_state_event() -> dict:
        return {"type": "state_snapshot", "payload": runtime.snapshot().model_dump(mode="json")}

    async def emit(event_type: str, payload: dict) -> None:
        await hub.broadcast({"type": event_type, "payload": payload})

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    @app.get("/api/state")
    async def get_state() -> dict:
        return runtime.snapshot().model_dump(mode="json")

    @app.get("/api/audit")
    async def get_audit() -> list[dict]:
        return [event.model_dump(mode="json") for event in audit.recent()]

    @app.get("/api/hash")
    async def get_hash() -> dict:
        snapshot = runtime.snapshot().model_dump(mode="json")
        messages = [message.model_dump(mode="json") for message in store.all()]
        systems = [
            {"name": config.name, "role": runtime.systems.get(config.id).role, "seq": runtime.systems.get(config.id).seq}
            for config in runtime.system_configs
            if config.id in runtime.systems and runtime.systems[config.id].active
        ]
        runtime_hashes = audit.hash_runtime_state(
            mode=runtime.governance.mode,
            posture=runtime.governance.posture,
            role=runtime.governance.role,
            vault_docs=runtime.vault.loaded,
            systems=systems,
        )
        return {
            "state_hash": runtime_hashes["hash_config"],
            "content_hash": audit.hash_payload(messages),
            "onchain_hash": runtime_hashes["hash_onchain"],
            "snapshot_hash": audit.hash_payload(snapshot),
        }

    @app.post("/api/governance/check")
    async def check_governed_action(payload: dict) -> dict:
        return runtime.check_action(payload["action"])

    @app.post("/api/messages")
    async def post_message(message: MessageCreate) -> dict:
        saved = runtime.create_message(message)
        await emit("message_added", saved.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return saved.model_dump(mode="json")

    @app.post("/api/governance")
    async def update_governance(payload: GovernanceUpdate) -> dict:
        updated = runtime.update_governance(payload.model_dump())
        await emit("governance_updated", updated.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    @app.post("/api/systems")
    async def update_system(payload: SystemUpdate) -> dict:
        updated = runtime.update_system(payload.system_id, payload.model_dump(exclude={"system_id"}))
        await emit(
            "systems_updated",
            {
                "systems": {system_id: system.model_dump(mode="json") for system_id, system in runtime.systems.items()},
                "sequence": router.sequence_map(runtime.systems),
            },
        )
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    @app.post("/api/vault/load")
    async def load_context(payload: VaultSelection) -> dict:
        loaded = runtime.load_context(payload.file)
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"loaded_context": loaded}

    @app.post("/api/vault/unload")
    async def unload_context(payload: VaultSelection) -> dict:
        loaded = runtime.unload_context(payload.file)
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"loaded_context": loaded}

    # ── File Upload ──────────────────────────────────────────────
    vault_files_dir = root / "vault"
    vault_files_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/vault/upload")
    async def upload_vault_file(
        file: UploadFile = File(...),
        category: str = Form("general"),
        filename: str = Form(""),
    ) -> dict:
        """Upload a file to the vault. Accepts .md, .txt, .pdf, .json."""
        name = filename or file.filename or "unnamed"
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in ".-_ ").strip()
        if not safe_name:
            safe_name = f"upload-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

        # Save to vault directory
        cat_dir = vault_files_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        dest = cat_dir / safe_name
        content = await file.read()
        dest.write_bytes(content)

        # Validate file is readable (text or binary)
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            pass  # Binary files are accepted as-is

        # Add to vault manifest if not already present
        manifest = runtime.vault.manifest
        if category not in manifest:
            manifest[category] = []
        if safe_name not in manifest[category]:
            manifest[category].append(safe_name)

        # Auto-load the uploaded file
        loaded = runtime.load_context(safe_name)

        audit.log("vault", "file_uploaded", {
            "file": safe_name,
            "category": category,
            "size": len(content),
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })

        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "uploaded": safe_name,
            "category": category,
            "size": len(content),
            "loaded_context": loaded,
        }

    @app.get("/api/vault/files")
    async def list_vault_files() -> dict:
        """List all files in the vault directory."""
        files = {}
        if vault_files_dir.exists():
            for cat_dir in vault_files_dir.iterdir():
                if cat_dir.is_dir():
                    files[cat_dir.name] = [f.name for f in cat_dir.iterdir() if f.is_file()]
        return {"vault_files": files}

    # ── Fork Session ──────────────────────────────────────────────

    @app.post("/api/fork")
    async def fork_session(payload: dict = {}) -> dict:
        """
        Fork the current session into a new branch.
        Snapshots governance, systems, vault, messages, and audit.
        Creates a new data directory with the snapshot as starting state.
        """
        fork_label = payload.get("label", datetime.now(UTC).strftime("fork-%Y%m%d-%H%M%S"))
        fork_dir = root / "forks" / fork_label
        fork_dir.mkdir(parents=True, exist_ok=True)

        # Copy data files
        data_dir = root / "data"
        if data_dir.exists():
            fork_data = fork_dir / "data"
            shutil.copytree(data_dir, fork_data, dirs_exist_ok=True)

        # Write fork metadata
        fork_meta = {
            "forked_at": datetime.now(UTC).isoformat(),
            "label": fork_label,
            "source": "main",
            "governance_at_fork": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
            "systems_at_fork": {sid: s.model_dump(mode="json") for sid, s in runtime.systems.items() if s.active},
            "loaded_context_at_fork": list(runtime.vault.loaded),
            "message_count": len(runtime.store.all()),
            "audit_count": len(audit.recent(100)),
        }
        (fork_dir / "fork_meta.json").write_text(json.dumps(fork_meta, indent=2))

        audit.log("session", "forked", {
            "label": fork_label,
            "path": str(fork_dir),
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "forked": True,
            "label": fork_label,
            "path": str(fork_dir),
            "governance": fork_meta["governance_at_fork"],
            "message_count": fork_meta["message_count"],
        }

    @app.get("/api/forks")
    async def list_forks() -> dict:
        """List all session forks."""
        forks_dir = root / "forks"
        if not forks_dir.exists():
            return {"forks": []}
        forks = []
        for fork_dir in sorted(forks_dir.iterdir()):
            meta_path = fork_dir / "fork_meta.json"
            if meta_path.exists():
                forks.append(json.loads(meta_path.read_text()))
        return {"forks": forks}

    @app.post("/api/deploy")
    async def update_deploy(payload: DeployUpdate) -> dict:
        updated = runtime.update_deploy(payload.model_dump())
        await emit("deploy_updated", updated.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    # ── Message Starring / Favorites ─────────────────────────────

    stars_path = root / "data" / "starred.json"

    def _load_stars() -> list[dict]:
        if stars_path.exists():
            return json.loads(stars_path.read_text())
        return []

    def _save_stars(stars: list[dict]):
        stars_path.parent.mkdir(parents=True, exist_ok=True)
        stars_path.write_text(json.dumps(stars, indent=2))

    @app.post("/api/messages/star")
    async def star_message(payload: dict) -> dict:
        """Star/favorite a message by ID with optional note and tag."""
        msg_id = payload.get("id")
        note = payload.get("note", "")
        tag = payload.get("tag", "gold")
        if msg_id is None:
            return JSONResponse({"error": "id required"}, status_code=400)

        # Find the message
        msg = next((m for m in store.all() if m.id == msg_id), None)
        if not msg:
            return JSONResponse({"error": f"Message {msg_id} not found"}, status_code=404)

        stars = _load_stars()
        # Remove existing star for this ID if present
        stars = [s for s in stars if s.get("id") != msg_id]
        star_entry = {
            "id": msg_id,
            "sender": msg.sender,
            "text": msg.text,
            "timestamp": msg.timestamp.isoformat(),
            "governance": msg.governance.model_dump(mode="json"),
            "vault_loaded": msg.vault_loaded,
            "starred_at": datetime.now(UTC).isoformat(),
            "note": note,
            "tag": tag,
        }
        stars.append(star_entry)
        _save_stars(stars)

        # Save starred message as vault document — atomic context drop
        starred_vault_dir = vault_files_dir / "starred"
        starred_vault_dir.mkdir(parents=True, exist_ok=True)
        doc_name = f"star-{msg_id}-{tag}.md"
        doc_content = (
            f"# Starred Message #{msg_id} [{tag.upper()}]\n\n"
            f"**Sender:** {msg.sender}\n"
            f"**Time:** {msg.timestamp.isoformat()}\n"
            f"**Mode:** {msg.governance.mode}\n"
            f"**Posture:** {msg.governance.posture}\n"
        )
        if note:
            doc_content += f"**Note:** {note}\n"
        doc_content += f"\n---\n\n{msg.text}\n"
        if msg.vault_loaded:
            doc_content += f"\n---\n**Context at time:** {', '.join(msg.vault_loaded)}\n"

        (starred_vault_dir / doc_name).write_text(doc_content)

        # Add to vault manifest
        manifest = runtime.vault.manifest
        if "starred" not in manifest:
            manifest["starred"] = []
        if doc_name not in manifest["starred"]:
            manifest["starred"].append(doc_name)

        # Auto-load into active context
        loaded = runtime.load_context(doc_name)

        audit.log("messages", "starred", {
            "message_id": msg_id,
            "tag": tag,
            "vault_doc": doc_name,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"starred": True, "entry": star_entry, "vault_doc": doc_name, "loaded_context": loaded}

    @app.post("/api/messages/unstar")
    async def unstar_message(payload: dict) -> dict:
        """Remove star from a message."""
        msg_id = payload.get("id")
        stars = _load_stars()
        stars = [s for s in stars if s.get("id") != msg_id]
        _save_stars(stars)
        return {"unstarred": True, "id": msg_id}

    @app.get("/api/messages/starred")
    async def get_starred() -> dict:
        """Get all starred messages."""
        return {"starred": _load_stars()}

    # ── Agent Self-Signup / Provision API ────────────────────────

    import secrets

    @app.post("/api/provision/signup")
    async def agent_signup(payload: dict) -> dict:
        """
        Agent self-registration. The Snowmaker endpoint.
        Agent provides name, optional system preference, and gets a key + governance assignment.
        Respects provision config: require_governance, max_agents, approval_mode, rate_limit.
        """
        agent_name = payload.get("name", "").strip()
        if not agent_name:
            return JSONResponse({"error": "Agent name required"}, status_code=400)

        # Check max agents
        current_agents = [r for r in runtime.registry if r.get("type") == "agent"]
        max_agents = runtime.provision.get("max_agents", 50)
        if len(current_agents) >= max_agents:
            return JSONResponse({"error": f"Max agents ({max_agents}) reached"}, status_code=429)

        # Check if name already exists
        existing = next((r for r in runtime.registry if r.get("name") == agent_name), None)
        if existing:
            return JSONResponse({"error": f"Agent '{agent_name}' already registered", "agent_id": existing.get("agent_id")}, status_code=409)

        # Generate agent key
        key_prefix = f"cmd_ak_{secrets.token_hex(3)}***"
        agent_id = f"agent-{secrets.token_hex(4)}"

        # Determine approval mode
        approval_mode = runtime.provision.get("approval_mode", "auto")
        status = "active" if approval_mode == "auto" else "pending"

        # Auto-assign role and governance
        auto_role = runtime.provision.get("auto_assign_role", "secondary")
        require_gov = runtime.provision.get("require_governance", True)
        gov_mode = runtime.governance.mode if require_gov else "None (Unrestricted)"

        # Build registry entry
        entry = {
            "agent_id": agent_id,
            "name": agent_name,
            "type": "agent",
            "status": status,
            "provisioned": datetime.now(UTC).isoformat(),
            "key_prefix": key_prefix,
            "governance": gov_mode.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "system": payload.get("system", None),
            "assigned_system": payload.get("system", None),
            "role": auto_role,
            "rate_limit": runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
        }

        runtime.registry.append(entry)

        audit.log("provision", "agent_signup", {
            "agent_id": agent_id,
            "name": agent_name,
            "status": status,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "registered": True,
            "agent_id": agent_id,
            "name": agent_name,
            "key_prefix": key_prefix,
            "status": status,
            "governance": gov_mode,
            "role": auto_role,
            "rate_limit": entry["rate_limit"],
        }

    @app.post("/api/provision/key")
    async def issue_agent_key(payload: dict) -> dict:
        """Issue or rotate an API key for a registered agent."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        new_key = f"cmd_ak_{secrets.token_hex(8)}"
        agent["key_prefix"] = new_key[:12] + "***"

        audit.log("provision", "key_rotated", {
            "agent_id": agent_id,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "agent_id": agent_id,
            "key": new_key,
            "key_prefix": agent["key_prefix"],
            "note": "Store this key securely. It will not be shown again.",
        }

    @app.get("/api/provision/status/{agent_id}")
    async def agent_provision_status(agent_id: str) -> dict:
        """Agent checks its own governance status and registration."""
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        return {
            "agent_id": agent_id,
            "name": agent.get("name"),
            "status": agent.get("status"),
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
            "assigned_role": agent.get("role"),
            "rate_limit": agent.get("rate_limit"),
            "loaded_context": runtime.vault.loaded,
        }

    @app.get("/api/provision/registry")
    async def get_registry() -> dict:
        """List all registered agents and systems."""
        return {"registry": runtime.registry}

    @app.post("/api/provision/approve")
    async def approve_agent(payload: dict) -> dict:
        """Approve a pending agent (manual approval mode)."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        agent["status"] = "active"
        audit.log("provision", "agent_approved", {
            "agent_id": agent_id,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"approved": True, "agent_id": agent_id, "status": "active"}

    @app.post("/api/provision/suspend")
    async def suspend_agent(payload: dict) -> dict:
        """Suspend an active agent."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        agent["status"] = "suspended"
        audit.log("provision", "agent_suspended", {"agent_id": agent_id})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"suspended": True, "agent_id": agent_id}

    @app.get("/api/mcp/status")
    async def mcp_status() -> dict:
        return mcp_bridge.chat_status()

    @app.post("/api/mcp/join")
    async def mcp_join(payload: dict) -> dict:
        joined = mcp_bridge.chat_join(payload["name"])
        await emit("presence_updated", {"presence": runtime.presence, "joined": joined})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return joined

    @app.post("/api/mcp/read")
    async def mcp_read(payload: MCPReadRequest) -> dict:
        return mcp_bridge.chat_read(
            payload.name,
            channel=payload.channel,
            since_id=payload.since_id or None,
            limit=payload.limit,
        )

    @app.post("/api/mcp/send")
    async def mcp_send(payload: MCPSendRequest) -> dict:
        saved = mcp_bridge.chat_send(
            payload.sender,
            payload.message,
            channel=payload.channel,
            systems=payload.systems,
        )
        await emit("message_added", saved)
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return saved

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        await websocket.send_json(current_state_event())
        try:
            while True:
                payload = await websocket.receive_json()
                action = payload.get("action")
                if action == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
                elif action == "chat_send":
                    saved = runtime.create_message(MessageCreate.model_validate(payload["payload"]))
                    await emit("message_added", saved.model_dump(mode="json"))
                    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
                elif action == "agent_join":
                    joined = runtime.join_agent(payload["payload"]["name"])
                    await emit("presence_updated", {"presence": runtime.presence, "joined": joined})
                    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
                elif action == "mcp_read":
                    result = mcp_bridge.chat_read(
                        payload["payload"]["name"],
                        channel=payload["payload"].get("channel", "general"),
                        since_id=payload["payload"].get("since_id"),
                        limit=payload["payload"].get("limit", 20),
                    )
                    await websocket.send_json({"type": "mcp_read_result", "payload": result})
                else:
                    await websocket.send_json({"type": "error", "payload": {"message": f"Unknown action: {action}"}})
        except WebSocketDisconnect:
            hub.disconnect(websocket)

    @app.on_event("startup")
    async def startup_event() -> None:
        audit.log("server", "started", {"root": str(root)})
        # Give the event loop a chance before initial broadcast in tests/manual runs.
        await asyncio.sleep(0)

    return app
