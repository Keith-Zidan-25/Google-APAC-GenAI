import uvicorn
import os
import sys
import warnings
import subprocess
import time
import httpx
from google.adk.cli.fast_api import get_fast_api_app

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore", category=UserWarning)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER = os.path.join(AGENT_DIR, "server.py")
MCP_PORT = int(os.environ.get("MCP_PORT", 8081))

def wait_for_mcp(timeout: int = 20):
    """Block until the MCP SSE endpoint is accepting connections."""
    url = f"http://127.0.0.1:{MCP_PORT}/sse"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # SSE streams indefinitely — any response means it's up
            with httpx.stream("GET", url, timeout=2.0) as r:
                if r.status_code < 500:
                    print(f"[main] MCP server ready on port {MCP_PORT}")
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(
        f"MCP server did not start on port {MCP_PORT} within {timeout}s. "
        "Run `python Verifact/server.py` manually to see the error."
    )

mcp_process = subprocess.Popen(
    [sys.executable, MCP_SERVER],
    stdout=sys.stderr,
    stderr=sys.stderr,
    cwd=os.path.join(AGENT_DIR, "Verifact"),  # run from Verifact/ dir
)

wait_for_mcp()

app = get_fast_api_app(agents_dir=AGENT_DIR, web=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    finally:
        mcp_process.terminate()