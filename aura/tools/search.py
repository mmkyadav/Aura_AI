"""
aura/tools/search.py
--------------------
Google web search tool using SerpAPI.
"""

import json
import logging
import urllib.request
import urllib.parse
from langchain_core.tools import tool
from aura.config import settings
from aura.tools.base import TOOL_REGISTRY, LANGCHAIN_TOOLS

logger = logging.getLogger(__name__)


@tool
def google_search(query: str) -> str:
    """Search Google via SerpAPI for real-time news, current facts, live updates, or real-time event information."""
    if not settings.SERPAPI_API_KEY:
        return "Error: SERPAPI_API_KEY is not configured in settings/environment."
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    url = f"https://serpapi.com/search.json?engine=google&q={urllib.parse.quote(query.strip())}&api_key={settings.SERPAPI_API_KEY}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Aura-Assistant/1.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []

        # Answer box
        ab = data.get("answer_box", {})
        ans = ab.get("answer") or ab.get("title") or ab.get("snippet")
        if ans:
            results.append(f"Answer Box: {ans}")

        # Knowledge graph
        kg = data.get("knowledge_graph", {})
        if kg.get("title") and kg.get("description"):
            results.append(f"Knowledge Graph ({kg['title']}): {kg['description']}")

        # Organic results (top 3)
        organic = data.get("organic_results", [])
        if organic:
            results.append("Top Web Search Results:")
            for i, item in enumerate(organic[:3], 1):
                results.append(f" {i}. {item.get('title')}\n    Snippet: {item.get('snippet')}\n    Link: {item.get('link')}")

        if not results:
            return "No relevant search results found."

        return "\n".join(results)
    except Exception as e:
        logger.error("Search API error for query '%s': %s", query, e)
        return f"Error performing web search: {e}"


# Register in registry
TOOL_REGISTRY["google_search"] = google_search
LANGCHAIN_TOOLS.append(google_search)
