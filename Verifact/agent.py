import dotenv
import os
import sys
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from tools.database import big_query_tools

dotenv.load_dotenv(dotenv_path=os.path.join(_HERE, ".env.local"))

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("API Key not found")

MCP_PORT = int(os.environ.get("MCP_PORT", 8081))

def load_instructions(file_path: str) -> str:
    abs_path = os.path.join(_HERE, file_path)
    if not os.path.exists(abs_path):
        return "Default instructions: Fact-check the user's claim."
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()

agent = Agent(
    name="VeriFact",
    model="gemini-2.5-flash-lite",
    description="Cross-references claims with BigQuery and Search.",
    instruction=load_instructions("fact-checker.md"),
    tools=[
        big_query_tools,
        McpToolset(
            connection_params=SseConnectionParams(
                url=f"http://127.0.0.1:{MCP_PORT}/sse",
            ),
            tool_filter=[
                "health_check",
                "search_news",
                "fetch_article_snippet",
                "google_search",
                "google_search_site",
                "google_fact_check_search",
                "search_web_serper",
            ]
        ),
    ],
)

root_agent = agent