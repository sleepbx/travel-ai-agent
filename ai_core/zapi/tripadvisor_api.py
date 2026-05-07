# zapi/tripadvisor_api.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def search_tripadvisor(
    city: str,
    interests: str | None = None,
    max_results: int = 10,
    currency: str = "INR",
):
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY missing in .env"}

    query = f"{city} {interests}" if interests else city

    url = "https://serpapi.com/search"

    params = {
        "engine": "tripadvisor",
        "q": query,
        "currency": currency,
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

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
            }
        )

    return {"places": places}


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
                }
            )

        if len(restaurants) >= max_items:
            break

    return restaurants
