import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from cache_utils import TTLCache
from ai_core.llm.groq_llm import get_groq_client
from ai_core.zapi.maps_api import get_distance, search_google_places_nearby
from backend.nearby.nearby_models import (
    Coordinates,
    NearbyAlternate,
    NearbyCosts,
    NearbyDiagnostics,
    NearbyPlanRequest,
    NearbyPlanResponse,
    NearbyRoute,
    NearbyScoreBreakdown,
    NearbySignal,
    NearbyStop,
    NearbySummary,
    NearbyTiming,
)


NEARBY_SEARCH_LIMIT = int(os.getenv("NEARBY_SEARCH_LIMIT", "8"))
NEARBY_QUERY_LIMIT = int(os.getenv("NEARBY_QUERY_LIMIT", "5"))
NEARBY_DISTANCE_CALL_LIMIT = int(os.getenv("NEARBY_DISTANCE_CALL_LIMIT", "4"))
NEARBY_EXPLANATION_TTL = int(os.getenv("NEARBY_EXPLANATION_CACHE_TTL", "21600"))
_explanation_cache = TTLCache(ttl_seconds=NEARBY_EXPLANATION_TTL)


MOOD_QUERIES = {
    "Relax": ["parks", "cafes", "spa"],
    "Adventure": ["adventure activities", "sports complex", "trekking"],
    "Food": ["restaurants", "street food", "cafes"],
    "Romantic": ["romantic restaurants", "view points", "gardens"],
    "Nature": ["parks", "lakes", "nature attractions"],
    "Nightlife": ["pubs", "live music", "nightlife"],
    "Shopping": ["markets", "shopping mall", "boutiques"],
    "Photography": ["tourist attractions", "view points", "art galleries"],
    "Hidden Gems": ["tourist attractions", "art galleries", "cafes"],
    "Luxury": ["fine dining", "luxury spa", "premium restaurants"],
    "Spiritual": ["temples", "churches", "spiritual places"],
    "Family": ["family attractions", "museums", "parks"],
    "Solo Recharge": ["book cafes", "parks", "museums"],
    "Rainy Day": ["museums", "indoor activities", "cafes"],
}

OUTDOOR_WORDS = ("park", "lake", "garden", "beach", "view", "trail", "fort", "outdoor")
INDOOR_WORDS = ("museum", "mall", "cafe", "restaurant", "gallery", "spa", "book", "indoor", "arcade")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signal(value: str, source: str, confidence: str = "medium", live: bool = False) -> NearbySignal:
    return NearbySignal(
        value=str(value),
        source=source,
        confidence=confidence,
        live=live,
        updated_at=_now_iso(),
    )


def _format_inr(value: int | float) -> str:
    return f"INR {max(int(value), 0):,}"


def _parse_money(value: str | int | float | None, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    match = re.search(r"([0-9][0-9,]*)", str(value or ""))
    return int(match.group(1).replace(",", "")) if match else fallback


def _short(value: str | None, fallback: str, max_words: int = 12) -> str:
    words = str(value or fallback).strip().split()
    return " ".join(words[:max_words]) or fallback


def _place_image_url(title: str, location: str = "", kind: str = "", width: int = 1100, height: int = 760) -> str:
    query = " ".join(part for part in (title, location, kind, "travel") if part)
    return f"https://source.unsplash.com/{width}x{height}/?{quote_plus(query)}"


def _duration_hours(duration: str) -> int:
    text = (duration or "").lower()
    if "2 hour" in text:
        return 2
    if "4 hour" in text:
        return 4
    if "half" in text:
        return 6
    if "full" in text:
        return 10
    if "weekend" in text:
        return 32
    if "2 day" in text:
        return 44
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 5


def _radius_km(radius: str) -> float:
    text = (radius or "").lower()
    if "5" in text:
        return 5
    if "20" in text:
        return 20
    if "1-hour" in text or "1 hour" in text:
        return 45
    if "3-hour" in text or "3 hour" in text:
        return 140
    return 20


def _haversine_km(a: Coordinates, b: Coordinates) -> float:
    earth_radius = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a.lat, a.lng, b.lat, b.lng])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return earth_radius * 2 * math.asin(math.sqrt(h))


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _extract_json_object(text: str) -> dict | None:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                return None
    return None


