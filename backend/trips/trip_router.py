from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.session import SessionLocal
from backend.core.security import get_current_user_id

from backend.trips.trip_models import Trip
from backend.trips.trip_service import (
    create_trip,
    get_user_trips,
    save_trip_version,
    get_trip_versions,
    get_trip_version_by_number,
)

from backend.ai_adapter.planner import (
    generate_trip_itinerary,
    refine_trip_itinerary,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


# ------------------ DB Dependency ------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------ Schemas ------------------

class CreateTripRequest(BaseModel):
    origin_city: str
    destination_city: str
    depart_date: str
    return_date: str
    passengers: int = 2
    cabin_class: str = "economy"
    transport_mode: str = "flight"
    interests: str = "sightseeing"
    max_budget: int | None = None


class RefineTripRequest(BaseModel):
    instruction: str


class RollbackTripRequest(BaseModel):
    version_number: int


# ------------------ Routes ------------------

@router.post("/create")
def create_trip_api(
    data: CreateTripRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    itinerary = generate_trip_itinerary(data)

    trip = create_trip(
        db=db,
        user_id=user_id,
        title=f"{data.destination_city} Trip",
        destination=data.destination_city,
        itinerary=itinerary,
    )

    return {
        "trip_id": trip.id,
        "message": "Trip created successfully",
        "itinerary_preview": itinerary[:400],
    }


@router.post("/{trip_id}/refine")
def refine_trip_api(
    trip_id: str,
    data: RefineTripRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    updated_itinerary = refine_trip_itinerary(
        existing_itinerary=trip.itinerary,
        user_request=data.instruction,
    )

    trip.itinerary = updated_itinerary
    db.commit()
    db.refresh(trip)

    # Save refinement as a new version.
    save_trip_version(
        db=db,
        trip_id=trip.id,
        itinerary=updated_itinerary,
        instruction=data.instruction,
    )

    return {
        "trip_id": trip.id,
        "message": "Trip refined successfully",
        "updated_itinerary": updated_itinerary,
    }


@router.post("/{trip_id}/rollback")
def rollback_trip_api(
    trip_id: str,
    data: RollbackTripRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    version = get_trip_version_by_number(
        db=db,
        trip_id=trip_id,
        version_number=data.version_number,
    )

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Roll back itinerary.
    trip.itinerary = version.itinerary
    db.commit()
    db.refresh(trip)

    # Save rollback as a new version.
    save_trip_version(
        db=db,
        trip_id=trip.id,
        itinerary=version.itinerary,
        instruction=f"Rollback to version {data.version_number}",
    )

    return {
        "trip_id": trip.id,
        "message": f"Rolled back to version {data.version_number}",
        "current_itinerary": trip.itinerary,
    }


@router.get("/my")
def my_trips(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_trips(db, user_id)


@router.get("/{trip_id}/versions")
def trip_versions(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    versions = get_trip_versions(db, trip_id)

    return [
        {
            "version": v.version_number,
            "instruction": v.instruction,
            "created_at": v.created_at,
        }
        for v in versions
    ]
