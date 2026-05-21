from datetime import date
from typing import Any

from fastapi import APIRouter, Query

from ai_core.web_search import travel_web_search_json

router = APIRouter(prefix="/trends", tags=["Trends"])

PULSE_IMAGE_POOLS = {
    "festival": [
        "https://images.unsplash.com/photo-1496372412473-e8548ffd82bc?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1603262110263-fb0112e7cc33?auto=format&fit=crop&w=900&q=80",
    ],
    "event": [
        "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=900&q=80",
    ],
    "place": [
        "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=900&q=80",
    ],
    "travel news": [
        "https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
    ],
}


def _image_for(text: str, category: str = "Travel news") -> str:
    category_key = str(category or "Travel news").lower()
    pool = PULSE_IMAGE_POOLS.get(category_key, PULSE_IMAGE_POOLS["travel news"])
    index = sum(ord(char) for char in text) % len(pool)
    return pool[index]


def _category_for(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("festival", "fair", "mela", "utsav", "celebration")):
        return "Festival"
    if any(word in lowered for word in ("concert", "event", "expo", "summit", "show", "match")):
        return "Event"
    if any(word in lowered for word in ("beach", "hill", "temple", "fort", "park", "place", "destination")):
        return "Place"
    return "Travel news"


def _compact_item(item: dict[str, Any], index: int, provider: str) -> dict[str, Any]:
    title = item.get("title") or f"India travel trend {index + 1}"
    snippet = item.get("snippet") or "Live context available from search result."
    link = item.get("link") or ""
    category = _category_for(f"{title} {snippet}")
    return {
        "id": f"{provider.lower()}-{index}",
        "title": title,
        "summary": snippet,
        "link": link,
        "category": category,
        "source": provider,
        "freshness": "Live search result",
        "image": _image_for(title, category),
    }


def _fallback_items(query: str) -> list[dict[str, Any]]:
    base = [
        {
            "title": "Weekend festivals and city events in India",
            "summary": "Connect SerpAPI or Serper to replace this with live event listings, dates, and source links.",
            "category": "Event",
        },
        {
            "title": "Trending short trips from major Indian cities",
            "summary": "Use the query box to search beaches, hills, forts, food walks, concerts, or family events.",
            "category": "Place",
        },
        {
            "title": "Seasonal India travel ideas",
            "summary": "Offline suggestion mode is active. Live search will show current festivals, openings, and travel news.",
            "category": "Travel news",
        },
    ]

    return [
        {
            "id": f"fallback-{index}",
            "title": item["title"],
            "summary": item["summary"],
            "link": "",
            "category": item["category"],
            "source": "Offline fallback",
            "freshness": f"Fallback for query: {query}",
            "image": _image_for(item["title"], item["category"]),
        }
        for index, item in enumerate(base)
    ]


@router.get("/india")
def india_trends(
    q: str | None = Query(default=None, max_length=180),
    limit: int = Query(default=9, ge=3, le=12),
):
    today = date.today().isoformat()
    user_query = (q or "").strip()
    query = (
        user_query
        if user_query
        else (
            "latest trending travel places events festivals concerts exhibitions "
            f"India this week {today}"
        )
    )
    result = travel_web_search_json(query, max_results=limit)
    provider = result.get("provider", "web")
    raw_results = result.get("results") or []
    items = [_compact_item(item, index, provider) for index, item in enumerate(raw_results)]

    if not items:
        items = _fallback_items(query)

    return {
        "query": query,
        "generated_at": today,
        "provider": provider,
        "status": result.get("status", "fallback"),
        "message": result.get("message", "Live India discovery results loaded."),
        "items": items[:limit],
        "suggested_queries": [
            "music festivals in India this weekend",
            "trending hill stations in India right now",
            "food festivals and cultural events India",
            "new tourist attractions in India",
        ],
    }
