# api.py — FastAPI backend for TravelAI (with CORS)

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_core import TravelAI

# -------------------------------------------------
# APP INIT
# -------------------------------------------------
app = FastAPI(
    title="TravelAI",
    version="0.1.0",
    description="Travel AI backend with chat, streaming, and trip planning",
)

# -------------------------------------------------
# CORS (REQUIRED FOR FRONTEND)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# AI AGENT
# -------------------------------------------------
agent = TravelAI()

# -------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------
class ChatRequest(BaseModel):
    message: str


class TripRequest(BaseModel):
    origin_city: str
    destination_city: str
    depart_date: str
    return_date: str
    passengers: int = 2
    cabin_class: str = "economy"
    interests: str = "sightseeing"
    days: int = 3
    max_budget: int | None = None


# -------------------------------------------------
# HEALTH
# -------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok", "service": "TravelAI"}


# -------------------------------------------------
# CHAT (NON-STREAMING)
# -------------------------------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    response = agent.ask(req.message)
    return {"response": response}


# -------------------------------------------------
# CHAT (STREAMING)
# -------------------------------------------------
@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def generator():
        for token in agent.ask_stream(req.message):
            yield token

    return StreamingResponse(generator(), media_type="text/plain")


# -------------------------------------------------
# FULL TRIP PLANNER
# -------------------------------------------------
@app.post("/trip")
def plan_trip(req: TripRequest):
    itinerary = agent.plan_full_trip(
        origin_city=req.origin_city,
        destination_city=req.destination_city,
        depart_date=req.depart_date,
        return_date=req.return_date,
        passengers=req.passengers,
        cabin_class=req.cabin_class,
        interests=req.interests,
        days=req.days,
        max_budget=req.max_budget,
    )

    return {"itinerary": itinerary}



class RefineRequest(BaseModel):
    itinerary: str
    user_request: str


@app.post("/refine")
def refine_trip(req: RefineRequest):
    updated = agent.refine_itinerary(
        existing_itinerary=req.itinerary,
        user_request=req.user_request,
    )
    return {"itinerary": updated}


