# Travel AI Agent

Travel AI Agent is a full-stack AI trip planner built as an interview/demo project. It combines a FastAPI backend, React/Vite frontend, JWT authentication, saved trips, itinerary refinement, version history, LangGraph orchestration, FAISS retrieval, and live travel context from optional external APIs.

The project focuses on showing the complete travel planning flow: users can sign up, create a trip, review a structured itinerary, refine costs or transport choices, view previous versions, roll back changes, explore India travel trends, and generate short nearby plans.

## Project Features

- AI-generated day-wise itineraries with places, food, stay, transport, and estimated INR costs
- User-selectable transport mode: flight, train, or bus
- Budget-aware refinement for flights, hotels, daily spend, and total trip cost
- Saved trips with itinerary version history and rollback
- Travel HQ for trip readiness, price watch, and freeform refinements
- India Pulse for India travel trends, events, festivals, and discovery search
- AI Nearby Planner for short escapes, food trails, cafe hopping, weekend plans, and rainy-day backups
- Structured itinerary JSON designed for the frontend timeline, source confidence, and cost summaries
- JWT-based signup and login
- SQLite database for local development

## Project Structure

```text
.
|-- ai_core/              # LangGraph planner, Groq adapter, RAG, live search/API helpers
|-- backend/              # FastAPI app, auth, trips, nearby planner, discovery, database setup
|-- datasets/             # Optional local datasets for RAG/travel data
|-- frontend/             # React + Vite frontend
|-- api.py                # Older standalone API entrypoint
|-- Procfile              # Backend start command for platforms that read Procfiles
|-- requirements.txt      # Main Python dependencies
`-- README.md
```

## Requirements

- Python 3.11+
- Node.js 18+
- npm
- Groq API key
- Optional: SerpAPI key for flights, hotels, Tripadvisor, and Google search context
- Optional: Serper API key for web search fallback
- Optional: OpenWeather API key for weather context
- Optional: Indian Rail API key for train timetable enrichment

## Environment

Create `.env` in the project root. You can copy from `.env.example`.

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
APP_NAME=TravelAI Backend
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=sqlite:///backend/travelai.db

JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

SERPAPI_KEY=your_serpapi_key_here
SERPER_API_KEY=optional_serper_key_here
OPENWEATHER_API_KEY=your_openweather_key_here
INDIAN_RAIL_API_KEY=optional_indian_rail_api_key_here

SERPAPI_TIMEOUT=6
SERPAPI_CACHE_TTL=21600
WEB_SEARCH_TIMEOUT=5
WEB_SEARCH_CACHE_TTL=21600
WEATHER_CACHE_TTL=3600
TRANSPORT_API_TIMEOUT=6
TRANSPORT_CACHE_TTL=21600

RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_LOCAL_ONLY=true
RAG_CHUNK_SIZE=850
RAG_CHUNK_OVERLAP=140
RAG_TOP_K=5
RAG_SEARCH_MULTIPLIER=8
RAG_MMR_LAMBDA=0.72
LIVE_WEB_RESULTS=5
RAG_MEMORY_LIMIT=350
PLANNER_MAX_TOKENS=4500
```

Create `frontend/.env` if the backend URL is different from the default local URL.

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Local Setup

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Default local URLs:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://localhost:5173
Health:   GET http://127.0.0.1:8000/health
```

Useful frontend routes:

```text
/             Plan a trip
/nearby       AI Nearby Planner / Instant Escape
/dashboard    Saved trips
/command      Travel HQ price watch and refinement center
/india-pulse  India travel trends and events
/profile      Traveler profile
```

## Main API Routes

```text
POST /auth/signup
POST /auth/login

POST /trips/create
GET  /trips/my
POST /trips/{trip_id}/refine
GET  /trips/{trip_id}/versions
POST /trips/{trip_id}/rollback

GET  /trends/india
GET  /trends/india?q=events%20in%20Delhi%20this%20weekend

POST /nearby/generate
```

Authenticated routes require:

```text
Authorization: Bearer <access_token>
```

## AI/ML Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite, JWT authentication, Pydantic models, and modular route handlers for auth, trips, trends, and nearby planning.
- **Frontend:** React, Vite, JavaScript, CSS modules/pages, API service helpers, protected routes, dashboard views, trip detail views, Travel HQ, India Pulse, and Nearby Planner.
- **LLM layer:** Groq is used for itinerary generation, explanations, and refinement support.
- **Agent workflow:** LangGraph coordinates route resolution, retrieval, live context, quality checks, and final itinerary generation.
- **RAG:** FAISS stores local vector search data for retrieval-augmented generation.
- **Embeddings:** SentenceTransformers uses `all-MiniLM-L6-v2` for semantic search.
- **Retrieval logic:** Hybrid semantic and lexical retrieval improves matching, while MMR-style diversity reduces repetitive context.
- **Memory:** Useful live search results can be retained in local FAISS memory for future trip planning context.
- **Fallback embeddings:** If the sentence-transformer model is unavailable, the project can use deterministic hash embeddings so the planner still works locally.
- **Live context:** SerpAPI and Serper can provide fresher travel search information when keys are available.
- **Weather context:** OpenWeather can enrich destination planning with weather information.
- **Budget logic:** Deterministic guardrails parse user refinement requests, adjust costs, recalculate totals, and keep itinerary pricing consistent.
- **Structured output:** The backend returns JSON shaped for the frontend timeline, transport cards, hotel cards, cost summaries, source confidence, and nearby-plan maps.

Planning pipeline:

```text
resolve route -> retrieve RAG/live context -> fetch weather/flights/hotels/restaurants -> quality check -> generate itinerary
```

The main itinerary object is stored as `travelai_itinerary_v2` JSON and includes transport options, hotels, day-wise plans, cost summaries, and source confidence. The Nearby Planner uses a separate structured object for summary, stops, timing, route, costs, insights, alternates, and map coordinates.
