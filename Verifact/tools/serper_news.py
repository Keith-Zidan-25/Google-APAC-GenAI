import json
import logging
import os

from dotenv import load_dotenv
from typing import Any

import mcp
import httpx
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("verifact.serper_news")

_SERPER_BASE = "https://google.serper.dev"
_TIMEOUT = 60.0


_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

load_dotenv(os.path.join(_HERE, ".env.local"))

def _serper_headers() -> dict[str, str]:
    key = os.environ.get("SERPER_API_KEY", "")
    
    if not key:
        raise EnvironmentError("SERPER_API_KEY environment variable is not set.")
    return {
        "X-API-KEY": key,
        "Content-Type": "application/json",
    }

def _post(endpoint: str, payload: dict) -> dict[str, Any]:
    """Synchronous POST helper (FastMCP runs sync tools in a thread pool)."""
    try:
        resp = httpx.post(
            f"{_SERPER_BASE}{endpoint}",
            headers=_serper_headers(),
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    
    except EnvironmentError as exc:
        return {"error": str(exc)}
    
    except httpx.HTTPStatusError as exc:
        return {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"}
    
    except Exception as exc:
        # logger.exception("Serper request failed")
        return {"error": str(exc)}


# Actual Tools
def _search_news(
    query: str,
    num_results: int = 3,
    time_range: str | None = None,
    country: str = "us",
    language: str = "en",
) -> dict[str, Any]:
    """
    Search Google News via Serper for articles related to a claim.
    Use this to find recent news coverage that supports or contradicts a claim.

    Args:
        query: The search query (e.g. the claim text or key phrases).
        num_results: Number of news results to return (default 3, max 10).
        time_range: Optional recency filter: "qdr:h" (past hour),
                     "qdr:d" (past day), "qdr:w" (past week),
                     "qdr:m" (past month), "qdr:y" (past year).
        country: 2-letter country code for geo-relevance (default "us").
        language: 2-letter language code (default "en").

    Returns:
        A dict with keys:
          articles - list of {title, link, snippet, source, date, imageUrl}
          credits_used - Serper API credits consumed
          error - error message (if any)
    """
    num_results = min(num_results, 10)
    payload: dict[str, Any] = {
        "q": query,
        "num": num_results,
        "gl": country,
        "hl": language,
    }
    if time_range:
        payload["tbs"] = time_range

    raw = _post("/news", payload)
    if "error" in raw:
        return {"articles": [], "credits_used": 0, "error": raw["error"]}

    articles = [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": item.get("source", ""),
            "date": item.get("date", ""),
            "imageUrl": item.get("imageUrl", ""),
        }
        for item in raw.get("news", [])
    ]
    return {
        "articles": articles,
        "credits_used": raw.get("credits", 1),
        "error": None,
    }


def _search_web_serper(
    query: str,
    num_results: int = 3,
    country: str = "us",
    language: str = "en",
) -> dict[str, Any]:
    """
    Perform a general Google web search via Serper.

    Use for broader context when news results alone are insufficient — e.g.
    checking Wikipedia summaries, official government pages, or academic sources.

    Args:
        query:       The search query string.
        num_results: Number of organic results (default 3, max 10).
        country:     2-letter country code (default "us").
        language:    2-letter language code (default "en").

    Returns:
        A dict with keys:
          organic - list of {title, link, snippet, position}
          answer_box - direct answer box text (if Serper returns one)
          knowledge_graph - knowledge graph summary dict (if present)
          related_searches - list of related query strings
          credits_used - Serper API credits consumed
          error - error message (if any)
    """
    num_results = min(num_results, 10)
    payload: dict[str, Any] = {
        "q": query,
        "num": num_results,
        "gl": country,
        "hl": language,
    }
    raw = _post("/search", payload)
    if "error" in raw:
        return {
            "organic": [],
            "answer_box": None,
            "knowledge_graph": None,
            "related_searches": [],
            "credits_used": 0,
            "error": raw["error"],
        }

    organic = [
        {
            "title": r.get("title", ""),
            "link": r.get("link", ""),
            "snippet": r.get("snippet", ""),
            "position": r.get("position", idx + 1),
        }
        for idx, r in enumerate(raw.get("organic", []))
    ]

    answer_box = None
    if "answerBox" in raw:
        ab = raw["answerBox"]
        answer_box = ab.get("answer") or ab.get("snippet") or ab.get("title")

    kg = raw.get("knowledgeGraph")
    kg_summary = None
    if kg:
        kg_summary = {
            "title": kg.get("title"),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "website": kg.get("website"),
        }

    related = [r.get("query", "") for r in raw.get("relatedSearches", [])]

    return {
        "organic": organic,
        "answer_box": answer_box,
        "knowledge_graph": kg_summary,
        "related_searches": related,
        "credits_used": raw.get("credits", 1),
        "error": None,
    }


def _fetch_article_snippet(url: str, max_chars: int = 200) -> dict[str, Any]:
    """
    Fetch the raw text content of a news article URL via Serper's scrape endpoint.

    Use this to retrieve the full body of an article found by search_news so
    the agent can extract specific claims, quotes, or statistics.

    Args:
        url: The article URL to fetch.
        max_chars: Maximum characters of body text to return (default 200).

    Returns:
        A dict with keys:
          url - the requested URL
          title - page title
          text - truncated article body text
          error - error message (if any)
    """
    max_chars = min(max_chars, 5000)
    payload = {"url": url}
    raw = _post("/scrape", payload)
    if "error" in raw:
        return {"url": url, "title": "", "text": "", "error": raw["error"]}

    text = raw.get("text", "")[:max_chars]
    return {
        "url": url,
        "title": raw.get("title", ""),
        "text": text,
        "error": None,
    }

def register_tools(mcp) -> None:
    """Register all Serper tools on the given FastMCP instance."""

    mcp.tool(
        name="search_news",
        description=(
            "Search Google News via Serper for recent articles related to a claim. "
        ),
    )(_search_news)

    mcp.tool(
        name="search_web_serper",
        description=(
            "General Google web search via Serper. Returns organic results"
        ),
    )(_search_web_serper)

    mcp.tool(
        name="fetch_article_snippet",
        description=(
            "Fetch and return the text body of a specific URL (e.g. a news article). "
        ),
    )(_fetch_article_snippet)

    # logger.info("Serper news tools registered.")