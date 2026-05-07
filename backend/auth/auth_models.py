from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
import uuid

import uuid
from sqlalchemy import Column, String
from backend.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)          # ✅ ADD THIS
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