def _trip_name(data: NearbyPlanRequest) -> str:
    mood = data.moods[-1] if data.moods else "Nearby"
    if data.surprise_me:
        return f"{mood} Surprise Escape"
    return f"{data.group_type} {mood} Nearby Plan"


def _cost_for_place(place: dict, data: NearbyPlanRequest) -> int:
    category = str(place.get("category") or "").lower()
    price = str(place.get("price_level") or "")
    if "free" in price.lower():
        return 0
    base = 120
    if any(word in category for word in ("restaurant", "food", "cafe", "pub")):
        base = 450
    if any(word in category for word in ("spa", "fine", "luxury")):
        base = 1200
    if any(word in category for word in ("museum", "amusement", "adventure", "sports")):
        base = 350
    if "₹₹₹" in price or "$$$" in price:
        base *= 2
    if "₹₹" in price or "$$" in price:
        base = int(base * 1.35)
    if data.group_type in ("Family", "Office Team"):
        base = int(base * 1.4)
    return min(base, max(data.budget, 1))


def _queries_for_request(data: NearbyPlanRequest) -> list[str]:
    queries: list[str] = []
    for mood in data.moods:
        queries.extend(MOOD_QUERIES.get(mood, [mood]))
    if data.surprise_me:
        queries.append("hidden gems")
    deduped = []
    for query in queries:
        key = query.lower()
        if key not in deduped:
            deduped.append(key)
    return deduped[:NEARBY_QUERY_LIMIT] or ["tourist attractions", "restaurants"]


def _collect_candidates(data: NearbyPlanRequest) -> tuple[list[dict], list[str], int]:
    origin = data.coordinates
    radius = _radius_km(data.radius)
    warnings: list[str] = []
    candidates: dict[str, dict] = {}
    maps_calls = 0

    for query in _queries_for_request(data):
        result = search_google_places_nearby(
            origin.lat,
            origin.lng,
            query,
            radius_km=radius,
            max_results=NEARBY_SEARCH_LIMIT,
        )
        maps_calls += 1
        if result.get("error"):
            warnings.append(result["error"])
            continue
        for raw in result.get("places", []):
            lat = raw.get("latitude") or (raw.get("gps_coordinates") or {}).get("latitude")
            lng = raw.get("longitude") or (raw.get("gps_coordinates") or {}).get("longitude")
            if not raw.get("name") or lat is None or lng is None:
                continue
            coords = Coordinates(lat=float(lat), lng=float(lng))
            distance = _haversine_km(origin, coords)
            if distance > radius:
                continue
            key = re.sub(r"\s+", " ", str(raw["name"]).lower()).strip()
            current = candidates.get(key)
            if current and (current.get("rating") or 0) >= (raw.get("rating") or 0):
                continue
            candidates[key] = {
                **raw,
                "coordinates": coords,
                "distance_from_start_km": round(distance, 2),
                "matched_query": query,
                "estimated_cost_value": _cost_for_place(raw, data),
            }

    return list(candidates.values()), warnings, maps_calls


def _is_open(place: dict) -> bool:
    state = str(place.get("open_state") or place.get("hours") or "").lower()
    return "closed" not in state


def _is_outdoor(place: dict) -> bool:
    text = f"{place.get('name', '')} {place.get('category', '')} {place.get('matched_query', '')}".lower()
    return any(word in text for word in OUTDOOR_WORDS)


def _is_indoor(place: dict) -> bool:
    text = f"{place.get('name', '')} {place.get('category', '')} {place.get('matched_query', '')}".lower()
    return any(word in text for word in INDOOR_WORDS)


