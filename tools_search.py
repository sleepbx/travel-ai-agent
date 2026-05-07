from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    """
    Simple web search using DuckDuckGo.
    Returns a short, merged text summary of top results.
    """
    query = query.strip()
    if not query:
        return "No query provided to web search."

    try:
        results_text = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                snippet = r.get("body", "")
                link = r.get("href", "")
                if title or snippet:
                    results_text.append(f"- {title}\n  {snippet}\n  ({link})")

        if not results_text:
            return "No useful web results found."

        # Join a few top results into one block
        return "Top web results:\n" + "\n\n".join(results_text)
    except Exception as e:
        return f"Error performing web search: {e}"
