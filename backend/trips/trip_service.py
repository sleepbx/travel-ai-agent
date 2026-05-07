from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.trips.trip_models import Trip, TripVersion


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
):
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
