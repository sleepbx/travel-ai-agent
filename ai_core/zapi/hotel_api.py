import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def search_hotels_serpapi(
    city: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "INR",
    max_results: int = 5,
):
    """
    Hotel search using SerpAPI Google Hotels Engine.

    city      : "Hyderabad"
    checkin   : "YYYY-MM-DD"
    checkout  : "YYYY-MM-DD"
    """

    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY missing in .env"}

    url = "https://serpapi.com/search"

    params = {
        # REQUIRED
        "engine": "google_hotels",
        "q": city,
        "check_in_date": checkin,
        "check_out_date": checkout,

        # OPTIONAL
        "adults": adults,
        "rooms": rooms,
        "currency": currency,
        "hl": "en",

        # KEY
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "body": resp.text[:300]}

        data = resp.json()

        # Hotels appear in the "properties" array
        hotels_raw = data.get("properties", [])
        hotels_clean = []

        for h in hotels_raw[:max_results]:
            hotels_clean.append(
                {
                    "name": h.get("name"),
                    "rating": h.get("overall_rating") or h.get("rating"),
                    "reviews": h.get("reviews"), 
                    "price": h.get("rate_per_night") or (h.get("rate") or {}).get("extracted_lowest_price"),
                    "currency": currency,
                    "address": h.get("address"),
                    "image": h.get("thumbnail") or h.get("images", [{}])[0].get("thumbnail"),
                }
            )

        if not hotels_clean:
            return {"error": "No hotels returned", "raw": data}

        return {"hotels": hotels_clean}

    except Exception as e:
        return {"error": f"Exception calling SerpAPI Hotels API: {e}"}