def _score_place(place: dict, data: NearbyPlanRequest, weather_safe: bool) -> NearbyScoreBreakdown:
    text = f"{place.get('name', '')} {place.get('category', '')} {place.get('matched_query', '')}".lower()
    mood_hits = sum(1 for mood in data.moods if mood.lower() in text or place.get("matched_query", "") in MOOD_QUERIES.get(mood, []))
    mood_match = min(30, (mood_hits / max(len(data.moods), 1)) * 30)
    radius = max(_radius_km(data.radius), 1)
    distance_score = max(0, 20 * (1 - (place["distance_from_start_km"] / radius)))
    per_stop_budget = max(data.budget / 3, 1)
    cost = place.get("estimated_cost_value", 0)
    budget_fit = 20 if cost <= per_stop_budget else max(0, 20 * (1 - ((cost - per_stop_budget) / max(per_stop_budget, 1))))
    rating = float(place.get("rating") or 3.8)
    rating_score = max(0, min(15, (rating / 5) * 15))
    weather_fit = 10 if weather_safe or _is_indoor(place) else 6 if not _is_outdoor(place) else 3
    opening_hours_fit = 5 if _is_open(place) else 0
    total = mood_match + distance_score + budget_fit + rating_score + weather_fit + opening_hours_fit
    return NearbyScoreBreakdown(
        mood_match=round(mood_match, 1),
        distance_score=round(distance_score, 1),
        budget_fit=round(budget_fit, 1),
        rating_score=round(rating_score, 1),
        weather_fit=round(weather_fit, 1),
        opening_hours_fit=round(opening_hours_fit, 1),
        total=round(total, 1),
    )


def _rank_candidates(candidates: list[dict], data: NearbyPlanRequest) -> list[dict]:
    weather_safe = "Rainy Day" in data.moods
    ranked = []
    for place in candidates:
        if not _is_open(place):
            continue
        score = _score_place(place, data, weather_safe)
        ranked.append({**place, "score_breakdown": score})
    return sorted(ranked, key=lambda item: item["score_breakdown"].total, reverse=True)


def _nearest_neighbor(origin: Coordinates, places: list[dict], limit: int) -> list[dict]:
    remaining = places[:]
    ordered = []
    cursor = origin
    while remaining and len(ordered) < limit:
        next_place = min(remaining, key=lambda item: _haversine_km(cursor, item["coordinates"]))
        ordered.append(next_place)
        remaining.remove(next_place)
        cursor = next_place["coordinates"]
    return ordered


def _route_legs(origin: Coordinates, stops: list[dict], data: NearbyPlanRequest) -> tuple[list[NearbySignal], list[NearbySignal], int]:
    distance_signals: list[NearbySignal] = []
    duration_signals: list[NearbySignal] = []
    calls = 0
    previous_label = f"{origin.lat},{origin.lng}"
    previous_coords = origin

    for stop in stops:
        label = f"{stop['coordinates'].lat},{stop['coordinates'].lng}"
        can_call = calls < NEARBY_DISTANCE_CALL_LIMIT
        if can_call:
            result = get_distance(previous_label, label)
            calls += 1
        else:
            result = {"error": "Distance call cap reached"}

        if result.get("distance") or result.get("duration"):
            distance_signals.append(_signal(result.get("distance") or "Route available", result.get("provider", "Google Maps"), "high", True))
            duration_signals.append(_signal(result.get("duration") or "Duration available", result.get("provider", "Google Maps"), "high", True))
        else:
            km = _haversine_km(previous_coords, stop["coordinates"])
            speed = 4.5 if data.transport == "Walking" else 18 if data.transport == "Bike" else 22 if data.transport == "Metro" else 24
            minutes = max(5, round((km / speed) * 60))
            distance_signals.append(_signal(f"{km:.1f} km", "Haversine estimate", "medium", False))
            duration_signals.append(_signal(f"{minutes} minutes", "Speed estimate", "medium", False))

        previous_label = label
        previous_coords = stop["coordinates"]

    return distance_signals, duration_signals, calls


