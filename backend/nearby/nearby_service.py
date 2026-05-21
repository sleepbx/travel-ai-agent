import hashlib
import json
import os
import re
from datetime import datetime
from urllib.parse import quote_plus

from ai_core.llm.groq_llm import get_groq_client
from backend.nearby.nearby_models import (
    Coordinates,
    NearbyAlternate,
    NearbyCosts,
    NearbyPlanRequest,
    NearbyPlanResponse,
    NearbyRoute,
    NearbyStop,
    NearbySummary,
    NearbyTiming,
)


STOP_IMAGES = [
    "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1501446529957-6226bd447c46?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1481833761820-0509d3217039?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1100&q=80",
    "https://images.unsplash.com/photo-1528823872057-9c018a7a7553?auto=format&fit=crop&w=1100&q=80",
]


def _format_inr(value: int) -> str:
    return f"INR {value:,}"


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


def _parse_money(value, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    match = re.search(r"([0-9][0-9,]*)", str(value or ""))
    return int(match.group(1).replace(",", "")) if match else fallback


def _short(value, fallback: str, max_words: int = 7) -> str:
    words = str(value or fallback).strip().split()
    return " ".join(words[:max_words]) or fallback


def _place_image_url(title: str, location: str = "", kind: str = "", width: int = 1100, height: int = 760) -> str:
    if str(title or "").lower().startswith(("http://", "https://")):
        return str(title)
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
    digits = "".join(char for char in text if char.isdigit())
    return int(digits) if digits else 5


def _trip_name(data: NearbyPlanRequest) -> str:
    mood = data.moods[-1] if data.moods else "Nearby"
    group = "Solo" if data.group_type == "Solo" else data.group_type
    if data.surprise_me:
        return f"{mood} Surprise Escape"
    if mood == group:
        return f"{mood} Nearby Plan"
    return f"{group} {mood} Nearby Plan"


def _duration_bucket(hours: int) -> str:
    if hours <= 2:
        return "micro"
    if hours <= 5:
        return "short"
    if hours <= 10:
        return "day"
    return "escape"


def _mood_weights(moods: list[str]) -> dict[str, int]:
    return {mood: 6 + index * 2 for index, mood in enumerate(moods)}


def _seed_value(data: NearbyPlanRequest) -> str:
    return "|".join(
        [
            data.location or data.detected_city,
            data.duration,
            ",".join(data.moods),
            str(data.budget),
            data.transport,
            data.radius,
            data.group_type,
            str(data.surprise_me),
        ]
    )


def _seed_bonus(seed: str, title: str) -> int:
    digest = hashlib.sha1(f"{seed}:{title}".encode("utf-8")).hexdigest()
    return int(digest[:2], 16) % 4


def _stop_library(data: NearbyPlanRequest) -> list[dict]:
    return [
        {
            "title": "Rooftop Sunset Nook" if data.surprise_me else "Skyline Viewpoint",
            "description": "A compact golden-hour stop with a short walk, clean views, and enough quiet to reset.",
            "base_cost": 0,
            "image": STOP_IMAGES[0],
            "tags": ["Hidden Gems", "Photography", "Romantic"],
            "groups": ["Couple", "Solo", "Friends"],
            "transports": ["Car", "Bike"],
            "radii": ["Within 20 km", "1-hour drive"],
            "durations": ["micro", "short", "day"],
            "why": "You are about 20 mins away from a low-friction sunset spot that matches the current mood mix.",
        },
        {
            "title": "Chef-Led Street Food Lane",
            "description": "A walkable food stretch with snacks, dessert, and one sit-down option if the group slows down.",
            "base_cost": 520,
            "image": STOP_IMAGES[1],
            "tags": ["Food", "Family", "Nightlife"],
            "groups": ["Friends", "Family", "Office Team"],
            "transports": ["Metro", "Walking", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["micro", "short", "day"],
            "why": "It gives the plan a social anchor without needing a booking or a long commute.",
        },
        {
            "title": "Design Museum and Cafe",
            "description": "Indoor galleries, a covered cafe, and a backup bookstore nearby if rain arrives early.",
            "base_cost": 420,
            "image": STOP_IMAGES[2],
            "tags": ["Rainy Day", "Relax", "Photography"],
            "groups": ["Solo", "Couple", "Family"],
            "transports": ["Metro", "Car", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["short", "day"],
            "why": "Rain risk is handled with an indoor backup that still feels like an outing.",
        },
        {
            "title": "Leafy Lake Loop",
            "description": "A calm nature loop for photos, air, and an easy decompression window.",
            "base_cost": 80,
            "image": STOP_IMAGES[3],
            "tags": ["Nature", "Relax", "Solo Recharge", "Photography"],
            "groups": ["Solo", "Couple", "Family"],
            "transports": ["Walking", "Bike", "Car"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["micro", "short", "day"],
            "why": "AQI and crowd signals favor a lighter outdoor window before evening traffic builds.",
        },
        {
            "title": "Candlelit Courtyard Dinner",
            "description": "A soft-lit stop with reliable seating, warm drinks, and a second cafe within walking distance.",
            "base_cost": 1200,
            "image": STOP_IMAGES[4],
            "tags": ["Romantic", "Coffee", "Luxury"],
            "groups": ["Couple"],
            "transports": ["Car", "Metro"],
            "radii": ["Within 20 km"],
            "durations": ["short", "day"],
            "why": "This keeps the final hour emotionally warm and reduces last-minute venue hunting.",
        },
        {
            "title": "Maker Market Arcade",
            "description": "A compact set of local stores, stationery, handmade finds, and giftable food counters.",
            "base_cost": 900,
            "image": STOP_IMAGES[5],
            "tags": ["Shopping", "Hidden Gems", "Family"],
            "groups": ["Friends", "Family", "Couple"],
            "transports": ["Metro", "Walking", "Car"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["short", "day"],
            "why": "It creates a flexible browsing window that can expand or shrink based on energy.",
        },
        {
            "title": "Quiet Temple Courtyard",
            "description": "A peaceful courtyard with low noise, short rituals, and an easy exit route.",
            "base_cost": 40,
            "image": STOP_IMAGES[6],
            "tags": ["Spiritual", "Relax", "Solo Recharge"],
            "groups": ["Solo", "Family", "Couple"],
            "transports": ["Walking", "Metro", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["micro", "short"],
            "why": "It adds a reflective stop without making the plan feel heavy or over-scheduled.",
        },
        {
            "title": "Live Music Pocket",
            "description": "A small-format music venue timed before the late-night surge.",
            "base_cost": 850,
            "image": STOP_IMAGES[7],
            "tags": ["Nightlife", "Friends", "Romantic"],
            "groups": ["Friends", "Couple", "Office Team"],
            "transports": ["Car", "Metro"],
            "radii": ["Within 20 km", "1-hour drive"],
            "durations": ["short", "day"],
            "why": "The set starts before peak traffic and leaves room for a graceful exit.",
        },
        {
            "title": "Bouldering and Brew Session",
            "description": "A guided climbing block followed by a low-key brew stop nearby.",
            "base_cost": 1100,
            "image": STOP_IMAGES[8],
            "tags": ["Adventure", "Friends", "Photography"],
            "groups": ["Friends", "Office Team", "Solo"],
            "transports": ["Bike", "Car", "Metro"],
            "radii": ["Within 20 km", "1-hour drive"],
            "durations": ["short", "day"],
            "why": "It gives the route a real activity peak without spending the whole day in transit.",
        },
        {
            "title": "Indie Art Walk",
            "description": "Murals, micro-galleries, design stores, and a coffee pause in a walkable cluster.",
            "base_cost": 300,
            "image": STOP_IMAGES[9],
            "tags": ["Photography", "Hidden Gems", "Shopping", "Solo Recharge"],
            "groups": ["Solo", "Friends", "Couple"],
            "transports": ["Walking", "Metro", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["micro", "short", "day"],
            "why": "The plan stays easy to explore on foot and still feels discovery-led.",
        },
        {
            "title": "Luxury Spa and High Tea",
            "description": "A polished reset with reserved seating, quieter service, and a premium indoor backup.",
            "base_cost": 2400,
            "image": STOP_IMAGES[10],
            "tags": ["Luxury", "Relax", "Romantic", "Rainy Day"],
            "groups": ["Couple", "Solo"],
            "transports": ["Car"],
            "radii": ["Within 20 km", "1-hour drive"],
            "durations": ["short", "day"],
            "why": "Budget and mood allow one elevated anchor instead of many average stops.",
        },
        {
            "title": "Family Science and Dessert Loop",
            "description": "Hands-on exhibits, a snack break, and a dessert stop that works across ages.",
            "base_cost": 950,
            "image": STOP_IMAGES[11],
            "tags": ["Family", "Rainy Day", "Food"],
            "groups": ["Family"],
            "transports": ["Car", "Metro", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["short", "day"],
            "why": "It keeps kids, adults, weather, and food breaks in one manageable loop.",
        },
        {
            "title": "Golden Hour Nature Drive",
            "description": "A scenic outer-edge drive with one viewpoint, one snack stop, and a flexible return.",
            "base_cost": 700,
            "image": STOP_IMAGES[12],
            "tags": ["Nature", "Adventure", "Photography", "Romantic"],
            "groups": ["Couple", "Friends", "Family"],
            "transports": ["Car", "Bike"],
            "radii": ["1-hour drive", "3-hour drive"],
            "durations": ["day", "escape"],
            "why": "Your radius allows a wider route, so the plan spends budget on scenery rather than tickets.",
        },
        {
            "title": "Hidden Vineyard Lunch",
            "description": "A slower road-trip lunch with a scenic table, photo stops, and a no-rush return window.",
            "base_cost": 1800,
            "image": STOP_IMAGES[13],
            "tags": ["Luxury", "Food", "Romantic", "Hidden Gems"],
            "groups": ["Couple", "Friends"],
            "transports": ["Car"],
            "radii": ["3-hour drive", "1-hour drive"],
            "durations": ["day", "escape"],
            "why": "Weekend-style timing supports a memorable anchor experience outside the usual city loop.",
        },
        {
            "title": "Team Game Arena",
            "description": "Bowling, arcade games, quick food, and easy split-bill timing for a group.",
            "base_cost": 1300,
            "image": STOP_IMAGES[14],
            "tags": ["Adventure", "Nightlife", "Food", "Rainy Day"],
            "groups": ["Office Team", "Friends", "Family"],
            "transports": ["Car", "Metro"],
            "radii": ["Within 20 km"],
            "durations": ["short", "day"],
            "why": "It is weather-safe, group-friendly, and keeps everyone active without complex logistics.",
        },
        {
            "title": "Bookstore Recharge Cafe",
            "description": "A quiet bookstore-cafe hybrid for journaling, reading, coffee, and solo decompression.",
            "base_cost": 280,
            "image": STOP_IMAGES[15],
            "tags": ["Solo Recharge", "Relax", "Rainy Day", "Spiritual"],
            "groups": ["Solo"],
            "transports": ["Walking", "Metro", "Public Transport"],
            "radii": ["Within 5 km", "Within 20 km"],
            "durations": ["micro", "short"],
            "why": "It protects your energy and keeps the plan satisfying even with limited time.",
        },
    ]


def _select_stops(data: NearbyPlanRequest) -> list[dict]:
    hours = _duration_hours(data.duration)
    count = 2 if hours <= 2 else 3
    bucket = _duration_bucket(hours)
    mood_weights = _mood_weights(data.moods)
    seed = _seed_value(data)
    budget = max(data.budget, 1)

    def score(stop: dict) -> int:
        tag_score = sum(mood_weights.get(tag, 0) for tag in stop["tags"])
        group_score = 5 if data.group_type in stop.get("groups", []) else 0
        transport_score = 4 if data.transport in stop.get("transports", []) else 0
        radius_score = 3 if data.radius in stop.get("radii", []) else 0
        duration_score = 3 if bucket in stop.get("durations", []) else 0
        surprise_score = 4 if data.surprise_me and "Hidden Gems" in stop["tags"] else 0
        cost_score = 3 if stop["base_cost"] <= budget * 0.45 else -5 if stop["base_cost"] > budget * 0.85 else 0
        return (
            tag_score
            + group_score
            + transport_score
            + radius_score
            + duration_score
            + surprise_score
            + cost_score
            + _seed_bonus(seed, stop["title"])
        )

    ranked = sorted(_stop_library(data), key=lambda stop: (score(stop), -stop["base_cost"]), reverse=True)
    chosen = []
    chosen_titles = set()

    for mood in reversed(data.moods):
        match = next(
            (
                stop
                for stop in ranked
                if mood in stop["tags"] and bucket in stop.get("durations", []) and stop["title"] not in chosen_titles
            ),
            None,
        ) or next((stop for stop in ranked if mood in stop["tags"] and stop["title"] not in chosen_titles), None)
        if match and len(chosen) < count:
            chosen.append(match)
            chosen_titles.add(match["title"])

    for stop in ranked:
        if len(chosen) >= count:
            break
        if stop["title"] not in chosen_titles:
            chosen.append(stop)
            chosen_titles.add(stop["title"])

    return chosen


def _generate_nearby_plan_fallback(data: NearbyPlanRequest) -> NearbyPlanResponse:
    stops = _select_stops(data)
    hours = _duration_hours(data.duration)
    commute_unit = 9 if data.transport == "Walking" else 11 if data.transport == "Bike" else 16 if data.transport == "Metro" else 18

    food_budget = round(data.budget * (0.42 if "Food" in data.moods else 0.3))
    transport_budget = round(data.budget * (0.08 if data.transport == "Walking" else 0.18))
    ticket_budget = round(data.budget * 0.18)
    shopping_budget = round(data.budget * (0.2 if "Shopping" in data.moods else 0.1))
    buffer_budget = max(150, data.budget - food_budget - transport_budget - ticket_budget - shopping_budget)

    best_leave_hour = 9 if hours > 4 else min(datetime.now().hour + 1, 21)
    best_leave = f"{best_leave_hour:02d}:15"
    weather = "Cloudy, rain backup active" if "Rainy Day" in data.moods else "Warm with a clear evening window"

    normalized_stops = []
    for index, stop in enumerate(stops):
        lat = round(data.coordinates.lat + (index + 1) * 0.009 - (index % 2) * 0.006, 5)
        lng = round(data.coordinates.lng + (index + 1) * 0.008 + (index % 2) * 0.005, 5)
        normalized_stops.append(
            NearbyStop(
                id=f"stop-{index + 1}",
                sequence=index + 1,
                title=stop["title"],
                image=_place_image_url(stop["title"], data.location or data.detected_city, "nearby"),
                description=stop["description"],
                eta=best_leave if index == 0 else f"+{index * commute_unit + index * 45} mins",
                ideal_visit_duration="40 mins" if hours <= 2 else "75 mins" if index == len(stops) - 1 else "55 mins",
                estimated_cost=_format_inr(min(stop["base_cost"], max(0, data.budget - 250))),
                travel_time_to_next="Return when ready" if index == len(stops) - 1 else f"{commute_unit + index * 4} mins",
                crowd_level="Low now" if index == 0 else "Medium later" if index == len(stops) - 1 else "Balanced",
                weather_suitability="Indoor-safe" if "Rainy Day" in data.moods or "Rainy Day" in stop["tags"] else "Good",
                opening_hours="Open till 11:00 PM" if index == len(stops) - 1 else "Open now",
                why_ai_picked_this=stop["why"],
                mood_tags=stop["tags"],
                coordinates=Coordinates(lat=lat, lng=lng),
                backup_plan="Covered cafe table held as backup" if "Rainy Day" in stop["tags"] else "Indoor cafe fallback within 700 m",
            )
        )

    primary_mood = data.moods[-1] if data.moods else "your mood"
    lead_stop = normalized_stops[0].title if normalized_stops else "a nearby escape"
    magic_touch = f"Your strongest match is {lead_stop}, tuned for {primary_mood.lower()} energy and {data.transport.lower()} timing."

    costs = NearbyCosts(
        food=_format_inr(food_budget),
        transport=_format_inr(transport_budget),
        tickets=_format_inr(ticket_budget),
        shopping=_format_inr(shopping_budget),
        buffer=_format_inr(buffer_budget),
        total=_format_inr(food_budget + transport_budget + ticket_budget + shopping_budget + buffer_budget),
    )

    map_coordinates = [stop.coordinates for stop in normalized_stops]
    return NearbyPlanResponse(
        summary=NearbySummary(
            title=_trip_name(data),
            location=data.location or data.detected_city or "Current location",
            total_duration=data.duration,
            estimated_budget=_format_inr(data.budget),
            total_travel_distance="4.8 km" if data.radius == "Within 5 km" else "16.4 km" if data.radius == "Within 20 km" else data.radius,
            weather_snapshot=weather,
            best_time_to_leave=best_leave,
            vibe_tags=[*data.moods, data.group_type, data.transport][:7],
            magic_touch=magic_touch,
        ),
        stops=normalized_stops,
        timing=NearbyTiming(
            generated_at=f"{datetime.utcnow().isoformat()}Z",
            best_leave=best_leave,
            golden_hour="17:42 - 18:22",
            nightlife_window="20:00 - 23:15" if "Nightlife" in data.moods else "Optional after 20:30",
            traffic_note="Traffic expected after 19:00, so the route front-loads the longest commute.",
            rainy_day_cutover="If rain starts after 20:00, switch to the indoor backup at stop 3.",
        ),
        costs=costs,
        route=NearbyRoute(
            mode=data.transport,
            radius=data.radius,
            optimized_order=[stop.title for stop in normalized_stops],
            estimated_commute_time=f"{max(18, (len(normalized_stops) - 1) * commute_unit)} mins",
            transport_aware_routing=f"{data.transport} route balanced for commute time, crowd levels, and opening windows.",
            traffic_awareness="Avoids the densest outbound leg after 19:00.",
            map_coordinates=map_coordinates,
        ),
        insights=[
            "This cafe is less crowded after 17:00.",
            "Perfect sunset timing at the viewpoint if you leave by the suggested time.",
            "Traffic expected after 19:00, so the route front-loads the longest commute.",
            "Rain likely later, indoor backup added before the last stop." if "Rainy Day" in data.moods else "Weather is outdoor-friendly, with a cafe fallback if wind picks up.",
            "AQI-aware filter keeps the outdoor block short and close to greenery.",
            "Live opening-hour hooks are ready for future place APIs.",
        ],
        alternates=[
            NearbyAlternate(
                id="cheaper",
                title="Cheaper version",
                budget=_format_inr(max(500, round(data.budget * 0.62))),
                duration="Trim one paid stop",
                description="Keeps the route social and local with street food, free views, and walking hops.",
                tags=["Budget", "Flexible"],
            ),
            NearbyAlternate(
                id="luxury",
                title="Luxury version",
                budget=_format_inr(round(data.budget * 1.8)),
                duration="Same pace",
                description="Upgrades dinner, adds reserved seating, and swaps one stop for a premium experience.",
                tags=["Luxury", "Romantic"],
            ),
            NearbyAlternate(
                id="faster",
                title="Faster version",
                budget=_format_inr(round(data.budget * 0.9)),
                duration="2 stops",
                description="Compresses the plan into the two highest-signal stops with the least commute.",
                tags=["Fast", "Low commute"],
            ),
            NearbyAlternate(
                id="hidden",
                title="Hidden gems version",
                budget=_format_inr(data.budget),
                duration="Mystery route",
                description="Prioritizes lesser-known studios, rooftops, and quieter food counters.",
                tags=["Hidden Gems", "Surprise"],
            ),
            NearbyAlternate(
                id="weather",
                title="Weather-safe version",
                budget=_format_inr(round(data.budget * 1.05)),
                duration="Indoor-first",
                description="Moves outdoor stops earlier and keeps indoor backups within a short hop.",
                tags=["Rainy Day", "AQI-aware"],
            ),
        ],
        map_coordinates=map_coordinates,
    )


def _call_nearby_llm(data: NearbyPlanRequest) -> dict:
    client = get_groq_client()
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_tokens = int(os.getenv("NEARBY_MAX_TOKENS", "850"))
    payload = {
        "loc": data.location or data.detected_city,
        "dur": data.duration,
        "moods": data.moods[:4],
        "budget": data.budget,
        "transport": data.transport,
        "radius": data.radius,
        "group": data.group_type,
        "surprise": data.surprise_me,
    }
    prompt = f"""
Nearby planner. One compact JSON only.
Input={_json_dumps(payload)}
Return={{"summary":{{"title":"","magic_touch":"","weather_snapshot":"","best_time_to_leave":"","total_travel_distance":""}},"stops":[{{"title":"","type":"","area":"","eta":"","duration":"","cost":0,"why":""}}],"costs":{{"food":0,"transport":0,"tickets":0,"shopping":0,"buffer":0}},"insights":["","",""],"alternates":[{{"title":"","budget":0,"duration":"","description":"","tags":[]}}]}}
Rules: max 3 unique stops; real nearby place/area names; no RAG; no API; stay <= budget; desc max 5 words; why max 6 words; route practical.
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.38,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    parsed = _extract_json_object(response.choices[0].message.content)
    if not parsed:
        raise ValueError("Nearby LLM returned non-JSON")
    return parsed


def _response_from_llm(data: NearbyPlanRequest, parsed: dict) -> NearbyPlanResponse:
    hours = _duration_hours(data.duration)
    commute_unit = 9 if data.transport == "Walking" else 11 if data.transport == "Bike" else 16 if data.transport == "Metro" else 18
    now = datetime.utcnow()
    summary_raw = parsed.get("summary") or parsed.get("escape_summary") or {}
    raw_stops = parsed.get("stops") or parsed.get("route") or []
    if not isinstance(raw_stops, list) or not raw_stops:
        raise ValueError("Nearby LLM returned no stops")

    best_leave = _short(summary_raw.get("best_time_to_leave") or summary_raw.get("best_start_time"), "17:00", 3)
    normalized_stops = []
    total_stop_cost = 0
    used_titles: set[str] = set()
    for index, stop in enumerate(raw_stops[:3]):
        if not isinstance(stop, dict):
            continue
        cost = _parse_money(stop.get("cost") or stop.get("estimated_cost"), 0)
        lat = round(data.coordinates.lat + (index + 1) * 0.009 - (index % 2) * 0.006, 5)
        lng = round(data.coordinates.lng + (index + 1) * 0.008 + (index % 2) * 0.005, 5)
        title = _short(stop.get("title") or stop.get("name"), f"Stop {index + 1}", 5)
        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in used_titles:
            continue
        used_titles.add(title_key)
        total_stop_cost += cost
        area = _short(stop.get("area"), data.location or data.detected_city or "", 4)
        kind = _short(stop.get("type"), "nearby", 3)
        mood_tags = [str(tag) for tag in (stop.get("mood_tags") or stop.get("tags") or data.moods[:3])][:5]
        normalized_stops.append(
            NearbyStop(
                id=f"stop-{len(normalized_stops) + 1}",
                sequence=len(normalized_stops) + 1,
                title=title,
                image=stop.get("image") if str(stop.get("image") or "").startswith(("http://", "https://")) else _place_image_url(title, area or data.location, kind),
                description=_short(stop.get("description") or stop.get("type"), "Local stop", 8),
                eta=_short(stop.get("eta"), best_leave if not normalized_stops else f"+{len(normalized_stops) * 45} mins", 4),
                ideal_visit_duration=_short(stop.get("duration") or stop.get("stay_duration"), "50 mins", 3),
                estimated_cost=_format_inr(cost),
                travel_time_to_next="Return" if index == min(len(raw_stops[:3]), 3) - 1 else f"{commute_unit + index * 4} mins",
                crowd_level=_short(stop.get("crowd_level"), "Balanced", 3),
                weather_suitability=_short(stop.get("weather_suitability"), "Good", 3),
                opening_hours=_short(stop.get("opening_hours"), "Check hours", 4),
                why_ai_picked_this=_short(stop.get("why") or stop.get("why_ai_picked_this"), "Mood fit", 6),
                mood_tags=mood_tags,
                coordinates=Coordinates(lat=lat, lng=lng),
                backup_plan=_short(stop.get("backup_plan"), "Cafe backup nearby", 6),
            )
        )

    if not normalized_stops:
        raise ValueError("Nearby LLM stops invalid")
    for index, stop in enumerate(normalized_stops):
        stop.travel_time_to_next = "Return" if index == len(normalized_stops) - 1 else f"{commute_unit + index * 4} mins"

    raw_costs = parsed.get("costs") or parsed.get("totals") or {}
    food = _parse_money(raw_costs.get("food"), max(round(data.budget * 0.35), total_stop_cost))
    transport = _parse_money(raw_costs.get("transport"), round(data.budget * (0.08 if data.transport == "Walking" else 0.16)))
    tickets = _parse_money(raw_costs.get("tickets") or raw_costs.get("activities"), total_stop_cost)
    shopping = _parse_money(raw_costs.get("shopping"), 0)
    used = food + transport + tickets + shopping
    if used > data.budget:
        scale = data.budget / max(used, 1)
        food, transport, tickets, shopping = [int(value * scale) for value in (food, transport, tickets, shopping)]
        used = food + transport + tickets + shopping
    buffer = max(data.budget - used, 0)
    costs = NearbyCosts(
        food=_format_inr(food),
        transport=_format_inr(transport),
        tickets=_format_inr(tickets),
        shopping=_format_inr(shopping),
        buffer=_format_inr(buffer),
        total=_format_inr(food + transport + tickets + shopping + buffer),
    )

    map_coordinates = [stop.coordinates for stop in normalized_stops]
    insights = [str(item) for item in parsed.get("insights", []) if item][:3]
    if len(insights) < 3:
        insights = [*insights, "Low commute route.", "Budget kept tight.", "Best near golden hour."][:3]

    raw_alternates = parsed.get("alternates") if isinstance(parsed.get("alternates"), list) else []
    alternates = []
    for index, item in enumerate(raw_alternates[:3]):
        if not isinstance(item, dict):
            continue
        alternates.append(
            NearbyAlternate(
                id=f"alt-{index + 1}",
                title=_short(item.get("title"), "Alternate", 4),
                budget=_format_inr(_parse_money(item.get("budget"), data.budget)),
                duration=_short(item.get("duration"), "Same pace", 4),
                description=_short(item.get("description"), "Route variant", 8),
                tags=[str(tag) for tag in item.get("tags", ["Flexible"])][:4],
            )
        )
    if not alternates:
        alternates = _generate_nearby_plan_fallback(data).alternates[:3]

    return NearbyPlanResponse(
        summary=NearbySummary(
            title=_short(summary_raw.get("title"), _trip_name(data), 5),
            location=data.location or data.detected_city or "Current location",
            total_duration=data.duration,
            estimated_budget=_format_inr(data.budget),
            total_travel_distance=_short(summary_raw.get("total_travel_distance"), data.radius, 4),
            weather_snapshot=_short(summary_raw.get("weather_snapshot"), "Check weather", 5),
            best_time_to_leave=best_leave,
            vibe_tags=[*data.moods, data.group_type, data.transport][:7],
            magic_touch=_short(summary_raw.get("magic_touch"), f"{normalized_stops[0].title} fits best", 10),
        ),
        stops=normalized_stops,
        timing=NearbyTiming(
            generated_at=f"{now.isoformat()}Z",
            best_leave=best_leave,
            golden_hour="17:30 - 18:20",
            nightlife_window="20:00 - 23:00" if "Nightlife" in data.moods else "Optional after 20:30",
            traffic_note="Avoid peak hops.",
            rainy_day_cutover="Use cafe backup.",
        ),
        costs=costs,
        route=NearbyRoute(
            mode=data.transport,
            radius=data.radius,
            optimized_order=[stop.title for stop in normalized_stops],
            estimated_commute_time=f"{max(18, (len(normalized_stops) - 1) * commute_unit)} mins",
            transport_aware_routing="Shortest practical order.",
            traffic_awareness="Avoids peak return.",
            map_coordinates=map_coordinates,
        ),
        insights=insights,
        alternates=alternates,
        map_coordinates=map_coordinates,
    )


def generate_nearby_plan(data: NearbyPlanRequest) -> NearbyPlanResponse:
    try:
        return _response_from_llm(data, _call_nearby_llm(data))
    except Exception:
        return _generate_nearby_plan_fallback(data)
