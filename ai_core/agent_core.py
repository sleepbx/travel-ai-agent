import json
import os
import re
import asyncio
from datetime import datetime
from difflib import get_close_matches
from typing import Any, Optional, TypedDict

from dotenv import load_dotenv
from groq import Groq

from ai_core.rag_documents import india_travel_docs
from ai_core.rag_engine import RAGEngine
from ai_core.trip_payload import (
    apply_budget_preferences,
    build_budget_profile,
    build_fallback_trip_plan,
    classify_entities,
    classify_entity,
    complete_trip_plan,
    destination_place_seed,
    extract_budget_constraints,
    normalize_flight_options,
    normalize_ground_transport_options,
    normalize_hotel_options,
    normalize_transport_mode,
    parse_price,
    recalculate_cost_summary,
)
from ai_core.zapi.flight_api import search_flights_serpapi
from ai_core.zapi.transport_api import search_ground_transport_options
from ai_core.zapi.hotel_api import search_hotels_serpapi
from ai_core.zapi.maps_api import (
    extract_google_attractions,
    extract_google_restaurants,
    search_google_places,
)
from ai_core.zapi.tools_weather import get_weather

try:
    from langgraph.graph import END, START, StateGraph
except Exception:
    END = START = StateGraph = None

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
PLANNER_MAX_TOKENS = int(os.getenv("PLANNER_MAX_TOKENS", "1600"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
JSON_COMPACT = os.getenv("JSON_COMPACT", "1").strip().lower() not in {"0", "false", "no"}

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
_rag_singleton: RAGEngine | None = None


class TripGraphState(TypedDict, total=False):
    origin_city: str
    destination_city: str
    depart_date: str
    return_date: str
    passengers: int
    cabin_class: str
    transport_mode: str
    interests: str
    max_budget: Optional[int]
    origin: str
    dest: str
    origin_airport: str
    dest_airport: str
    total_days: int
    weather: str
    flights: Any
    hotels: Any
    places_raw: Any
    restaurants: Any
    attractions: Any
    rag_context: Any
    live_context: Any
    quality_notes: str
    itinerary: str
    ground_transport: Any
    provider_context: Any
    clusters: Any
    budget_profile: Any
    destination_mode: str
    error: str


def call_groq(prompt: str, max_tokens: int = PLANNER_MAX_TOKENS) -> str:
    if groq_client is None:
        raise RuntimeError("GROQ_API_KEY missing")
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.32,
        max_tokens=max_tokens,
    )
    return res.choices[0].message.content.strip()


def call_groq_json(prompt: str, max_tokens: int = PLANNER_MAX_TOKENS) -> str:
    try:
        res = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.18,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return call_groq(prompt, max_tokens=max_tokens)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(cleaned[start : end + 1])
    except Exception:
        return None


def _json_dumps(value: Any) -> str:
    if JSON_COMPACT:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _slim_list(items: Any, keep: int, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    slim: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        slim.append({k: item.get(k) for k in keys if item.get(k) not in (None, "", [])})
        if len(slim) >= keep:
            break
    return slim


def _compact_text(value: Any, limit: int = 700) -> str:
    if not value:
        return ""
    text = _json_dumps(value) if isinstance(value, (dict, list)) else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _price_int(value: Any) -> int | None:
    return parse_price(value)


def _short_words(value: Any, limit: int = 5) -> str:
    words = re.sub(r"\s+", " ", str(value or "").strip()).split()
    return " ".join(words[:limit])


def _area_from_place(item: dict[str, Any], fallback: str = "") -> str:
    raw = str(item.get("area") or item.get("address") or item.get("location") or fallback or "").strip()
    if not raw:
        return fallback.title() if fallback else ""
    parts = [part.strip() for part in re.split(r"[,|-]", raw) if part.strip()]
    return _short_words(parts[0] if parts else raw, 3)


def _cluster_places(attractions: list[dict[str, Any]], restaurants: list[dict[str, Any]]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for item in [*attractions, *restaurants]:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("title") or item.get("hotel")
        if not name:
            continue
        area = _area_from_place(item, "Central")
        clusters.setdefault(area or "Central", [])
        if len(clusters[area or "Central"]) < 5:
            clusters[area or "Central"].append(_short_words(name, 4))
    return dict(list(clusters.items())[:5])


def _destination_mode(destination: Any) -> str:
    text = str(destination or "").lower()
    if any(name in text for name in ("goa", "puducherry", "pondicherry", "bali")):
        return "coastal_relaxed"
    if any(name in text for name in ("delhi", "agra", "jaipur", "varanasi")):
        return "urban_heritage"
    if "hyderabad" in text:
        return "food_culture"
    if any(name in text for name in ("bangalore", "bengaluru", "pune")):
        return "cafe_worklife"
    if any(name in text for name in ("mumbai", "kolkata", "chennai")):
        return "metro_culture"
    return "balanced_city"


DESTINATION_MODE_RULES = {
    "coastal_relaxed": "slow mornings,sunset,shacks,scooter,cabs costly",
    "urban_heritage": "early landmarks,metro,heat-smart afternoons",
    "food_culture": "food clusters,old city pacing,cafe evenings",
    "cafe_worklife": "traffic-aware,cafes,brewery evenings",
    "metro_culture": "metro/taxi mix,early icons,evening food",
    "balanced_city": "clustered routing,local food,light evenings",
}


def _compact_source_payload(state: TripGraphState) -> dict[str, Any]:
    # Keep Groq context small for free-tier limits.
    flights = state.get("flights", {})
    hotels = state.get("hotels", {})
    ground = state.get("ground_transport", {})
    seed = destination_place_seed(state.get("dest", ""))
    restaurants = state.get("restaurants", []) if isinstance(state.get("restaurants"), list) else []
    attractions = state.get("attractions", []) if isinstance(state.get("attractions"), list) else []
    if len(restaurants) < 3:
        restaurants = [*restaurants, *seed.get("restaurants", [])]
    if len(attractions) < 6:
        attractions = [*attractions, *seed.get("attractions", [])]
    return {
        "destination": str(state.get("dest", "")).title(),
        "budget": state.get("max_budget") or 0,
        "weather": _compact_text(state.get("weather", ""), 80),
        "destination_mode": state.get("destination_mode") or _destination_mode(state.get("dest", "")),
        "flights": _slim_list(
            flights.get("flights", []) if isinstance(flights, dict) else (flights if isinstance(flights, list) else []),
            2,
            ("airline", "from", "to", "departure", "arrival", "duration", "price_per_person", "price"),
        ),
        "hotels": _slim_list(
            hotels.get("hotels", []) if isinstance(hotels, dict) else (hotels if isinstance(hotels, list) else []),
            2,
            ("name", "area", "address", "rating", "price", "price_per_night"),
        ),
        "restaurants": _slim_list(
            restaurants,
            6,
            ("name", "address", "rating", "price_level", "entity_type"),
        ),
        "attractions": _slim_list(
            attractions,
            8,
            ("name", "address", "category", "rating", "entity_type"),
        ),
        "ground_transport": ground if isinstance(ground, dict) else {},
        "clusters": state.get("clusters", {}),
        "rag": state.get("rag_context", []),
        "budget_profile": state.get("budget_profile", {}),
    }


def _compress_provider_payload(state: TripGraphState) -> dict[str, Any]:
    payload = _compact_source_payload(state)
    payload["flights"] = [
        {
            "airline": _short_words(item.get("airline") or "Flight", 3),
            "from": item.get("from", ""),
            "to": item.get("to", ""),
            "departure": _short_words(item.get("departure"), 4),
            "price": _price_int(item.get("price_per_person") or item.get("price")) or item.get("price"),
        }
        for item in payload.get("flights", [])[:2]
    ]
    payload["hotels"] = [
        {
            "name": _short_words(item.get("name"), 4),
            "price": _price_int(item.get("price_per_night") or item.get("price")) or item.get("price"),
            "area": _area_from_place(item, state.get("dest", "")),
        }
        for item in payload.get("hotels", [])[:2]
    ]
    payload["restaurants"] = [
        {
            "name": _short_words(item.get("name"), 4),
            "area": _area_from_place(item, state.get("dest", "")),
            "specialty": _short_words(item.get("price_level") or "Local", 3),
            "type": item.get("entity_type") or "restaurant",
        }
        for item in payload.get("restaurants", [])[:6]
    ]
    payload["attractions"] = [
        {
            "name": _short_words(item.get("name"), 4),
            "area": _area_from_place(item, state.get("dest", "")),
            "type": item.get("entity_type") or classify_entity(item),
        }
        for item in payload.get("attractions", [])[:8]
    ]
    ground = payload.get("ground_transport") if isinstance(payload.get("ground_transport"), dict) else {}
    payload["transport_estimates"] = {
        "train": _slim_list(ground.get("train", {}).get("options", []), 2, ("mode", "route", "duration", "price_per_person", "total_price")),
        "bus": _slim_list(ground.get("bus", {}).get("options", []), 2, ("mode", "route", "duration", "price_per_person", "total_price")),
    }
    payload.pop("ground_transport", None)
    return payload


def _compress_rag_results(results: list[Any], provider_context: dict[str, Any]) -> list[str]:
    place_names = {
        str(item.get("name") or item.get("hotel") or "").lower()
        for key in ("attractions", "restaurants", "hotels")
        for item in provider_context.get(key, [])
        if isinstance(item, dict)
    }
    insights: list[str] = []
    seen: set[str] = set()
    for result in results[:10]:
        text = getattr(result, "text", result.get("text", "") if isinstance(result, dict) else "")
        sentences = re.split(r"(?<=[.!?])\s+|[\n;]+", str(text))
        for sentence in sentences:
            cleaned = re.sub(r"\s+", " ", sentence).strip(" -•")
            if len(cleaned) < 12:
                continue
            lower = cleaned.lower()
            if place_names and not any(name and name in lower for name in place_names):
                if not any(term in lower for term in ("metro", "crowd", "traffic", "timing", "walk", "market", "local", "early")):
                    continue
            compact = _short_words(cleaned, 8)
            key = compact.lower()
            if key in seen:
                continue
            insights.append(compact)
            seen.add(key)
            if len(insights) >= 5:
                return insights
    return insights


def get_rag_engine() -> RAGEngine:
    global _rag_singleton

    if _rag_singleton is None:
        _rag_singleton = RAGEngine()
        _rag_singleton.load_docs(india_travel_docs)
        _rag_singleton.load_pdfs_from_folder()

    return _rag_singleton


class LocationResolver:
    CITY_TO_IATA = {
        "hyderabad": "HYD",
        "delhi": "DEL",
        "mumbai": "BOM",
        "bangalore": "BLR",
        "chennai": "MAA",
        "kolkata": "CCU",
        "goa": "GOI",
        "kochi": "COK",
        "jaipur": "JAI",
        "visakhapatnam": "VTZ",
        "pune": "PNQ",
        "ahmedabad": "AMD",
        "lucknow": "LKO",
        "chandigarh": "IXC",
        "amritsar": "ATQ",
        "varanasi": "VNS",
        "agra": "AGR",
        "udaipur": "UDR",
        "jodhpur": "JDH",
        "srinagar": "SXR",
        "leh": "IXL",
        "dehradun": "DED",
        "bhubaneswar": "BBI",
        "guwahati": "GAU",
        "patna": "PAT",
        "ranchi": "IXR",
        "raipur": "RPR",
        "indore": "IDR",
        "bhopal": "BHO",
        "nagpur": "NAG",
        "surat": "STV",
        "vadodara": "BDQ",
        "coimbatore": "CJB",
        "madurai": "IXM",
        "mangalore": "IXE",
        "mysore": "MYQ",
        "vijayawada": "VGA",
        "tirupati": "TIR",
        "port blair": "IXZ",
        "singapore": "SIN",
        "dubai": "DXB",
        "abu dhabi": "AUH",
        "bangkok": "BKK",
        "bali": "DPS",
        "paris": "CDG",
        "london": "LHR",
        "new york": "JFK",
    }

    STATE_TO_CITY = {
        "telangana": "hyderabad",
        "andhra pradesh": "visakhapatnam",
        "tamil nadu": "chennai",
        "karnataka": "bangalore",
        "kerala": "kochi",
        "maharashtra": "mumbai",
        "rajasthan": "jaipur",
        "west bengal": "kolkata",
        "goa": "goa",
        "delhi": "delhi",
    }

    ALIASES = {
        "hyd": "hyderabad",
        "blr": "bangalore",
        "bengaluru": "bangalore",
        "bom": "mumbai",
        "mum": "mumbai",
        "del": "delhi",
        "maa": "chennai",
        "vizag": "visakhapatnam",
        "benaras": "varanasi",
        "banaras": "varanasi",
        "pondicherry": "puducherry",
        "manali": "kullu",
        "darjeeling": "bagdogra",
        "ooty": "coimbatore",
    }

    @classmethod
    def resolve(cls, text: str) -> str:
        t = re.sub(r"\s+", " ", text.strip().lower())

        if t in cls.ALIASES:
            return cls.ALIASES[t]
        if t in cls.CITY_TO_IATA:
            return t
        if t in cls.STATE_TO_CITY:
            return cls.STATE_TO_CITY[t]

        match = get_close_matches(t, cls.CITY_TO_IATA.keys(), n=1, cutoff=0.75)
        if match:
            return match[0]

        return t

    @classmethod
    def iata_for(cls, city: str) -> str:
        return cls.CITY_TO_IATA.get(city, "")


class TravelAI:
    def __init__(self):
        self.rag = get_rag_engine()
        self.resolver = LocationResolver()
        self.graph = self._build_graph()

    def _days(self, start_date: str, end_date: str) -> int:
        days = (
            datetime.strptime(end_date, "%Y-%m-%d")
            - datetime.strptime(start_date, "%Y-%m-%d")
        ).days + 1
        return max(1, min(days, 10))

    def _resolve_node(self, state: TripGraphState) -> TripGraphState:
        try:
            origin = self.resolver.resolve(state["origin_city"])
            dest = self.resolver.resolve(state["destination_city"])
            return {
                "origin": origin,
                "dest": dest,
                "origin_airport": self.resolver.iata_for(origin),
                "dest_airport": self.resolver.iata_for(dest),
                "total_days": self._days(state["depart_date"], state["return_date"]),
                "destination_mode": _destination_mode(dest),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _retrieve_node(self, state: TripGraphState) -> TripGraphState:
        if state.get("error"):
            return {}

        dest = state["dest"]
        provider_context = state.get("provider_context") or _compress_provider_payload(state)
        names = []
        for key in ("attractions", "restaurants", "hotels"):
            names.extend(
                item.get("name") or item.get("hotel")
                for item in provider_context.get(key, [])
                if isinstance(item, dict)
            )
        cluster_terms = " ".join(provider_context.get("clusters", {}).keys()) if isinstance(provider_context.get("clusters"), dict) else ""
        query = (
            f"{dest} {' '.join(str(name) for name in names[:12] if name)} "
            f"{cluster_terms} timing crowd metro local transport pacing hidden gems"
        )
        rag_results = self.rag.retrieve(query, top_k=5, state=None)
        rag_context = _compress_rag_results(rag_results, provider_context)

        return {
            "rag_context": rag_context,
        }

    async def _supplier_node_async(self, state: TripGraphState) -> TripGraphState:
        if state.get("error"):
            return {}

        budget_profile = build_budget_profile(
            int(state.get("total_days") or 1),
            int(state.get("passengers") or 2),
            state.get("cabin_class", "economy"),
            max_budget=state.get("max_budget"),
            transport_mode=state.get("transport_mode", "flight"),
        )
        selected_transport_mode = normalize_transport_mode(state.get("transport_mode"))

        async def fetch_flights():
            if not state.get("origin_airport") or not state.get("dest_airport"):
                return {"error": "Airport code unavailable", "flights": []}
            return await asyncio.to_thread(
                search_flights_serpapi,
                origin_airport=state["origin_airport"],
                destination_airport=state["dest_airport"],
                depart_date=state["depart_date"],
                return_date=state["return_date"],
                passengers=state.get("passengers", 2),
                cabin_class=state.get("cabin_class", "economy"),
                max_price=budget_profile.get("target_flight_per_person"),
                max_results=2,
            )

        async def fetch_hotels():
            return await asyncio.to_thread(
                search_hotels_serpapi,
                city=state["dest"],
                checkin=state["depart_date"],
                checkout=state["return_date"],
                adults=state.get("passengers", 2),
                rooms=1,
                max_price=budget_profile.get("target_hotel_per_night"),
                max_results=2,
            )

        async def fetch_restaurants():
            return await asyncio.to_thread(
                search_google_places,
                city=state["dest"],
                query_type=f"{state.get('interests', '')} restaurants",
                max_results=8,
            )

        async def fetch_attractions():
            return await asyncio.to_thread(
                search_google_places,
                city=state["dest"],
                query_type=f"{state.get('interests', 'sightseeing')} attractions",
                max_results=10,
            )

        async def fetch_weather():
            return await asyncio.to_thread(get_weather, state["dest"])

        async def fetch_ground_transport():
            return await asyncio.to_thread(
                search_ground_transport_options,
                origin_city=state["origin"],
                destination_city=state["dest"],
                depart_date=state["depart_date"],
                passengers=state.get("passengers", 2),
                selected_mode=selected_transport_mode,
                max_price=budget_profile.get("target_transport_per_person"),
            )

        (
            flights_result,
            hotels_result,
            restaurants_raw,
            attractions_raw,
            weather_result,
            ground_transport_result,
        ) = await asyncio.gather(
            fetch_flights(),
            fetch_hotels(),
            fetch_restaurants(),
            fetch_attractions(),
            fetch_weather(),
            fetch_ground_transport(),
        )

        restaurants = classify_entities(extract_google_restaurants(restaurants_raw, max_items=8), "restaurant")
        attractions = classify_entities(extract_google_attractions(attractions_raw, max_items=10))
        seed = destination_place_seed(state.get("dest", ""))
        restaurants = [*restaurants, *classify_entities(seed.get("restaurants", []), "restaurant")][:8]
        attractions = [*attractions, *classify_entities(seed.get("attractions", []))][:10]
        clusters = _cluster_places(attractions, restaurants)

        next_state = {
            "weather": weather_result,
            "flights": flights_result,
            "ground_transport": ground_transport_result,
            "hotels": hotels_result,
            "places_raw": {},
            "restaurants": restaurants,
            "attractions": attractions,
            "clusters": clusters,
            "destination_mode": state.get("destination_mode") or _destination_mode(state.get("dest", "")),
            "budget_profile": {
                "daily": budget_profile.get("target_daily_total"),
                "hotel_night": budget_profile.get("target_hotel_per_night"),
                "transport_pp": budget_profile.get("target_transport_per_person"),
                "flight_pp": budget_profile.get("target_flight_per_person"),
            },
        }
        next_state["provider_context"] = _compress_provider_payload({**state, **next_state})
        return next_state

    def _supplier_node(self, state: TripGraphState) -> TripGraphState:
        return asyncio.run(self._supplier_node_async(state))

    def _quality_node(self, state: TripGraphState) -> TripGraphState:
        if state.get("error"):
            return {}

        missing = []
        for key in ("rag_context", "flights", "ground_transport", "hotels", "restaurants", "weather"):
            value = state.get(key)
            if not value:
                missing.append(key)
                continue
            if isinstance(value, dict) and (
                value.get("error") or value.get("status") in {"disabled", "unavailable", "empty_query"}
            ):
                missing.append(key)

        notes = [
            "APIs finished before RAG.",
            "Use compressed provider facts.",
            "Python owns all budget math.",
        ]
        if missing:
            notes.append(f"Data gaps detected: {', '.join(missing)}.")

        return {"quality_notes": "\n".join(f"- {note}" for note in notes)}

    def _generate_node(self, state: TripGraphState) -> TripGraphState:
        if state.get("error"):
            fallback = build_fallback_trip_plan(state, {}, state["error"])
            return {"itinerary": _json_dumps(fallback)}

        source_payload = state.get("provider_context") or _compress_provider_payload(state)
        source_payload["rag"] = state.get("rag_context", [])[:5]
        source_payload["clusters"] = state.get("clusters", {})
        source_payload["destination_mode"] = state.get("destination_mode") or _destination_mode(state.get("dest", ""))
        source_payload["mode_rules"] = DESTINATION_MODE_RULES.get(source_payload["destination_mode"], DESTINATION_MODE_RULES["balanced_city"])

        prompt = f"""
TravelAI JSON only. Compact. No markdown.
Trip={{"from":"{state['origin'].title()}","to":"{state['dest'].title()}","dates":"{state['depart_date']}->{state['return_date']}","days":{state['total_days']},"pax":{state.get('passengers', 2)},"cabin":"{state.get('cabin_class', 'economy')}","mode":"{normalize_transport_mode(state.get('transport_mode'))}","interests":"{state.get('interests', 'sightseeing')}","budget":{state.get('max_budget') or 0}}}
Src={_json_dumps(source_payload)}
Return compact JSON:
{{"schema_version":"travelai_v11","pipeline":{{"providers_completed":true,"rag_completed":true,"compression_completed":true,"budget_optimized":true}},"destination_mode":"{source_payload['destination_mode']}","source_confidence":"medium","summary":{{"text":"","days":{state['total_days']},"budget":{state.get('max_budget') or 0}}},"selected_transport":{{}},"selected_hotel":{{}},"days":[],"cost_summary":{{}},"budget_guardrails":{{}},"ai_insights":[]}}
Rules:
- exact {state['total_days']} days.
- each day has morning, afternoon, evening activity; breakfast,lunch,dinner; local transport; daily total.
- day keys: day,theme,daily_total,activities,food,transport,stay_cost.
- activity={{"time":"morning","title":"Charminar","area":"Old City","cost":400}}
- food={{"breakfast":{{"meal":"breakfast","place":"Hotel cafe","specialty":"Idli","cost":250}},"lunch":{{"meal":"lunch","place":"Shah Ghouse","specialty":"Biryani","cost":550}},"dinner":{{"meal":"dinner","place":"Local grill","specialty":"Kebab","cost":700}}}}
- transport={{"mode":"Metro","route":"Hotel->Old City","cost":120}}
- activities exactly 3 slots: morning, afternoon, evening.
- food exactly breakfast,lunch,dinner.
- descriptions max 6 words; titles max 5 words.
- apply Src.destination_mode and Src.mode_rules.
- classify every entity by Src.*.type/entity_type.
- never place restaurant,café,hotel as landmark.
- restaurants only inside food.
- morning types: landmark,fort,heritage,viewpoint,park.
- afternoon types: museum,market,shopping,café,cultural area.
- evening types: sunset,food,nightlife,scenic walk,café.
- use clusters to avoid zig-zag.
- no repeated activity or meal names.
- vary activity, food, transport costs daily.
- provider/RAG first; fallback only missing fields.
- max 1-2 fallback entities/day.
- reject: LLM fill, Timing TBA, Local attraction, Popular restaurant, Viewpoint stop.
- never output Area walk/Market stop/Dinner walk.
- include 1-2 flights,trains,buses,hotels.
- cheapest practical {normalize_transport_mode(state.get('transport_mode'))}; economy default.
- LLM does no math; use given costs.
- INR numbers when possible.
- under 2500 output tokens.
"""
        try:
            raw = call_groq_json(prompt)
            parsed = _extract_json_object(raw)
        except Exception as exc:
            fallback = build_fallback_trip_plan(state, source_payload, f"AI generation unavailable: {exc}")
            return {"itinerary": _json_dumps(fallback)}

        if parsed:
            parsed = complete_trip_plan(parsed, state, source_payload)
            return {"itinerary": _json_dumps(parsed)}

        fallback = build_fallback_trip_plan(state, source_payload, "AI returned non-JSON output")
        fallback["legacy_text"] = raw
        return {"itinerary": _json_dumps(fallback)}

    def _build_graph(self):
        if StateGraph is None:
            return None

        try:
            graph = StateGraph(TripGraphState)
            graph.add_node("resolve", self._resolve_node)
            graph.add_node("suppliers", self._supplier_node)
            graph.add_node("retrieve", self._retrieve_node)
            graph.add_node("quality", self._quality_node)
            graph.add_node("generate", self._generate_node)

            graph.add_edge(START, "resolve")
            graph.add_edge("resolve", "suppliers")
            graph.add_edge("suppliers", "retrieve")
            graph.add_edge("retrieve", "quality")
            graph.add_edge("quality", "generate")
            graph.add_edge("generate", END)
            return graph.compile()
        except Exception:
            return None

    def _run_graph_fallback(self, state: TripGraphState) -> TripGraphState:
        state.update(self._resolve_node(state))
        state.update(self._supplier_node(state))
        state.update(self._retrieve_node(state))
        state.update(self._quality_node(state))
        state.update(self._generate_node(state))
        return state

    def _refresh_supplier_prices_for_refinement(
        self,
        plan: dict[str, Any],
        user_request: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        request = (user_request or "").lower()
        mentions_flights = bool(re.search(r"\b(flight|flights|fare|fares|airline|plane)\b", request))
        mentions_train = bool(re.search(r"\b(train|trains|rail|railway)\b", request))
        mentions_bus = bool(re.search(r"\b(bus|buses|coach)\b", request))
        mentions_hotels = bool(re.search(r"\b(hotel|hotels|stay|stays|room|rooms|night|nightly)\b", request))
        price_intent = bool(
            re.search(
                r"\b(price|prices|rate|rates|cost|budget|cheap|cheaper|lower|reduce|under|below|within|latest|current|refresh|available)\b",
                request,
            )
        )

        if mentions_flights or mentions_hotels or mentions_train or mentions_bus:
            wants_flights = mentions_flights
            wants_ground = mentions_train or mentions_bus
            wants_hotels = mentions_hotels
        else:
            wants_flights = price_intent
            wants_ground = price_intent
            wants_hotels = price_intent

        if not wants_flights and not wants_ground and not wants_hotels:
            return plan, {}

        date_range = plan.get("date_range") if isinstance(plan.get("date_range"), dict) else {}
        depart_date = date_range.get("start")
        return_date = date_range.get("end") or depart_date

        if not depart_date or not return_date:
            return plan, {
                "status": "skipped",
                "reason": "Saved itinerary is missing dates needed for live supplier refresh.",
            }

        origin = self.resolver.resolve(str(plan.get("origin") or ""))
        dest = self.resolver.resolve(str(plan.get("destination") or ""))
        origin_airport = self.resolver.iata_for(origin)
        dest_airport = self.resolver.iata_for(dest)
        total_days = int(date_range.get("total_days") or len(plan.get("days") or []) or 1)
        travelers = int(plan.get("travelers") or 2)
        cabin_class = plan.get("cabin_class") or "economy"
        selected_transport_mode = normalize_transport_mode(plan.get("selected_transport_mode"))
        if mentions_train:
            selected_transport_mode = "train"
            plan["selected_transport_mode"] = "train"
        elif mentions_bus:
            selected_transport_mode = "bus"
            plan["selected_transport_mode"] = "bus"
        current_total = parse_price(plan.get("cost_summary", {}).get("grand_total")) if isinstance(plan.get("cost_summary"), dict) else None
        guardrail_total = (
            parse_price(plan.get("budget_guardrails", {}).get("target_total"))
            if isinstance(plan.get("budget_guardrails"), dict)
            else None
        )
        near_budget_request = bool(
            re.search(r"\b(near|close to|around|within|keep|stay near|match)\b.{0,24}\bbudget\b", request)
            or re.search(r"\bbudget\b.{0,24}\b(near|close|around|matched|aligned)\b", request)
        )
        budget_anchor = (guardrail_total or current_total) if near_budget_request else (current_total or guardrail_total)
        constraints = extract_budget_constraints(user_request, current_total=budget_anchor)
        target_total = constraints.get("target_total") or guardrail_total
        budget_profile = build_budget_profile(
            total_days,
            travelers,
            cabin_class,
            max_budget=target_total,
            transport_mode=selected_transport_mode,
        )
        target_flight_per_person = constraints.get("target_flight") or budget_profile.get("target_flight_per_person")
        explicit_transport_target = constraints.get("target_transport")
        target_transport = explicit_transport_target or budget_profile.get("target_transport_total")
        target_transport_per_person = (
            explicit_transport_target
            if explicit_transport_target
            else max(int(target_transport / max(travelers, 1)), 1)
            if target_transport
            else budget_profile.get("target_transport_per_person")
        )
        target_hotel = constraints.get("target_hotel_nightly") or budget_profile.get("target_hotel_per_night")

        refresh_context: dict[str, Any] = {
            "status": "attempted",
            "requested": user_request,
            "refreshed": [],
            "warnings": [],
        }

        if wants_flights:
            if origin_airport and dest_airport:
                flights_result = search_flights_serpapi(
                    origin_airport=origin_airport,
                    destination_airport=dest_airport,
                    depart_date=depart_date,
                    return_date=return_date,
                    passengers=travelers,
                    cabin_class=cabin_class,
                    max_price=target_flight_per_person,
                    max_results=8,
                )
                plan["flights"] = normalize_flight_options(
                    flights_result,
                    origin.title(),
                    dest.title(),
                    origin_airport,
                    dest_airport,
                    travelers,
                    cabin_class,
                    target_per_person=target_flight_per_person,
                    max_per_person=target_flight_per_person if (target_total or constraints.get("target_flight")) else None,
                )
                refresh_context["refreshed"].append(
                    {
                        "type": "flights",
                        "pricing_mode": flights_result.get("pricing_mode") if isinstance(flights_result, dict) else "live",
                        "provider": flights_result.get("provider") if isinstance(flights_result, dict) else "SerpAPI",
                    }
                )
            else:
                refresh_context["warnings"].append("Airport code unavailable, so flights stayed as budget-aligned estimates.")

        if wants_ground:
            ground_result = search_ground_transport_options(
                origin_city=origin.title(),
                destination_city=dest.title(),
                depart_date=depart_date,
                passengers=travelers,
                selected_mode=selected_transport_mode,
                max_price=target_transport_per_person,
            )
            plan["trains"] = normalize_ground_transport_options(
                ground_result,
                "train",
                origin.title(),
                dest.title(),
                travelers,
                target_per_person=budget_profile.get("target_train_per_person"),
                max_per_person=target_transport_per_person if selected_transport_mode == "train" else None,
            )
            plan["buses"] = normalize_ground_transport_options(
                ground_result,
                "bus",
                origin.title(),
                dest.title(),
                travelers,
                target_per_person=budget_profile.get("target_bus_per_person"),
                max_per_person=target_transport_per_person if selected_transport_mode == "bus" else None,
            )
            plan["transport_options"] = {
                "flight": plan.get("flights", []),
                "train": plan.get("trains", []),
                "bus": plan.get("buses", []),
            }
            refresh_context["refreshed"].append(
                {
                    "type": "ground_transport",
                    "selected_mode": selected_transport_mode,
                    "provider": ground_result.get("provider", "search"),
                }
            )

        if wants_hotels:
            hotels_result = search_hotels_serpapi(
                city=dest,
                checkin=depart_date,
                checkout=return_date,
                adults=travelers,
                rooms=1,
                max_price=target_hotel,
                max_results=8,
            )
            plan["hotels"] = normalize_hotel_options(
                hotels_result,
                dest.title(),
                total_days=total_days,
                travelers=travelers,
                cabin_class=cabin_class,
                target_nightly=target_hotel,
                max_nightly=target_hotel if (target_total or constraints.get("target_hotel_nightly")) else None,
            )
            refresh_context["refreshed"].append(
                {
                    "type": "hotels",
                    "pricing_mode": hotels_result.get("pricing_mode") if isinstance(hotels_result, dict) else "live",
                    "provider": hotels_result.get("provider") if isinstance(hotels_result, dict) else "SerpAPI",
                }
            )

        sources = plan.get("sources") if isinstance(plan.get("sources"), list) else []
        sources = [
            {
                "name": "Supplier refresh",
                "confidence": "Medium",
                "note": "Refinement refreshed live supplier data or online estimates, then kept prices near the user's budget.",
            },
            *sources,
        ][:6]
        plan["sources"] = sources
        plan["supplier_refresh"] = refresh_context
        recalculate_cost_summary(
            plan,
            "Supplier rates were refreshed for this refinement where possible. Live fares and room rates can still change before checkout.",
        )
        return apply_budget_preferences(plan, user_request=user_request, source="refine"), refresh_context

    def plan_full_trip(
        self,
        origin_city: str,
        destination_city: str,
        depart_date: str,
        return_date: str,
        passengers: int = 2,
        cabin_class: str = "economy",
        transport_mode: str = "flight",
        interests: str = "sightseeing",
        max_budget: Optional[int] = None,
    ) -> str:
        initial_state: TripGraphState = {
            "origin_city": origin_city,
            "destination_city": destination_city,
            "depart_date": depart_date,
            "return_date": return_date,
            "passengers": passengers,
            "cabin_class": cabin_class,
            "transport_mode": normalize_transport_mode(transport_mode),
            "interests": interests,
            "max_budget": max_budget,
        }

        try:
            if self.graph is not None:
                final_state = self.graph.invoke(initial_state)
            else:
                final_state = self._run_graph_fallback(initial_state)
        except Exception as exc:
            state = dict(initial_state)
            state.update(
                {
                    "origin": origin_city.strip().lower(),
                    "dest": destination_city.strip().lower(),
                    "origin_airport": "",
                    "dest_airport": "",
                    "total_days": self._days(depart_date, return_date),
                    "transport_mode": normalize_transport_mode(transport_mode),
                }
            )
            fallback = build_fallback_trip_plan(state, {}, f"Planning pipeline recovered from: {exc}")
            return _json_dumps(fallback)

        return final_state.get("itinerary") or final_state.get("error") or "Unable to generate itinerary."

    def refine_itinerary(self, existing_itinerary: str, user_request: str) -> str:
        parsed_existing = _extract_json_object(existing_itinerary)
        refreshed_context: dict[str, Any] = {}
        itinerary_for_prompt = existing_itinerary

        if parsed_existing:
            parsed_existing, refreshed_context = self._refresh_supplier_prices_for_refinement(
                parsed_existing,
                user_request,
            )
            itinerary_for_prompt = _json_dumps(parsed_existing)

        prompt = f"""
TravelAI JSON editor. Compact output only.
Current={itinerary_for_prompt}
User={user_request}
Fresh={_json_dumps(refreshed_context)}
Rules:
- preserve travelai_v11 shape.
- edit only requested fields.
- price/transport requests are hard constraints.
- each day keeps 3 activities: Morning, Afternoon, Night.
- each day keeps Breakfast, Lunch, Dinner.
- keep flights,trains,buses,hotels,cost_summary.
- fares are per person; totals multiply pax.
- uncertain prices = estimate/target range.
- short strings, no markdown.
JSON:
"""
        try:
            raw = call_groq_json(prompt)
            parsed = _extract_json_object(raw)
            if parsed:
                parsed.setdefault("schema_version", "travelai_v11")
                parsed = apply_budget_preferences(parsed, user_request=user_request, source="refine")
                return _json_dumps(parsed)
            if parsed_existing:
                parsed_existing.setdefault("schema_version", "travelai_v11")
                parsed_existing = apply_budget_preferences(parsed_existing, user_request=user_request, source="refine")
                parsed_existing["refinement_note"] = "Deterministic budget guardrails applied."
                return _json_dumps(parsed_existing)
            return raw
        except Exception:
            if parsed_existing:
                parsed_existing.setdefault("schema_version", "travelai_v11")
                parsed_existing = apply_budget_preferences(parsed_existing, user_request=user_request, source="refine")
                parsed_existing.setdefault(
                    "booking_tips",
                    ["Refine unavailable; plan kept."],
                )
                return _json_dumps(parsed_existing)
            return existing_itinerary
