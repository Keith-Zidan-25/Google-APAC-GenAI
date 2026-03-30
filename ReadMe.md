# Agent

# Tools
## Server
The single entry point that the ADK agent launches via StdioServerParameters. 
It aggregates tools from three sub-modules:
  - `database.py`    → BigQuery / Bigtable ground-truth lookups
  - `serper_news.py` → Serper.dev news & web search
  - `google_search.py` → Google Custom Search JSON API
 
Run directly:
    `python server.py`
Or via the ADK agent (`agent.py`) which spawns it automatically.
 
Required env vars (put in .env.local one level above this directory):
 - GOOGLE_API_KEY / GEMINI_API_KEY
 - BIGQUERY_PROJECT_ID
 - BIGQUERY_DATASET_ID
 - SERPER_API_KEY
 - GOOGLE_CSE_API_KEY           # Google Custom Search JSON API key
 - GOOGLE_CSE_ID                # Programmable Search Engine CX id

## Serper News API Tools
Exposes three MCP tools:
  - search_news          – search Google News via Serper for claim-related articles
  - search_web_serper    – general Google web search via Serper
  - fetch_article_snippet – fetch & summarise a news article URL

Required env var:
    SERPER_API_KEY  – from https://serper.dev
    
## Google Search API Tools
Exposes two MCP tools:
  - `google_search`        – web search via Google Custom Search JSON API
  - `google_search_site`   – site-restricted search (e.g. site:reuters.com)

Why not the managed Google MCP server?
Google's official managed MCP servers (announced Dec 2025) use remote HTTP/OAuth transport, which is incompatible with the stdio, StdioServerParameters pattern used by this agent.  The Custom Search JSON API achieves the same result & runs fully locally.

Required env vars:

`GOOGLE_CSE_API_KEY`  – API key with Custom Search JSON API enabled
`GOOGLE_CSE_ID`       – Programmable Search Engine ID (the "cx" param)

How to obtain:
  1. Enable "Custom Search JSON API" in Google Cloud Console.
  2. Create credentials → API Key → restrict to Custom Search JSON API.
  3. Go to https://programmablesearchengine.google.com/ → Create engine → enable "Search the entire web" → copy the Search engine ID.

# Agent Reasoning Flow
The agent follows the instruction in agent.py:
1. google_fact_check_search: check if professional fact-checkers have already debunked/verified the claim.
2. search_bigquery_claims/query_ground_truth: query internal ground-truth records.
3. search_news: find recent news articles for or against the claim.
4. google_search/google_search_site: gather broader context.
5. fetch_article_snippet: read full article bodies when snippets are insufficient.
6. Synthesise findings & flag any discrepancies between sources.