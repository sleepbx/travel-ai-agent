from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "TravelAI Backend"),
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

app.include_router(auth_router)
app.include_router(trip_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
