import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# The real planner loads the LLM, LangGraph and the FAISS/embedding stack.
# Tests exercise the API and database logic, so replace it with a stub
# before any router module imports it.
_planner_stub = types.ModuleType("backend.ai_adapter.planner")
_planner_stub.generate_trip_itinerary = lambda data: f"plan for {data.destination_city}"
_planner_stub.refine_trip_itinerary = (
    lambda existing_itinerary, user_request: f"{existing_itinerary} | {user_request}"
)
sys.modules["backend.ai_adapter.planner"] = _planner_stub

from backend.database.base import Base  # noqa: E402
from backend.auth.auth_models import User  # noqa: E402,F401  (registers the users table)
from backend.trips.trip_models import Trip, TripVersion  # noqa: E402,F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
