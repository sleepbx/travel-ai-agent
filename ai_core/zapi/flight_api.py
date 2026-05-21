import os
import re
import requests
from dotenv import load_dotenv
from cache_utils import TTLCache
from ai_core.web_search import travel_web_search_json

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_TIMEOUT = int(os.getenv("SERPAPI_TIMEOUT", "6"))
_flight_cache = TTLCache(ttl_seconds=int(os.getenv("SERPAPI_CACHE_TTL", "21600")))


def _format_inr(amount: int | float | None) -> str:
    if amount is None:
        return "INR estimate pending"
    return f"INR {int(round(amount)):,}"


def _cabin_factor(cabin_class: str) -> float:
    cabin = str(cabin_class or "economy").lower()
    if "business" in cabin or "luxury" in cabin:
        return 2.7
    if "first" in cabin:
        return 3.4
    if "premium" in cabin or "comfort" in cabin:
        return 1.45
    return 1.0


def _fallback_price_range(cabin_class: str, max_price: int | None = None) -> tuple[int, int]:
    factor = _cabin_factor(cabin_class)
    low = int(4200 * factor)
    high = int(7800 * factor)

    if max_price:
        low = min(low, max(int(max_price * 0.92), 1))
        high = max(low, int(max_price * 1.08))

    return low, high


def _extract_prices_from_web_results(results: list[dict]) -> list[int]:
    prices: list[int] = []
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
            if 500 <= amount <= 500000:
                prices.append(amount)

    return sorted(set(prices))


def _build_estimate_options(
    origin_airport: str,
    destination_airport: str,
    depart_date: str,
    return_date: str,
    passengers: int,
    cabin_class: str,
    price_low: int,
    price_high: int,
    source: str,
    booking_note: str,
    confidence: str,
):
    route = f"{origin_airport} to {destination_airport}"
    total_low = price_low * max(passengers, 1)
    total_high = price_high * max(passengers, 1)
    return [
        {
            "airline": "Nearest fare estimate",
            "flight_number": "",
            "from": origin_airport,
            "to": destination_airport,
            "departure": f"Flexible on {depart_date}",
            "arrival": f"Return {return_date}",
            "duration": "Check live schedule",
            "price": f"{_format_inr(price_low)} - {_format_inr(price_high)}",
            "price_per_person": f"{_format_inr(price_low)} - {_format_inr(price_high)}",
            "total_price": f"{_format_inr(total_low)} - {_format_inr(total_high)}",
            "passengers": passengers,
            "cabin_class": cabin_class,
            "pricing_unit": "per_person",
            "route": route,
            "booking_note": booking_note,
            "source": source,
            "estimate_confidence": confidence,
        },
        {
            "airline": "Flexible timing estimate",
            "flight_number": "",
            "from": origin_airport,
            "to": destination_airport,
            "departure": "Early morning or late evening",
            "arrival": "Flexible",
            "duration": "Check live schedule",
            "price": f"{_format_inr(int(price_low * 1.08))} - {_format_inr(int(price_high * 1.16))}",
            "price_per_person": f"{_format_inr(int(price_low * 1.08))} - {_format_inr(int(price_high * 1.16))}",
            "total_price": f"{_format_inr(int(price_low * 1.08) * max(passengers, 1))} - {_format_inr(int(price_high * 1.16) * max(passengers, 1))}",
            "passengers": passengers,
            "cabin_class": cabin_class,
            "pricing_unit": "per_person",
            "route": route,
            "booking_note": "Use this wider comparison range if the first estimate is sold out or has poor timings.",
            "source": source,
            "estimate_confidence": confidence,
        },
    ]