def _allocate_budget(stops: list[dict], data: NearbyPlanRequest, duration_signals: list[NearbySignal]) -> tuple[NearbyCosts, list[int]]:
    stop_costs = [int(stop.get("estimated_cost_value") or 0) for stop in stops]
    ticket_total = sum(stop_costs)
    transport_total = min(round(data.budget * (0.05 if data.transport == "Walking" else 0.14)), max(data.budget - ticket_total, 0))
    food_total = min(round(data.budget * (0.35 if "Food" in data.moods else 0.22)), max(data.budget - ticket_total - transport_total, 0))
    shopping_total = min(round(data.budget * (0.16 if "Shopping" in data.moods else 0.05)), max(data.budget - ticket_total - transport_total - food_total, 0))
    used = ticket_total + transport_total + food_total + shopping_total
    if used > data.budget:
        scale = data.budget / max(used, 1)
        stop_costs = [int(value * scale) for value in stop_costs]
        ticket_total = sum(stop_costs)
        transport_total = int(transport_total * scale)
        food_total = int(food_total * scale)
        shopping_total = int(shopping_total * scale)
        used = ticket_total + transport_total + food_total + shopping_total
    buffer_total = max(data.budget - used, 0)
    signals = {
        "total": _signal(_format_inr(data.budget), "Budget allocator", "high", False),
        "transport": _signal(_format_inr(transport_total), "Budget allocator + route legs", "medium", False),
    }
    return (
        NearbyCosts(
            food=_format_inr(food_total),
            transport=_format_inr(transport_total),
            tickets=_format_inr(ticket_total),
            shopping=_format_inr(shopping_total),
            buffer=_format_inr(buffer_total),
            total=_format_inr(food_total + transport_total + ticket_total + shopping_total + buffer_total),
            signals=signals,
        ),
        stop_costs,
    )


def _template_explanations(stops: list[dict], data: NearbyPlanRequest) -> dict:
    return {
        "magic_touch": f"{stops[0]['name']} leads because it scores highest for {', '.join(data.moods[:2])} within {data.radius}.",
        "stop_reasons": {
            stop["name"]: f"Score {stop['score_breakdown'].total}/100 with real Maps coordinates and a budget-safe estimate."
            for stop in stops
        },
        "insights": [
            "Places, coordinates, ratings, and addresses come from Google Maps via SerpAPI.",
            "Costs, weather, AQI, and uncapped traffic are marked as estimates when no live source is configured.",
            "The route uses nearest-neighbor ordering and capped distance calls to protect API quotas.",
        ],
        "alternates": {
            "cheaper": "Drops premium picks and keeps free or low-cost stops first.",
            "luxury": "Raises budget and prefers higher-cost dining or spa-style anchors.",
            "faster": "Reduces the route to the closest two high-scoring stops.",
            "weather": "Prefers indoor categories and keeps outdoor stops optional.",
        },
    }


