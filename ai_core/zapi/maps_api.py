import os
import requests
from dotenv import load_dotenv
from cache_utils import TTLCache

load_dotenv()

SERPAPI_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("SERPAPI_KEY")
SERPAPI_TIMEOUT = int(os.getenv("SERPAPI_TIMEOUT", "6"))
_places_cache = TTLCache(ttl_seconds=int(os.getenv("SERPAPI_CACHE_TTL", "21600")))


def search_google_places(city: str, query_type: str, max_results: int = 10):
    query = f"{city} {query_type}".strip()
    cache_key = (query.lower(), max_results)
    cached = _places_cache.get(*cache_key)
    if cached:
        return cached

    if not SERPAPI_KEY:
        return {"error": "GOOGLE_MAPS_API_KEY or SERPAPI_KEY missing", "places": []}

    params = {
        "engine": "google_maps",
        "type": "search",
        "q": query,
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=SERPAPI_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"error": f"Google places search unavailable: {exc}", "places": []}

    raw_places = data.get("local_results") or data.get("places_results") or []
    places = []
    for item in raw_places[:max_results]:
        if not isinstance(item, dict):
            continue
        places.append(
            {
                "name": item.get("title"),
                "address": item.get("address"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews"),
                "category": item.get("type"),
                "price_level": item.get("price"),
                "source": "SerpAPI Google Maps",
            }
        )

    result = {"provider": "SerpAPI Google Maps", "places": places}
    _places_cache.set(result, *cache_key)
    return result


def extract_google_restaurants(places_data, max_items: int = 8):
    restaurants = []
    for item in (places_data or {}).get("places", []):
        name = item.get("name")
        if not name:
            continue
        restaurants.append(
            {
                "name": name,
                "address": item.get("address"),
                "rating": item.get("rating"),
                "price_level": item.get("price_level") or item.get("category") or "local",
                "source": item.get("source"),
            }
        )
        if len(restaurants) >= max_items:
            break
    return restaurants


def extract_google_attractions(places_data, max_items: int = 10):
    attractions = []
    for item in (places_data or {}).get("places", []):
        name = item.get("name")
        if not name:
            continue
        attractions.append(
            {
                "name": name,
                "address": item.get("address"),
                "category": item.get("category") or "attraction",
                "rating": item.get("rating"),
                "source": item.get("source"),
            }
        )
        if len(attractions) >= max_items:
            break
    return attractions


def get_distance(origin: str, destination: str):
    """
    Returns driving distance and duration between two places using SerpAPI Google Maps.
    Example: origin="Hyderabad airport", destination="Charminar"
    """

    url = "https://serpapi.com/search"

    params = {
        "engine": "google_maps",
        "type": "distance_matrix",
        "origins": origin,
        "destinations": destination,
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=SERPAPI_TIMEOUT)
        data = resp.json()

        row = (data.get("distance_matrix", {})
                    .get("rows", [{}])[0]
                    .get("elements", [{}])[0])

        distance = row.get("distance", {}).get("text")
        duration = row.get("duration", {}).get("text")

        return {
            "origin": origin,
            "destination": destination,
            "distance": distance,
            "duration": duration,
        }

    except:
        return {"error": "Could not fetch distance"}
