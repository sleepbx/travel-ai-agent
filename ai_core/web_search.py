import os
from typing import Any

import requests
from dotenv import load_dotenv

from cache_utils import TTLCache

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "5"))

_search_cache = TTLCache(ttl_seconds=int(os.getenv("WEB_SEARCH_CACHE_TTL", "21600")))


def _compact_serpapi_results(data: dict[str, Any], max_results: int) -> list[dict[str, str]]:
    results = data.get("organic_results", []) or data.get("results", [])
    compact = []

    for item in results[:max_results]:
        title = item.get("title") or item.get("name") or ""
        snippet = item.get("snippet") or item.get("description") or ""
        link = item.get("link") or item.get("url") or ""

        if title or snippet:
            compact.append({"title": title, "snippet": snippet, "link": link})

    return compact


def _compact_serper_results(data: dict[str, Any], max_results: int) -> list[dict[str, str]]:
    compact = []

    for item in data.get("organic", [])[:max_results]:
        title = item.get("title") or ""
        snippet = item.get("snippet") or ""
        link = item.get("link") or ""

        if title or snippet:
            compact.append({"title": title, "snippet": snippet, "link": link})

    return compact


def _format_results(provider: str, results: list[dict[str, str]]) -> str:
    if not results:
        return "No useful live web results found."

    lines = [f"Live web context from {provider}:"]
    for result in results:
        title = result.get("title", "").strip()
        snippet = result.get("snippet", "").strip()
        link = result.get("link", "").strip()
        lines.append(f"- {title}: {snippet} ({link})")

    return "\n".join(lines)


def travel_web_search_json(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Fast cached web enrichment for travel planning, returned as structured data.

    Priority:
    1. SerpAPI Google Search when SERPAPI_KEY is available.
    2. Serper Google Search when SERPER_API_KEY is available.
    3. A clear no-key message so planning still works offline.
    """
    query = query.strip()
    if not query:
        return {
            "provider": "none",
            "status": "empty_query",
            "results": [],
            "message": "No live web query provided.",
        }

    cached = _search_cache.get("travel_web_search_json", query, max_results)
    if cached:
        return cached

    try:
        if SERPAPI_KEY:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google",
                    "q": query,
                    "hl": "en",
                    "gl": "in",
                    "api_key": SERPAPI_KEY,
                },
                timeout=WEB_SEARCH_TIMEOUT,
            )
            resp.raise_for_status()
            result = {
                "provider": "SerpAPI",
                "status": "ok",
                "results": _compact_serpapi_results(resp.json(), max_results),
            }
            _search_cache.set(result, "travel_web_search_json", query, max_results)
            return result

        if SERPER_API_KEY:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "in", "hl": "en", "num": max_results},
                timeout=WEB_SEARCH_TIMEOUT,
            )
            resp.raise_for_status()
            result = {
                "provider": "Serper",
                "status": "ok",
                "results": _compact_serper_results(resp.json(), max_results),
            }
            _search_cache.set(result, "travel_web_search_json", query, max_results)
            return result

        return {
            "provider": "none",
            "status": "disabled",
            "results": [],
            "message": "Live web search disabled. Set SERPAPI_KEY or SERPER_API_KEY to enable live travel context.",
        }

    except Exception as exc:
        return {
            "provider": "error",
            "status": "unavailable",
            "results": [],
            "message": f"Live web search unavailable: {exc}",
        }


def travel_web_search(query: str, max_results: int = 5) -> str:
    result = travel_web_search_json(query, max_results)
    if result.get("results"):
        return _format_results(result.get("provider", "web"), result["results"])
    return result.get("message", "No useful live web results found.")
