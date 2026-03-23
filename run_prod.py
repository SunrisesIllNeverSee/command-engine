"""
Production entrypoint — binds to 0.0.0.0 so the server is reachable
inside Docker or on a VPS. For local dev, use run.py (127.0.0.1 only).
"""
from pathlib import Path
import threading

import uvicorn

from app.server import create_app


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    app = create_app(root)
    mcp = app.state.mcp_bridge.build_fastmcp()
    threading.Thread(target=lambda: mcp.run(transport="streamable-http"), daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8300)
