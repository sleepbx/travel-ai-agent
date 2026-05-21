import os
import re
import requests
from dotenv import load_dotenv
from cache_utils import TTLCache
from ai_core.web_search import travel_web_search_json

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_TIMEOUT = int(os.getenv("SERPAPI_TIMEOUT", "6"))
_hotel_cache = TTLCache(ttl_seconds=int(os.getenv("SERPAPI_CACHE_TTL", "21600")))


def _format_inr(amount):
    return f"INR {int(round(amount)):,}"


def _price_value(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        for key in ("extracted_lowest_price", "extracted_price", "lowest_price"):
            parsed = _price_value(value.get(key))
            if parsed:
                return parsed
    match = re.search(r"([0-9][0-9,]{2,})", str(value or ""))
    return int(match.group(1).replace(",", "")) if match else None


def _extract_prices_from_web_results(results):
    prices = []
    price_pattern = re.compile(
        r"(?:INR|Rs\.?|\u20b9)\s*([0-9][0-9,]{2,})|([0-9][0-9,]{2,})\s*(?:INR|Rs\.?|\u20b9)",
        re.I,
    )

    for result in results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        for match in price_pattern.finditer(text):
            raw = match.group(1) or match.group(2)
            try:
                amount = int(raw.replace(",", ""))
            except ValueError:
                continue
            if 700 <= amount <= 150000:
                prices.append(amount)

    return sorted(set(prices))


def _fallback_nightly_range(max_price=None):
    if max_price:
        low = max(int(max_price * 0.9), 900)
        high = max(int(max_price * 1.12), low)
        return low, high
    return 3200, 6200


def estimate_hotels_online(
    city: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "INR",
    max_price: int | None = None,
    reason: str = "",
):
    query = (
        f"{city} hotel price per night estimate {checkin} {checkout} "
        f"{adults} guests {rooms} room {currency}"
    )
    web_context = travel_web_search_json(query, max_results=6)
    results = web_context.get("results") if isinstance(web_context, dict) else []
    prices = _extract_prices_from_web_results(results or [])

    if prices:
        anchor_prices = [price for price in prices if not max_price or price <= int(max_price * 1.45)]
        anchor_prices = anchor_prices or prices
        midpoint = anchor_prices[len(anchor_prices) // 2]
        nightly_low = max(int(midpoint * 0.86), 900)
        nightly_high = int(midpoint * 1.18)
        confidence = "Medium"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = "Estimated from online hotel snippets because live hotel inventory was unavailable. Verify taxes and room rules before booking."
    elif web_context.get("status") == "ok":
        nightly_low, nightly_high = _fallback_nightly_range(max_price=max_price)
        confidence = "Low"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = "Online search returned hotel context but no parseable room rate, so TravelAI used a budget-aligned range."
    else:
        nightly_low, nightly_high = _fallback_nightly_range(max_price=max_price)
        confidence = "Low"
        source = "Offline hotel estimate"
        note = web_context.get("message") or "Live and online hotel estimates were unavailable."

    if reason:
        note = f"{note} Supplier note: {reason}"

    return {
        "status": "estimated",
        "pricing_mode": "online_estimate" if web_context.get("status") == "ok" else "offline_estimate",
        "provider": web_context.get("provider", "estimate"),
        "query": query,
        "hotels": [
            {
                "name": f"Nearest {city.title()} stay estimate",
                "rating": "Estimate",
                "reviews": "",
                "price": f"{_format_inr(nightly_low)} - {_format_inr(nightly_high)}",
                "currency": currency,
                "address": "Well-connected area",
                "image": "",
                "source": source,
                "why": note,
                "estimate_confidence": confidence,
            },
            {
                "name": f"Flexible {city.title()} comfort estimate",
                "rating": "Estimate",
                "reviews": "",
                "price": f"{_format_inr(int(nightly_low * 1.08))} - {_format_inr(int(nightly_high * 1.16))}",
                "currency": currency,
                "address": "Central or transit-friendly area",
                "image": "",
                "source": source,
                "why": "Wider comparison range for better reviews, cancellation terms, or a calmer location.",
                "estimate_confidence": confidence,
            },
        ],
        "web_results": (results or [])[:3],
        "message": note,
    }


def search_hotels_serpapi(
    city: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "INR",
    max_results: int = 5,
    max_price: int | None = None,
):
    """
    Hotel search using SerpAPI Google Hotels Engine.

    city      : "Hyderabad"
    checkin   : "YYYY-MM-DD"
    checkout  : "YYYY-MM-DD"
    """

    cache_key = (city, checkin, checkout, adults, rooms, currency, max_results, max_price)
    cached = _hotel_cache.get(*cache_key)
    if cached:
        return cached

    if not SERPAPI_KEY:
        result = estimate_hotels_online(
            city=city,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            rooms=rooms,
            currency=currency,
            max_price=max_price,
            reason="SERPAPI_KEY missing",
        )
        _hotel_cache.set(result, *cache_key)
        return result

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

    if max_price:
        params["max_price"] = max_price

    try:
        resp = requests.get(url, params=params, timeout=SERPAPI_TIMEOUT)

        if resp.status_code != 200:
            result = estimate_hotels_online(
                city=city,
                checkin=checkin,
                checkout=checkout,
                adults=adults,
                rooms=rooms,
                currency=currency,
                max_price=max_price,
                reason=f"HTTP {resp.status_code}: {resp.text[:160]}",
            )
            _hotel_cache.set(result, *cache_key)
            return result

        data = resp.json()

        # Hotels appear in the "properties" array
        hotels_raw = data.get("properties", [])
        hotels_clean = []

        for h in hotels_raw[: max(max_results, 2)]:
            hotels_clean.append(
                {
                    "name": h.get("name"),
                    "rating": h.get("overall_rating") or h.get("rating"),
                    "reviews": h.get("reviews"), 
                    "price": h.get("rate_per_night") or (h.get("rate") or {}).get("extracted_lowest_price"),
                    "currency": currency,
                    "address": h.get("address"),
                    "image": h.get("thumbnail") or h.get("images", [{}])[0].get("thumbnail"),
                    "source": "SerpAPI Google Hotels",
                }
            )

        if not hotels_clean:
            result = estimate_hotels_online(
                city=city,
                checkin=checkin,
                checkout=checkout,
                adults=adults,
                rooms=rooms,
                currency=currency,
                max_price=max_price,
                reason="SerpAPI returned no hotel options",
            )
            _hotel_cache.set(result, *cache_key)
            return result

        hotels_clean.sort(key=lambda item: _price_value(item.get("price")) or 10**9)
        hotels_clean = hotels_clean[:max_results]

        result = {"hotels": hotels_clean}
        _hotel_cache.set(result, *cache_key)
        return result

    except Exception as e:
        result = estimate_hotels_online(
            city=city,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            rooms=rooms,
            currency=currency,
            max_price=max_price,
            reason=f"Exception calling SerpAPI Hotels API: {e}",
        )
        _hotel_cache.set(result, *cache_key)
        return result
