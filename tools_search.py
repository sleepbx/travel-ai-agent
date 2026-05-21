from ai_core.web_search import travel_web_search


def web_search(query: str, max_results: int = 5) -> str:
    """
    Cached live travel search.

    Uses SerpAPI when SERPAPI_KEY is set, then Serper when SERPER_API_KEY is set.
    The function returns a compact text block that is safe to pass into prompts.
    """
    return travel_web_search(query=query, max_results=max_results)
