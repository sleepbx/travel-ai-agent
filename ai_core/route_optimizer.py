import os
import re
from typing import Any

from ai_core.zapi.maps_api import get_distance


ROUTE_MAPS_ENABLED = os.getenv("ROUTE_MAPS_ENABLED", "true").lower() not in {"0", "false", "no"}
ROUTE_MAPS_MAX_DAYS = max(int(os.getenv("ROUTE_MAPS_MAX_DAYS", "3")), 0)
ROUTE_MAPS_MAX_CALLS = max(int(os.getenv("ROUTE_MAPS_MAX_CALLS", "12")), 0)


def _place_label(activity: dict[str, Any], destination: str) -> str:
    title = str(activity.get("title") or "").strip()
    location = str(activity.get("location") or activity.get("area") or destination).strip()
    if title and location and location.lower() not in title.lower():
        return f"{title}, {location}"
    return title or location or destination


def _duration_minutes(value: Any) -> int | None:
    text = str(value or "").lower()
    if not text:
        return None
    hours = re.search(r"(\d+)\s*(?:hour|hr|h)", text)
    minutes = re.search(r"(\d+)\s*(?:minute|min|m)", text)
    total = (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)
    return total or None


def _estimated_leg(origin: str, destination: str) -> dict[str, Any]:
    return {
        "origin": origin,
        "destination": destination,
        "distance": "Estimate unavailable",
        "duration": "30-60 min estimate",
        "duration_minutes": 45,
        "source": "Route estimate",
        "confidence": "Low",
    }


def apply_distance_routes(plan: dict[str, Any], destination: str, hotel_name: str) -> dict[str, Any]:
    """
    Enrich adjacent itinerary legs without using the LLM.

    Maps calls are capped for predictable API usage. Remaining legs are explicit
    low-confidence estimates rather than being presented as live route data.
    """
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    call_count = 0
    live_leg_count = 0
    estimated_leg_count = 0

    for day_index, day in enumerate(days):
        if not isinstance(day, dict):
            continue
        activities = [item for item in day.get("activities", []) if isinstance(item, dict)]
        if not activities:
            continue

        base = str(hotel_name or destination).strip()
        stops = [base, *[_place_label(activity, destination) for activity in activities], base]
        legs = []

        for origin, target in zip(stops, stops[1:]):
            can_call_maps = (
                ROUTE_MAPS_ENABLED
                and day_index < ROUTE_MAPS_MAX_DAYS
                and call_count < ROUTE_MAPS_MAX_CALLS
            )
            result = get_distance(origin, target) if can_call_maps else {"error": "Maps call budget reached"}
            if can_call_maps:
                call_count += 1

            if result.get("distance") or result.get("duration"):
                leg = {
                    "origin": origin,
                    "destination": target,
                    "distance": result.get("distance") or "Distance unavailable",
                    "duration": result.get("duration") or "Duration unavailable",
                    "duration_minutes": _duration_minutes(result.get("duration")),
                    "source": result.get("provider") or "Maps distance API",
                    "confidence": "High",
                    "cached": bool(result.get("cached")),
                }
                live_leg_count += 1
            else:
                leg = _estimated_leg(origin, target)
                estimated_leg_count += 1
            legs.append(leg)

        live_minutes = sum(int(leg.get("duration_minutes") or 0) for leg in legs)
        day["route_plan"] = {
            "optimization": "clustered_adjacent_legs",
            "legs": legs,
            "total_duration_minutes": live_minutes,
            "source": "Maps distance API" if any(leg["confidence"] == "High" for leg in legs) else "Route estimates",
            "all_legs_live": all(leg["confidence"] == "High" for leg in legs),
        }

        existing = day.get("local_transport") if isinstance(day.get("local_transport"), dict) else {}
        day["local_transport"] = {
            **existing,
            "route": " -> ".join(stops),
            "duration": f"{live_minutes} min" if live_minutes else existing.get("duration", "30-60 min estimate"),
            "route_source": day["route_plan"]["source"],
        }
        if isinstance(day.get("transport"), dict):
            day["transport"]["route"] = day["local_transport"]["route"]

    plan["route_optimization"] = {
        "strategy": "clustered itinerary with adjacent-leg distance validation",
        "maps_calls": call_count,
        "live_legs": live_leg_count,
        "estimated_legs": estimated_leg_count,
        "max_days": ROUTE_MAPS_MAX_DAYS,
        "max_calls": ROUTE_MAPS_MAX_CALLS,
        "groq_calls_added": 0,
    }
    return plan
