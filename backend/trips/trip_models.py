from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
)
from sqlalchemy.sql import func
import uuid

from backend.database.base import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    destination = Column(String, nullable=False)

    itinerary = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class TripVersion(Base):
    __tablename__ = "trip_versions"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)

    version_number = Column(Integer, nullable=False)
    itinerary = Column(Text, nullable=False)
    instruction = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
