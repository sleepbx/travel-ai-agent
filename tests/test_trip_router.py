import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.security import get_current_user_id
from backend.trips import trip_router
from backend.trips.trip_service import create_trip


@pytest.fixture()
def client(db_session):
    app = FastAPI()
    app.include_router(trip_router.router)
    app.dependency_overrides[trip_router.get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    return TestClient(app)


def _trip(db, user_id="user-1"):
    return create_trip(db, user_id=user_id, title="Goa Trip", destination="Goa", itinerary="v1 plan")


def test_refine_updates_trip_and_records_version(client, db_session):
    trip = _trip(db_session)

    res = client.post(f"/trips/{trip.id}/refine", json={"instruction": "make it cheaper"})

    assert res.status_code == 200
    assert res.json()["updated_itinerary"] == "v1 plan | make it cheaper"
    versions = client.get(f"/trips/{trip.id}/versions").json()
    assert [(v["version"], v["instruction"]) for v in versions] == [(1, "Initial plan"), (2, "make it cheaper")]


def test_rollback_endpoint_restores_version(client, db_session):
    trip = _trip(db_session)
    client.post(f"/trips/{trip.id}/refine", json={"instruction": "make it cheaper"})

    res = client.post(f"/trips/{trip.id}/rollback", json={"version_number": 1})

    assert res.status_code == 200
    assert res.json()["current_itinerary"] == "v1 plan"
    assert client.get(f"/trips/{trip.id}/versions").json()[-1]["instruction"] == "Rollback to version 1"


def test_rollback_to_unknown_version_is_404(client, db_session):
    trip = _trip(db_session)

    res = client.post(f"/trips/{trip.id}/rollback", json={"version_number": 9})

    assert res.status_code == 404
    assert len(client.get(f"/trips/{trip.id}/versions").json()) == 1


def test_users_cannot_touch_each_others_trips(client, db_session):
    other = _trip(db_session, user_id="user-2")

    assert client.post(f"/trips/{other.id}/rollback", json={"version_number": 1}).status_code == 404
    assert client.post(f"/trips/{other.id}/refine", json={"instruction": "x"}).status_code == 404
    assert client.get(f"/trips/{other.id}/versions").status_code == 404
    assert client.get("/trips/my").json() == []
