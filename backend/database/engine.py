import os
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "travelai.db")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine_kwargs = (
    {"connect_args": {"check_same_thread": False}}
    if IS_SQLITE
    else {"pool_pre_ping": True}
)

engine = create_engine(DATABASE_URL, **engine_kwargs)
