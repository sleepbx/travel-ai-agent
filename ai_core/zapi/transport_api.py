import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

from cache_utils import TTLCache
from ai_core.web_search import travel_web_search_json

load_dotenv()

INDIAN_RAIL_API_KEY = os.getenv("INDIAN_RAIL_API_KEY")
TRANSPORT_API_TIMEOUT = int(os.getenv("TRANSPORT_API_TIMEOUT", "6"))
_transport_cache = TTLCache(ttl_seconds=int(os.getenv("TRANSPORT_CACHE_TTL", "21600")))


CITY_TO_STATION = {
    "agra": "AGC",
    "ahmedabad": "ADI",
    "amritsar": "ASR",
    "bangalore": "SBC",
    "bengaluru": "SBC",
    "bhopal": "BPL",
    "bhubaneswar": "BBS",
    "chandigarh": "CDG",
    "chennai": "MAS",
    "coimbatore": "CBE",
    "delhi": "NDLS",
    "goa": "MAO",
    "guwahati": "GHY",
    "hyderabad": "HYB",
    "indore": "INDB",
    "jaipur": "JP",
    "jodhpur": "JU",
    "kochi": "ERS",
    "kolkata": "HWH",
    "lucknow": "LKO",
    "madurai": "MDU",
    "mangalore": "MAQ",
    "mumbai": "CSMT",
    "mysore": "MYS",
    "nagpur": "NGP",
    "patna": "PNBE",
    "pune": "PUNE",
    "surat": "ST",
    "udaipur": "UDZ",
    "varanasi": "BSB",
    "visakhapatnam": "VSKP",
}


def _format_inr(amount: int | float | None) -> str:
    if amount is None:
        return "INR estimate pending"
    return f"INR {int(round(amount)):,}"


def _clean_city(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _station_code(city: str) -> str:
    return CITY_TO_STATION.get(_clean_city(city), "")


def _extract_prices(results: list[dict[str, Any]], low_limit: int, high_limit: int) -> list[int]:
    prices: list[int] = []
    pattern = re.compile(
        r"(?:INR|Rs\.?|\u20b9)\s*([0-9][0-9,]{2,})|([0-9][0-9,]{2,})\s*(?:INR|Rs\.?|\u20b9)",
        re.I,
    )

    for result in results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        for match in pattern.finditer(text):
            raw = match.group(1) or match.group(2)
            try:
                amount = int(raw.replace(",", ""))
            except ValueError:
                continue
            if low_limit <= amount <= high_limit:
                prices.append(amount)

    return sorted(set(prices))


def _extract_duration(results: list[dict[str, Any]], fallback: str) -> str:
    pattern = re.compile(
        r"([0-9]{1,2})\s*(?:h|hr|hrs|hour|hours)(?:\s*([0-9]{1,2})\s*(?:m|min|mins|minutes))?",
        re.I,
    )
    for result in results:
        text = f"{result.get('title', '')} {result.get('snippet', '')}"
        match = pattern.search(text)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2) or 0)
            return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return fallback


def _fallback_range(mode: str, max_price: int | None = None) -> tuple[int, int]:
    if max_price:
        low = max(int(max_price * 0.82), 250)
        high = max(int(max_price * 1.12), low)
        return low, high

    if mode == "train":
        return 550, 1900
    return 650, 2200


def _total_label(low: int, high: int, passengers: int) -> str:
    if low == high:
        return _format_inr(low * passengers)
    return f"{_format_inr(low * passengers)} - {_format_inr(high * passengers)}"


