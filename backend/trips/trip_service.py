from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.trips.trip_models import Trip, TripVersion


def _add_version(
    db: Session,
    trip_id: str,
    itinerary: str,
    instruction: str,
) -> TripVersion:
    """Stage the next version of a trip in the current transaction (no commit)."""
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
    return version


def create_trip(
    db: Session,
    user_id: str,
    title: str,
    destination: str,
    itinerary: str,
):
    """Create a trip and its version 1 in one transaction."""
    trip = Trip(
        user_id=user_id,
        title=title,
        destination=destination,
        itinerary=itinerary,
    )
    db.add(trip)
    db.flush()  # assigns trip.id without committing

    db.add(
        TripVersion(
            trip_id=trip.id,
            version_number=1,
            itinerary=itinerary,
            instruction="Initial plan",
        )
    )
    db.commit()
    db.refresh(trip)
    return trip


def save_trip_version(
    db: Session,
    trip_id: str,
    itinerary: str,
    instruction: str,
) -> TripVersion:
    version = _add_version(db, trip_id, itinerary, instruction)
    db.commit()
    return version


def update_trip_itinerary(
    db: Session,
    trip: Trip,
    itinerary: str,
    instruction: str,
) -> TripVersion:
    """Replace a trip's itinerary and record the change as a new version.

    Both writes share one commit, so the trip and its version history can
    never disagree if the second write fails.
    """
    trip.itinerary = itinerary
    version = _add_version(db, trip.id, itinerary, instruction)
    db.commit()
    db.refresh(trip)
    return version


def rollback_trip(
    db: Session,
    trip: Trip,
    version_number: int,
) -> TripVersion | None:
    """Restore an earlier version. History is append-only: the rollback is
    itself saved as a new version. Returns None if the version doesn't exist."""
    target = get_trip_version_by_number(db, trip.id, version_number)
    if target is None:
        return None
    return update_trip_itinerary(
        db,
        trip,
        target.itinerary,
        f"Rollback to version {version_number}",
    )


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
