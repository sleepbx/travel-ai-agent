import pytest

from backend.trips.trip_models import Trip, TripVersion
from backend.trips.trip_service import (
    create_trip,
    get_trip_versions,
    rollback_trip,
    save_trip_version,
    update_trip_itinerary,
)


def _new_trip(db, itinerary="v1 plan"):
    return create_trip(db, user_id="user-1", title="Goa Trip", destination="Goa", itinerary=itinerary)


def test_create_trip_saves_version_one(db_session):
    trip = _new_trip(db_session)

    versions = get_trip_versions(db_session, trip.id)
    assert [v.version_number for v in versions] == [1]
    assert versions[0].instruction == "Initial plan"
    assert versions[0].itinerary == "v1 plan"


def test_versions_increment(db_session):
    trip = _new_trip(db_session)
    save_trip_version(db_session, trip.id, "v2 plan", "make it cheaper")
    save_trip_version(db_session, trip.id, "v3 plan", "add a beach day")

    assert [v.version_number for v in get_trip_versions(db_session, trip.id)] == [1, 2, 3]


def test_update_itinerary_changes_trip_and_appends_version(db_session):
    trip = _new_trip(db_session)

    update_trip_itinerary(db_session, trip, "v2 plan", "switch to train")

    assert trip.itinerary == "v2 plan"
    latest = get_trip_versions(db_session, trip.id)[-1]
    assert (latest.version_number, latest.instruction) == (2, "switch to train")


def test_rollback_restores_itinerary_and_keeps_history(db_session):
    trip = _new_trip(db_session)
    update_trip_itinerary(db_session, trip, "v2 plan", "make it cheaper")

    version = rollback_trip(db_session, trip, 1)

    assert trip.itinerary == "v1 plan"
    assert version.version_number == 3
    assert version.instruction == "Rollback to version 1"
    assert [v.itinerary for v in get_trip_versions(db_session, trip.id)] == ["v1 plan", "v2 plan", "v1 plan"]


def test_rollback_to_missing_version_changes_nothing(db_session):
    trip = _new_trip(db_session)

    assert rollback_trip(db_session, trip, 7) is None
    assert trip.itinerary == "v1 plan"
    assert len(get_trip_versions(db_session, trip.id)) == 1


def test_failed_commit_leaves_trip_and_history_consistent(db_session, monkeypatch):
    trip = _new_trip(db_session)
    trip_id = trip.id

    def failing_commit():
        raise RuntimeError("database went away")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        update_trip_itinerary(db_session, trip, "v2 plan", "make it cheaper")
    monkeypatch.undo()
    db_session.rollback()

    stored = db_session.get(Trip, trip_id)
    assert stored.itinerary == "v1 plan"
    assert db_session.query(TripVersion).filter(TripVersion.trip_id == trip_id).count() == 1


def test_each_operation_commits_exactly_once(db_session, monkeypatch):
    calls = []
    real_commit = db_session.commit

    def counting_commit():
        calls.append(1)
        real_commit()

    monkeypatch.setattr(db_session, "commit", counting_commit)

    trip = _new_trip(db_session)
    assert len(calls) == 1, "create_trip should save the trip and version 1 together"

    update_trip_itinerary(db_session, trip, "v2 plan", "make it cheaper")
    assert len(calls) == 2, "refine should update the trip and add a version together"

    rollback_trip(db_session, trip, 1)
    assert len(calls) == 3, "rollback should update the trip and add a version together"