def _build_options(
    mode: str,
    origin_city: str,
    destination_city: str,
    depart_date: str,
    passengers: int,
    price_low: int,
    price_high: int,
    duration: str,
    source: str,
    note: str,
    confidence: str,
    provider: str,
    raw_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    label = "Train" if mode == "train" else "Bus"
    route = f"{origin_city.title()} to {destination_city.title()}"
    return {
        "status": "estimated",
        "pricing_mode": "online_estimate" if provider not in {"none", "error", "estimate"} else "offline_estimate",
        "provider": provider,
        "mode": mode,
        "options": [
            {
                "mode": mode,
                "operator": f"Cheapest {label.lower()} watch",
                "service_name": f"{label} fare estimate",
                "route": route,
                "departure": f"Flexible on {depart_date}",
                "arrival": "Check live timetable",
                "duration": duration,
                "price_per_person": f"{_format_inr(price_low)} - {_format_inr(price_high)}",
                "total_price": _total_label(price_low, price_high, passengers),
                "passengers": passengers,
                "booking_note": note,
                "source": source,
                "estimate_confidence": confidence,
            },
            {
                "mode": mode,
                "operator": f"Flexible {label.lower()} timing",
                "service_name": f"{label} comparison estimate",
                "route": route,
                "departure": "Late evening or early morning",
                "arrival": "Check live timetable",
                "duration": duration,
                "price_per_person": f"{_format_inr(int(price_low * 1.08))} - {_format_inr(int(price_high * 1.16))}",
                "total_price": _total_label(int(price_low * 1.08), int(price_high * 1.16), passengers),
                "passengers": passengers,
                "booking_note": "Use this as the backup range if the cheapest timing is sold out or inconvenient.",
                "source": source,
                "estimate_confidence": confidence,
            },
        ],
        "web_results": (raw_results or [])[:3],
        "message": note,
    }


def _search_ground_estimate(
    mode: str,
    origin_city: str,
    destination_city: str,
    depart_date: str,
    passengers: int,
    currency: str,
    max_price: int | None,
    reason: str = "",
) -> dict[str, Any]:
    query = (
        f"cheapest {mode} fare {origin_city} to {destination_city} "
        f"{depart_date} duration {currency} per person"
    )
    web_context = travel_web_search_json(query, max_results=6)
    results = web_context.get("results") if isinstance(web_context, dict) else []
    prices = _extract_prices(results or [], 120, 30000)

    if prices:
        anchor_prices = [price for price in prices if not max_price or price <= int(max_price * 1.45)]
        anchor_prices = anchor_prices or prices
        midpoint = anchor_prices[len(anchor_prices) // 2]
        price_low = max(int(midpoint * 0.82), 120)
        price_high = int(midpoint * 1.18)
        confidence = "Medium"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = (
            f"Estimated from online {mode} fare snippets. Verify timetable, seat class, "
            "taxes, and cancellation rules before booking."
        )
    elif web_context.get("status") == "ok":
        price_low, price_high = _fallback_range(mode, max_price=max_price)
        confidence = "Low"
        source = f"{web_context.get('provider', 'web')} online estimate"
        note = (
            f"Online search returned {mode} context but no parseable fare, so TravelAI used a budget-aligned range."
        )
    else:
        price_low, price_high = _fallback_range(mode, max_price=max_price)
        confidence = "Low"
        source = f"Offline {mode} estimate"
        note = web_context.get("message") or f"Live and online {mode} estimates were unavailable."

    if reason:
        note = f"{note} Supplier note: {reason}"

    duration = _extract_duration(results or [], "6-18h by route" if mode == "train" else "5-16h by route")
    return _build_options(
        mode=mode,
        origin_city=origin_city,
        destination_city=destination_city,
        depart_date=depart_date,
        passengers=passengers,
        price_low=price_low,
        price_high=price_high,
        duration=duration,
        source=source,
        note=note,
        confidence=confidence,
        provider=web_context.get("provider", "estimate"),
        raw_results=results or [],
    )


def _search_indian_rail_api(
    origin_city: str,
    destination_city: str,
    depart_date: str,
    passengers: int,
    currency: str,
    max_price: int | None,
) -> dict[str, Any] | None:
    if not INDIAN_RAIL_API_KEY:
        return None

    origin_code = _station_code(origin_city)
    destination_code = _station_code(destination_city)
    if not origin_code or not destination_code:
        return None

    url = (
        "http://indianrailapi.com/api/v2/TrainBetweenStation/"
        f"apikey/{INDIAN_RAIL_API_KEY}/From/{origin_code}/To/{destination_code}/"
    )
    try:
        resp = requests.get(url, timeout=TRANSPORT_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    trains = data.get("Trains") if isinstance(data, dict) else None
    if not isinstance(trains, list) or not trains:
        return None

    price_low, price_high = _fallback_range("train", max_price=max_price)
    options = []
    for train in trains[:4]:
        if not isinstance(train, dict):
            continue
        options.append(
            {
                "mode": "train",
                "operator": "Indian Railways",
                "service_name": train.get("TrainName") or "Train option",
                "route": f"{origin_code} to {destination_code}",
                "departure": train.get("DepartureTime") or f"Flexible on {depart_date}",
                "arrival": train.get("ArrivalTime") or "Check live timetable",
                "duration": train.get("TravelTime") or "Check live timetable",
                "price_per_person": f"{_format_inr(price_low)} - {_format_inr(price_high)}",
                "total_price": _total_label(price_low, price_high, passengers),
                "passengers": passengers,
                "booking_note": (
                    "Train timing came from Indian Rail API. Fare is an estimated per-person range; "
                    "verify class availability and final fare before booking."
                ),
                "source": "Indian Rail API + fare estimate",
                "estimate_confidence": "Medium",
            }
        )

    if not options:
        return None

    return {
        "status": "estimated",
        "pricing_mode": "rail_api_timetable_estimate",
        "provider": "Indian Rail API",
        "mode": "train",
        "options": options,
        "message": "Train timetable data loaded from Indian Rail API; fares are estimated per person.",
    }


def search_ground_transport_options(
    origin_city: str,
    destination_city: str,
    depart_date: str,
    passengers: int = 1,
    selected_mode: str = "flight",
    currency: str = "INR",
    max_price: int | None = None,
) -> dict[str, Any]:
    selected = _clean_city(selected_mode)
    cache_key = (origin_city, destination_city, depart_date, passengers, selected, currency, max_price)
    cached = _transport_cache.get(*cache_key)
    if cached:
        return cached

    train_result = _search_indian_rail_api(
        origin_city=origin_city,
        destination_city=destination_city,
        depart_date=depart_date,
        passengers=passengers,
        currency=currency,
        max_price=max_price,
    ) or _search_ground_estimate(
        mode="train",
        origin_city=origin_city,
        destination_city=destination_city,
        depart_date=depart_date,
        passengers=passengers,
        currency=currency,
        max_price=max_price,
        reason="INDIAN_RAIL_API_KEY missing or route unavailable",
    )

    bus_result = _search_ground_estimate(
        mode="bus",
        origin_city=origin_city,
        destination_city=destination_city,
        depart_date=depart_date,
        passengers=passengers,
        currency=currency,
        max_price=max_price,
    )

    result = {
        "status": "ok",
        "selected_mode": selected if selected in {"train", "bus"} else "flight",
        "train": train_result,
        "bus": bus_result,
    }
    _transport_cache.set(result, *cache_key)
    return result