def _groq_explanations(stops: list[dict], data: NearbyPlanRequest) -> tuple[dict, int, bool]:
    def score_payload(score: NearbyScoreBreakdown) -> dict:
        return score.model_dump() if hasattr(score, "model_dump") else score.dict()

    payload = {
        "location": data.location or data.detected_city,
        "moods": data.moods[:4],
        "budget": data.budget,
        "radius": data.radius,
        "stops": [
            {
                "name": stop["name"],
                "category": stop.get("category"),
                "rating": stop.get("rating"),
                "distance_km": stop.get("distance_from_start_km"),
                "score": score_payload(stop["score_breakdown"]),
            }
            for stop in stops
        ],
    }
    cache_key = hashlib.sha1(_json_dumps(payload).encode("utf-8")).hexdigest()
    cached = _explanation_cache.get(cache_key)
    if cached:
        return cached, 0, True

    try:
        client = get_groq_client()
        model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        prompt = f"""
Write compact nearby-plan explanations as JSON only.
Input={_json_dumps(payload)}
Return keys: magic_touch string max 24 words, stop_reasons object keyed by stop name max 14 words each, insights array of 3 strings max 14 words, alternates object with cheaper/luxury/faster/weather max 12 words each.
Do not invent new places, coordinates, prices, live traffic, AQI, or weather.
"""
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=int(os.getenv("NEARBY_GROQ_MAX_TOKENS", "420")),
            response_format={"type": "json_object"},
        )
        parsed = _extract_json_object(response.choices[0].message.content)
        if not parsed:
            raise ValueError("Groq returned non-JSON")
        fallback = _template_explanations(stops, data)
        merged = {
            "magic_touch": parsed.get("magic_touch") or fallback["magic_touch"],
            "stop_reasons": {**fallback["stop_reasons"], **(parsed.get("stop_reasons") or {})},
            "insights": (parsed.get("insights") or fallback["insights"])[:3],
            "alternates": {**fallback["alternates"], **(parsed.get("alternates") or {})},
        }
        _explanation_cache.set(merged, cache_key)
        return merged, 1, False
    except Exception:
        return _template_explanations(stops, data), 0, False


def _validate_plan(stops: list[dict], costs: NearbyCosts, data: NearbyPlanRequest, duration_signals: list[NearbySignal]) -> list[str]:
    errors: list[str] = []
    radius = _radius_km(data.radius)
    if not stops:
        errors.append("No real nearby stops found.")
    names = set()
    for stop in stops:
        name_key = str(stop.get("name", "")).lower().strip()
        if name_key in names:
            errors.append(f"Duplicate stop rejected: {stop.get('name')}")
        names.add(name_key)
        if not stop.get("coordinates"):
            errors.append(f"Missing real coordinates: {stop.get('name')}")
        if stop.get("distance_from_start_km", 0) > radius:
            errors.append(f"Outside requested radius: {stop.get('name')}")
        if not _is_open(stop):
            errors.append(f"Closed place excluded: {stop.get('name')}")
    if _parse_money(costs.total) > data.budget:
        errors.append("Total cost exceeds requested budget.")
    route_minutes = sum(_parse_money(signal.value, 0) for signal in duration_signals)
    visit_minutes = len(stops) * (40 if _duration_hours(data.duration) <= 2 else 60)
    if route_minutes + visit_minutes > _duration_hours(data.duration) * 60:
        errors.append("Route does not fit requested duration.")
    if "Rainy Day" in data.moods and any(_is_outdoor(stop) for stop in stops) and not any(_is_indoor(stop) for stop in stops):
        errors.append("Outdoor stops need an indoor weather-safe alternative.")
    return errors


def _build_alternates(data: NearbyPlanRequest, explanations: dict) -> list[NearbyAlternate]:
    alt_text = explanations.get("alternates") or {}
    return [
        NearbyAlternate(
            id="cheaper",
            title="Cheaper version",
            budget=_format_inr(max(300, round(data.budget * 0.7))),
            duration=data.duration,
            description=alt_text.get("cheaper", "Prioritizes free and low-cost nearby stops."),
            tags=["Budget", "Interactive"],
            request_patch={"budget": max(300, round(data.budget * 0.7)), "moods": [*data.moods, "Hidden Gems"]},
        ),
        NearbyAlternate(
            id="luxury",
            title="Luxury version",
            budget=_format_inr(round(data.budget * 1.6)),
            duration=data.duration,
            description=alt_text.get("luxury", "Upgrades dining and premium indoor anchors."),
            tags=["Luxury", "Interactive"],
            request_patch={"budget": round(data.budget * 1.6), "moods": [*data.moods, "Luxury"]},
        ),
        NearbyAlternate(
            id="faster",
            title="Faster version",
            budget=_format_inr(data.budget),
            duration="2 Hours",
            description=alt_text.get("faster", "Keeps the two closest high-scoring stops."),
            tags=["Fast", "Low commute"],
            request_patch={"duration": "2 Hours", "radius": "Within 5 km"},
        ),
        NearbyAlternate(
            id="weather",
            title="Weather-safe version",
            budget=_format_inr(data.budget),
            duration=data.duration,
            description=alt_text.get("weather", "Prefers indoor places and outdoor backups."),
            tags=["Rainy Day", "Indoor"],
            request_patch={"moods": [*data.moods, "Rainy Day"]},
        ),
    ]


