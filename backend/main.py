from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "TravelAI Backend"),
    version="0.1.0"
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175",
    ).split(",")
    if origin.strip()
]
allow_all_origins = "*" in cors_origins
app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower()
local_dev_origin_regex = (
    r"https?://(localhost|127\.0\.0\.1):[0-9]+"
    if app_env not in {"prod", "production"} and not allow_all_origins
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_origin_regex=local_dev_origin_regex,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- DATABASE + MODELS --------
from backend.database.engine import engine
from backend.database.base import Base
from backend.auth.auth_models import User
from backend.trips.trip_models import Trip

Base.metadata.create_all(bind=engine)

# -------- ROUTERS --------
from backend.auth.auth_router import router as auth_router
from backend.trips.trip_router import router as trip_router
from backend.discovery.trends_router import router as trends_router
from backend.nearby.nearby_router import router as nearby_router

app.include_router(auth_router)
app.include_router(trip_router)
app.include_router(trends_router)
app.include_router(nearby_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": os.getenv("APP_NAME", "TravelAI Backend")}
