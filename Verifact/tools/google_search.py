import logging
import os
import sys

from typing import Any
from dotenv import load_dotenv

import httpx
import mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("verifact.google_search")

_CSE_URL = "https://www.googleapis.com/customsearch/v1"
_TIMEOUT = 60.0


_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

load_dotenv(os.path.join(_HERE, ".env.local"))

def _cse_params(extra: dict) -> dict[str, Any]:
    key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CSE_ID", "")
    if not key or not cx:
        raise EnvironmentError(
            "GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables must be set."
        )
    return {"key": key, "cx": cx, **extra}


def _get(params: dict) -> dict[str, Any]:
    try:
        resp = httpx.get(_CSE_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except EnvironmentError as exc:
        return {"error": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {"error": f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"}
    except Exception as exc:  # noqa: BLE001
        # logger.exception("Google CSE request failed")
        return {"error": str(exc)}


def _parse_items(raw: dict) -> list[dict]:
    return [
        {
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "display_link": item.get("displayLink", ""),
            "mime": item.get("mime", ""),
        }
        for item in raw.get("items", [])
    ]


# Actual Tools
def _google_search(
    query: str,
    num_results: int = 3,
    language: str = "en",
    country: str | None = None,
    date_restrict: str | None = None,
    safe: str = "off",
) -> dict[str, Any]:
    """
    Search the web using the Google Custom Search JSON API.

    Use this for authoritative, general-purpose web results — official government
    pages, fact-check databases (e.g. Snopes, PolitiFact), encyclopaedias, etc.

    Args:
        query: The search query (e.g. claim text or keywords).
        num_results: Number of results (1-10, API maximum per request).
        language: Language code for results, e.g. "en", "fr" (default "en").
        country: Optional 2-letter country code to restrict results, e.g. "us", "gb".  Leave None for global results.
        date_restrict: Restrict to recent content.  Format: "d[n]" past n-days, "w[n]" past n-weeks, 
                        "m[n]" past n-months, "y[n]" past n-years.  E.g. "m6" = past 6 months.
        safe: SafeSearch level: "off" (default) or "active".

    Returns:
        A dict with keys:
          results - list of {title, link, snippet, display_link}
          total_results - estimated total Google results (string)
          search_time - seconds the search took
          error - error message (if any)
    """
    num_results = min(max(1, num_results), 10)
    params: dict[str, Any] = {
        "q": query,
        "num": num_results,
        "hl": language,
        "safe": safe,
    }
    if country:
        params["gl"] = country
    if date_restrict:
        params["dateRestrict"] = date_restrict

    raw = _get(_cse_params(params))
    if "error" in raw:
        return {"results": [], "total_results": "0", "search_time": 0, "error": raw["error"]}

    info = raw.get("searchInformation", {})
    return {
        "results": _parse_items(raw),
        "total_results": info.get("totalResults", "0"),
        "search_time": info.get("searchTime", 0),
        "error": None,
    }


def _google_search_site(
    query: str,
    site: str,
    num_results: int = 3,
    date_restrict: str | None = None,
) -> dict[str, Any]:
    """
    Perform a Google Custom Search restricted to a specific domain.

    Use this to search authoritative domains directly, e.g.:
      - "site:reuters.com" for Reuters fact-checks
      - "site:apnews.com"  for AP News
      - "site:politifact.com" for PolitiFact verdicts
      - "site:snopes.com"  for Snopes debunks
      - "site:who.int"     for WHO health claims
      - "site:cdc.gov"     for CDC statements

    Args:
        query:        The search keywords (do NOT include "site:" yourself).
        site:         Domain to restrict to, e.g. "snopes.com".
        num_results:  Number of results (1-10, default 3).
        date_restrict: Optional recency filter (same format as google_search).

    Returns:
        Same structure as `google_search`.
    """
    site_query = f"site:{site} {query}"
    return _google_search(
        query=site_query,
        num_results=num_results,
        date_restrict=date_restrict,
    )


def _google_fact_check_search(
    claim: str,
    num_results: int = 3,
    date_restrict: str | None = None,
) -> dict[str, Any]:
    """
    Search multiple authoritative fact-check sources for a given claim.

    Internally runs a Google Custom Search with an OR-combined site filter
    covering PolitiFact, Snopes, AP Fact Check, Reuters Fact Check, and
    FullFact — returning consolidated results from all sources.

    Args:
        claim:        The claim text to fact-check.
        num_results:  Total results to return (1-10, default 3).
        date_restrict: Optional recency filter (e.g. "y1" = past year).

    Returns:
        Same structure as `google_search`, with an additional `sources` key
        listing the domains that were searched.
    """
    fact_check_sites = [
        "politifact.com",
        "snopes.com",
        "apnews.com",
        "reuters.com",
        "fullfact.org",
        "factcheck.org",
    ]
    site_filter = " OR ".join(f"site:{s}" for s in fact_check_sites)
    combined_query = f"({claim}) ({site_filter})"

    result = _google_search(
        query=combined_query,
        num_results=num_results,
        date_restrict=date_restrict,
    )
    result["sources"] = fact_check_sites
    return result


def register_tools(mcp) -> None:
    """Register all Google Custom Search tools on the given FastMCP instance."""

    mcp.tool(
        name="google_search",
        description=(
            "Search the web via Google Custom Search JSON API. "
        ),
    )(_google_search)

    mcp.tool(
        name="google_search_site",
        description=(
            "Google Custom Search restricted to a single domain "
        ),
    )(_google_search_site)

    mcp.tool(
        name="google_fact_check_search",
        description=(
            "Search PolitiFact, Snopes, AP News, Reuters, FullFact"
        ),
    )(_google_fact_check_search)

    # logger.info("Google Custom Search tools registered.")