def generate_nearby_plan(data: NearbyPlanRequest) -> NearbyPlanResponse:
    warnings: list[str] = []
    candidates, search_warnings, maps_calls = _collect_candidates(data)
    warnings.extend(search_warnings)
    ranked = _rank_candidates(candidates, data)
    if len(ranked) < 2:
        raise ValueError("Nearby planner needs at least two real, open Google Maps places with coordinates.")

    stop_count = 2 if _duration_hours(data.duration) <= 2 else 3
    selected = _nearest_neighbor(data.coordinates, ranked[:8], stop_count)
    distance_signals, duration_signals, distance_calls = _route_legs(data.coordinates, selected, data)
    maps_calls += distance_calls
    costs, stop_costs = _allocate_budget(selected, data, duration_signals)
    explanations, groq_calls, explanation_cache_hit = _groq_explanations(selected, data)

    errors = _validate_plan(selected, costs, data, duration_signals)
    if errors:
        raise ValueError("; ".join(errors))

    total_distance = sum(float(re.search(r"[\d.]+", signal.value).group(0)) for signal in distance_signals if re.search(r"[\d.]+", signal.value))
    total_route_minutes = sum(_parse_money(signal.value, 0) for signal in duration_signals)
    best_leave = "Now"
    weather_live = False
    weather_value = "Weather not live; indoor backup considered" if "Rainy Day" in data.moods else "Weather estimate; verify before leaving"

    stop_reasons = explanations.get("stop_reasons") or {}
    stops: list[NearbyStop] = []
    for index, stop in enumerate(selected):
        cost = stop_costs[index] if index < len(stop_costs) else int(stop.get("estimated_cost_value") or 0)
        leg_duration = duration_signals[index] if index < len(duration_signals) else _signal("Estimate", "Deterministic estimate")
        leg_distance = distance_signals[index] if index < len(distance_signals) else _signal("Estimate", "Deterministic estimate")
        opening_value = stop.get("open_state") or stop.get("hours") or "Opening hours not returned"
        stops.append(
            NearbyStop(
                id=f"stop-{index + 1}",
                sequence=index + 1,
                title=stop["name"],
                image=_place_image_url(stop["name"], data.location or data.detected_city, stop.get("category") or "nearby"),
                description=_short(stop.get("category") or stop.get("address"), "Real nearby place", 9),
                eta=best_leave if index == 0 else f"+{sum(_parse_money(item.value, 0) for item in duration_signals[:index]) + index * 55} mins",
                ideal_visit_duration="40 mins" if _duration_hours(data.duration) <= 2 else "60 mins",
                estimated_cost=_format_inr(cost),
                travel_time_to_next="Return when ready" if index == len(selected) - 1 else duration_signals[index + 1].value if index + 1 < len(duration_signals) else leg_duration.value,
                crowd_level="Estimated; no live crowd source",
                weather_suitability="Indoor-safe" if _is_indoor(stop) else "Outdoor; verify weather",
                opening_hours=str(opening_value),
                why_ai_picked_this=_short(stop_reasons.get(stop["name"]), "High deterministic score and real map data.", 14),
                mood_tags=[*data.moods[:3], str(stop.get("category") or "Nearby")][:5],
                coordinates=stop["coordinates"],
                backup_plan="Use the closest indoor scored stop if weather changes." if _is_outdoor(stop) else "Works as the indoor backup stop.",
                address=stop.get("address") or "",
                rating=float(stop["rating"]) if stop.get("rating") is not None else None,
                category=stop.get("category") or "",
                distance_from_start_km=float(stop.get("distance_from_start_km") or 0),
                score_breakdown=stop["score_breakdown"],
                signals={
                    "coordinates": _signal(f"{stop['coordinates'].lat},{stop['coordinates'].lng}", "Google Maps", "high", True),
                    "rating": _signal(str(stop.get("rating") or "Not returned"), "Google Maps", "high" if stop.get("rating") else "medium", True),
                    "opening_hours": _signal(str(opening_value), "Google Maps", "high" if stop.get("open_state") else "medium", bool(stop.get("open_state"))),
                    "distance_from_previous": leg_distance,
                    "duration_from_previous": leg_duration,
                    "estimated_cost": _signal(_format_inr(cost), "Budget allocator", "medium", False),
                },
            )
        )

    map_coordinates = [stop.coordinates for stop in stops]
    summary_signals = {
        "total_travel_distance": _signal(f"{total_distance:.1f} km", "Google Maps + capped estimates", "high" if any(item.live for item in distance_signals) else "medium", any(item.live for item in distance_signals)),
        "estimated_budget": _signal(costs.total, "Budget validator", "high", False),
        "weather_snapshot": _signal(weather_value, "Deterministic weather guardrail", "medium", weather_live),
        "best_time_to_leave": _signal(best_leave, "Route scheduler", "medium", False),
    }

    return NearbyPlanResponse(
        summary=NearbySummary(
            title=_trip_name(data),
            location=data.location or data.detected_city or "Current location",
            total_duration=data.duration,
            estimated_budget=costs.total,
            total_travel_distance=f"{total_distance:.1f} km",
            weather_snapshot=weather_value,
            best_time_to_leave=best_leave,
            vibe_tags=[*data.moods, data.group_type, data.transport][:7],
            magic_touch=_short(explanations.get("magic_touch"), f"{stops[0].title} is the strongest scored match.", 24),
            signals=summary_signals,
        ),
        stops=stops,
        timing=NearbyTiming(
            generated_at=_now_iso(),
            best_leave=best_leave,
            golden_hour="Estimate; verify local sunset",
            nightlife_window="Estimate; verify venue timing" if "Nightlife" in data.moods else "Optional if venues are open",
            traffic_note=f"{total_route_minutes} minutes route time from capped Maps/estimate legs.",
            rainy_day_cutover="Switch outdoor stops to indoor backups if rain starts.",
            signals={
                "traffic_note": _signal(f"{total_route_minutes} minutes", "Google Maps + capped estimates", "medium", any(item.live for item in duration_signals)),
                "golden_hour": _signal("Estimate; verify local sunset", "Deterministic estimate", "medium", False),
                "rainy_day_cutover": _signal("Indoor backup required for outdoor stops", "Weather guardrail", "medium", False),
            },
        ),
        costs=costs,
        route=NearbyRoute(
            mode=data.transport,
            radius=data.radius,
            optimized_order=[stop.title for stop in stops],
            estimated_commute_time=f"{total_route_minutes} minutes",
            transport_aware_routing="Nearest-neighbor order over real place coordinates.",
            traffic_awareness="Durations use capped Google Maps calls; estimates are labeled when caps or keys limit live data.",
            map_coordinates=map_coordinates,
            leg_distances=distance_signals,
            leg_durations=duration_signals,
        ),
        insights=[str(item) for item in explanations.get("insights", [])[:3]],
        alternates=_build_alternates(data, explanations),
        map_coordinates=map_coordinates,
        diagnostics=NearbyDiagnostics(
            status="ok",
            source="Google Maps deterministic pipeline + Groq explanations",
            validation_errors=[],
            warnings=warnings,
            maps_calls=maps_calls,
            groq_calls=groq_calls,
            cache_hit=explanation_cache_hit,
        ),
    )
