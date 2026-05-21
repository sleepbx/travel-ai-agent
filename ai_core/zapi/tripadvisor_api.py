# zapi/tripadvisor_api.py

import os
import requests
from dotenv import load_dotenv
from cache_utils import TTLCache

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_TIMEOUT = int(os.getenv("SERPAPI_TIMEOUT", "6"))
_tripadvisor_cache = TTLCache(ttl_seconds=int(os.getenv("SERPAPI_CACHE_TTL", "21600")))


def search_tripadvisor(
    city: str,
    interests: str | None = None,
    max_results: int = 10,
    currency: str = "INR",
):
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY missing in .env"}

    query = f"{city} {interests}" if interests else city
    cache_key = (query, max_results, currency)
    cached = _tripadvisor_cache.get(*cache_key)
    if cached:
        return cached

    url = "https://serpapi.com/search"

    params = {
        "engine": "tripadvisor",
        "q": query,
        "currency": currency,
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=SERPAPI_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"error": f"Tripadvisor search unavailable: {exc}"}

    results = data.get("organic_results", []) or data.get("results", [])

    places = []
    for r in results[:max_results]:
        places.append(
            {
                "title": r.get("title"),
                "category": r.get("category") or r.get("type"),
                "rating": r.get("rating"),
                "reviews": r.get("reviews"),
                "price_level": r.get("price_level"),
                "address": r.get("address"),
                "snippet": r.get("snippet"),
                "link": r.get("link"),
                "image": r.get("thumbnail") or r.get("image") or r.get("photo"),
            }
        )

    result = {"places": places}
    _tripadvisor_cache.set(result, *cache_key)
    return result


# ---------------- RESTAURANT FILTER ----------------
def extract_restaurants(tripadvisor_data, max_items=6):
    """
    Returns only REAL restaurant names for LLM grounding.
    """
    restaurants = []

    for p in tripadvisor_data.get("places", []):
        category = (p.get("category") or "").lower()
        title = p.get("title")

        if not title:
            continue

        if "restaurant" in category or "food" in category:
            restaurants.append(
                {
                    "name": title,
                    "rating": p.get("rating"),
                    "price_level": p.get("price_level"),
                    "address": p.get("address"),
                    "image": p.get("image"),
                }
            )

        if len(restaurants) >= max_items:
            break

    return restaurants


def extract_attractions(tripadvisor_data, max_items=8):
    """
    Returns only REAL attraction/place titles for grounding.
    """
    attractions = []
    for p in (tripadvisor_data or {}).get("places", []):
        category = (p.get("category") or "").lower()
        title = p.get("title")
        if not title:
            continue
        # Exclude food + stays.
        if "restaurant" in category or "food" in category:
            continue
        if "hotel" in category or "lodging" in category:
            continue
        attractions.append(
            {
                "name": title,
                "category": p.get("category"),
                "rating": p.get("rating"),
                "address": p.get("address"),
                "snippet": p.get("snippet"),
                "link": p.get("link"),
                "image": p.get("image"),
            }
        )
        if len(attractions) >= max_items:
            break
    return attractions