def estimate_flights_online(
    origin_airport: str,
    destination_airport: str,
    depart_date: str,
    return_date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    currency: str = "INR",
    max_price: int | None = None,
    reason: str = "",
):
    """
    Cached online fallback for flight pricing.

    It uses search snippets as an estimate source when Google Flights supplier data
    is unavailable. Returned prices are always labeled as estimates.
    """
    query = (
        f"{origin_airport} to {destination_airport} round trip flight fare estimate "
        f"{depart_date} {return_date} {passengers} passenger {cabin_class} {currency}"
    )
    web_context = travel_web_search_json(query, max_results=6)
    results = web_context.get("results") if isinstance(web_context, dict) else []

    prices = _extract_prices_from_web_results(results or [])
    if prices:
        anchor_prices = [price for price in prices if not max_price or price <= int(max_price * 1.35)]
        anchor_prices = anchor_prices or prices
        midpoint = anchor_prices[len(anchor_prices) // 2]
        price_low = max(int(midpoint * 0.88), 1)
        price_high = int(midpoint * 1.18)
        confidence = "Medium"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = (
            "Estimated from online fare snippets because live Google Flights pricing was unavailable. "
            "Verify exact fare and baggage rules before payment."
        )
    elif web_context.get("status") == "ok":
        price_low, price_high = _fallback_price_range(cabin_class, max_price=max_price)
        confidence = "Low"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = (
            "Online search returned route context but no parseable fare in snippets, so TravelAI used a budget-aligned range."
        )
    else:
        price_low, price_high = _fallback_price_range(cabin_class, max_price=max_price)
        confidence = "Low"
        source = "Offline fare estimate"
        note = web_context.get("message") or "Live and online flight estimates were unavailable."

    if reason:
        note = f"{note} Supplier note: {reason}"

    return {
        "status": "estimated",
        "pricing_mode": "online_estimate" if web_context.get("status") == "ok" else "offline_estimate",
        "provider": web_context.get("provider", "estimate"),
        "query": query,
        "flights": _build_estimate_options(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            depart_date=depart_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            price_low=price_low,
            price_high=price_high,
            source=source,
            booking_note=note,
            confidence=confidence,
        ),
        "web_results": (results or [])[:3],
        "message": note,
    }


def search_flights_serpapi(
    origin_airport: str,
    destination_airport: str,
    depart_date: str,
    return_date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    currency: str = "INR",
    max_price: int | None = None,
    max_results: int = 8,
):
    cache_key = (
        origin_airport,
        destination_airport,
        depart_date,
        return_date,
        passengers,
        cabin_class,
        currency,
        max_price,
        max_results,
    )
    cached = _flight_cache.get(*cache_key)
    if cached:
        return cached

    if not SERPAPI_KEY:
        result = estimate_flights_online(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            depart_date=depart_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            currency=currency,
            max_price=max_price,
            reason="SERPAPI_KEY missing",
        )
        _flight_cache.set(result, *cache_key)
        return result

    params = {
        "engine": "google_flights",
        "departure_id": origin_airport,
        "arrival_id": destination_airport,
        "outbound_date": depart_date,
        "return_date": return_date,
        # Query one adult so the resulting fare is treated consistently as a
        # per-person rate. The trip total is calculated separately.
        "adults": 1,
        "currency": currency,
        "api_key": SERPAPI_KEY,
    }

    travel_class_map = {
        "economy": 1,
        "premium_economy": 2,
        "premium": 2,
        "comfort": 2,
        "business": 3,
        "luxury": 3,
        "first": 4,
    }
    travel_class = travel_class_map.get(str(cabin_class or "economy").lower())
    if travel_class:
        params["travel_class"] = travel_class
    if max_price:
        params["max_price"] = max_price

    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=SERPAPI_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        result = estimate_flights_online(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            depart_date=depart_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            currency=currency,
            max_price=max_price,
            reason=f"Flight search unavailable: {exc}",
        )
        _flight_cache.set(result, *cache_key)
        return result

    flights_raw = (data.get("best_flights", []) or []) + (data.get("other_flights", []) or [])

    flights = []
    for f in flights_raw[: max(max_results, 2)]:
        legs = f.get("flights") or []
        if not legs:
            continue
        leg = legs[0]
        flights.append({
            "airline": leg.get("airline"),
            "flight_number": leg.get("flight_number"),
            "from": leg.get("departure_airport", {}).get("id"),
            "to": leg.get("arrival_airport", {}).get("id"),
            "departure": leg.get("departure_airport", {}).get("time"),
            "arrival": leg.get("arrival_airport", {}).get("time"),
            "duration_min": leg.get("duration"),
            "price": f.get("price"),
            "price_per_person": f.get("price"),
            "total_price": (f.get("price") or 0) * max(passengers, 1) if isinstance(f.get("price"), (int, float)) else None,
            "passengers": passengers,
            "pricing_unit": "per_person",
            "source": "SerpAPI Google Flights",
        })

    if not flights:
        result = estimate_flights_online(
            origin_airport=origin_airport,
            destination_airport=destination_airport,
            depart_date=depart_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            currency=currency,
            max_price=max_price,
            reason="SerpAPI returned no priced flight options",
        )
        _flight_cache.set(result, *cache_key)
        return result

    flights.sort(key=lambda item: item.get("price") or 10**9)
    result = {
        "status": "ok",
        "pricing_mode": "live",
        "provider": "SerpAPI",
        "flights": flights[:max_results],
    }
    _flight_cache.set(result, *cache_key)
    return result


