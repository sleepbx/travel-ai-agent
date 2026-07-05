import os
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "TravelAI Backend"),
    version="0.1.0"
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_startup_errors: list[str] = []


def _try_import(label: str, fn):
    try:
        return fn()
    except Exception:
        _startup_errors.append(f"[{label}] {traceback.format_exc()}")
        return None


# DB setup
def _setup_db():
    from backend.database.engine import engine
    from backend.database.base import Base
    import backend.auth.auth_models  # noqa: F401
    import backend.trips.trip_models  # noqa: F401
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

_try_import("db_setup", _setup_db)

# Routers
auth_router = _try_import("auth_router", lambda: __import__("backend.auth.auth_router", fromlist=["router"]).router)
trip_router = _try_import("trip_router", lambda: __import__("backend.trips.trip_router", fromlist=["router"]).router)
trends_router = _try_import("trends_router", lambda: __import__("backend.discovery.trends_router", fromlist=["router"]).router)
nearby_router = _try_import("nearby_router", lambda: __import__("backend.nearby.nearby_router", fromlist=["router"]).router)

if auth_router:
    app.include_router(auth_router)
if trip_router:
    app.include_router(trip_router)
if trends_router:
    app.include_router(trends_router)
if nearby_router:
    app.include_router(nearby_router)


@app.get("/health")
def health_check():
    if _startup_errors:
        return {
            "status": "degraded",
            "service": os.getenv("APP_NAME", "TravelAI Backend"),
            "errors": _startup_errors,
        }
    return {"status": "ok", "service": os.getenv("APP_NAME", "TravelAI Backend")}
