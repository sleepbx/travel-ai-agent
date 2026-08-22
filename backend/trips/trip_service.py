from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import re
from typing import Any

from backend.trips.trip_models import Trip, TripVersion


def _safe_json(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value or "")
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _compact_text(value: Any, fallback: str = "") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, dict):
        text = value.get("text") or value.get("name") or value.get("title") or value.get("grand_total") or ""
    elif isinstance(value, list):
        text = ", ".join(_compact_text(item) for item in value[:3])
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120] if text else fallback


def _plan_snapshot(raw_itinerary: str) -> dict[str, Any]:
    parsed = _safe_json(raw_itinerary)
    if not parsed:
        return {
            "summary": _compact_text(raw_itinerary, "Text itinerary"),
            "transport": "",
            "hotel": "",
            "total": "",
            "day_titles": [],
        }

    hotels = parsed.get("hotels") if isinstance(parsed.get("hotels"), list) else []
    selected_hotel = parsed.get("selected_hotel") if isinstance(parsed.get("selected_hotel"), dict) else {}
    days = parsed.get("days") if isinstance(parsed.get("days"), list) else []
    summary = parsed.get("summary")

    return {
        "summary": _compact_text(summary, "Structured itinerary"),
        "transport": _compact_text(
            parsed.get("selected_transport")
            or parsed.get("selected_transport_mode")
            or parsed.get("transport_mode")
            or "",
        ),
        "hotel": _compact_text(selected_hotel or (hotels[0] if hotels else "")),
        "total": _compact_text((parsed.get("cost_summary") or {}).get("grand_total")),
        "day_titles": [
            _compact_text(day.get("title") or day.get("theme") or f"Day {index + 1}")
            for index, day in enumerate(days[:10])
            if isinstance(day, dict)
        ],
    }


def summarize_itinerary_changes(
    before_itinerary: str,
    after_itinerary: str,
    instruction: str | None = None,
) -> list[str]:
    before = _plan_snapshot(before_itinerary)
    after = _plan_snapshot(after_itinerary)
    changes: list[str] = []

    if before["summary"] != after["summary"]:
        changes.append(f"Overview changed to: {after['summary']}")
    if before["transport"] != after["transport"] and after["transport"]:
        changes.append(f"Transport changed to: {after['transport']}")
    if before["hotel"] != after["hotel"] and after["hotel"]:
        changes.append(f"Stay changed to: {after['hotel']}")
    if before["total"] != after["total"] and after["total"]:
        changes.append(f"Estimated total changed to: {after['total']}")

    before_days = before["day_titles"]
    after_days = after["day_titles"]
    if len(before_days) != len(after_days):
        changes.append(f"Day count changed from {len(before_days) or 'text'} to {len(after_days) or 'text'}.")
    else:
        changed_days = [
            f"Day {index + 1}: {title}"
            for index, title in enumerate(after_days)
            if index >= len(before_days) or before_days[index] != title
        ][:3]
        if changed_days:
            changes.append(f"Updated day themes: {'; '.join(changed_days)}")

    if not changes and instruction:
        changes.append(f"Applied request: {_compact_text(instruction)}")
    if not changes:
        changes.append("Restored itinerary content without detectable structural changes.")

    return changes[:5]


def create_trip(
    db: Session,
    user_id: str,
    title: str,
    destination: str,
    itinerary: str,
):
    trip = Trip(
        user_id=user_id,
        title=title,
        destination=destination,
        itinerary=itinerary,
    )

    db.add(trip)
    db.commit()
    db.refresh(trip)

    # Version 1
    version = TripVersion(
        trip_id=trip.id,
        version_number=1,
        itinerary=itinerary,
        instruction="Initial plan",
    )

    db.add(version)
    db.commit()

    return trip


def save_trip_version(
    db: Session,
    trip_id: str,
    itinerary: str,
    instruction: str,
) -> TripVersion:
    latest_version = (
        db.query(func.max(TripVersion.version_number))
        .filter(TripVersion.trip_id == trip_id)
        .scalar()
    ) or 0

    version = TripVersion(
        trip_id=trip_id,
        version_number=latest_version + 1,
        itinerary=itinerary,
        instruction=instruction,
    )

    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def get_user_trips(db: Session, user_id: str):
    return db.query(Trip).filter(Trip.user_id == user_id).all()


def get_trip_versions(db: Session, trip_id: str):
    return (
        db.query(TripVersion)
        .filter(TripVersion.trip_id == trip_id)
        .order_by(TripVersion.version_number)
        .all()
    )


def get_trip_version_by_number(
    db: Session,
    trip_id: str,
    version_number: int,
):
    return (
        db.query(TripVersion)
        .filter(
            TripVersion.trip_id == trip_id,
            TripVersion.version_number == version_number,
        )
        .first()
    )
