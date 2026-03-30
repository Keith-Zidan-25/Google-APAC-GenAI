import logging
import os
import sys
import warnings
from dotenv import load_dotenv

os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore", category=UserWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

load_dotenv(os.path.join(_HERE, ".env.local"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("verifact.server")

from mcp.server.fastmcp import FastMCP
from tools.serper_news import register_tools as register_serper_tools
from tools.google_search import register_tools as register_google_tools

MCP_PORT = int(os.environ.get("MCP_PORT", 8081))

# Set host and port on the constructor — works across all FastMCP versions
mcp = FastMCP(
    name="verifact-server",
    host="0.0.0.0",
    port=MCP_PORT,
)

register_serper_tools(mcp)
register_google_tools(mcp)

@mcp.tool(
    name="health_check",
    description="Returns server status and a list of configured data sources.",
)
def health_check() -> dict:
    return {
        "status": "ok",
        "server": "verifact-server",
        "integrations": {
            "serper": bool(os.getenv("SERPER_API_KEY")),
            "google_cse": bool(
                os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_ID")
            ),
        },
    }

if __name__ == "__main__":
    mcp.run(transport="sse")