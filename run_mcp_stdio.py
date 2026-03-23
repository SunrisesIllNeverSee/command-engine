import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.server import create_app  # noqa: E402

if __name__ == "__main__":
    app = create_app(ROOT)
    mcp = app.state.mcp_bridge.build_fastmcp()
    mcp.run()
