# Travel AI Agent

Travel AI Agent is a full-stack AI trip planner with a FastAPI backend, React/Vite frontend, JWT auth, saved trips, itinerary refinement, version history, LangGraph orchestration, FAISS vector RAG, and live travel search enrichment.

## Highlights

- AI-generated day-wise itineraries with places, travel, food, stay, and estimated INR costs
- Eye-catching React itinerary timeline with day tabs, section cards, and cost badges
- Budget-aware refinement that can lower flight fares, hotel rates, daily spend, or total trip cost toward the user's requested price
- Flight, train, bus, and hotel pricing fallback chain: live/optional APIs, cached online search estimates, then clearly labeled budget-aligned offline estimates
- User-selectable transport mode for each trip: flight, train, or bus
- Flight fares are treated as per-person rates; trip totals multiply the selected fare by traveler count
- Travel HQ command center for price watch, readiness tasks, and freeform refinements across saved trips
- India Pulse page for latest/trending India travel places, events, festivals, and query-based discovery
- AI Nearby Planner / Instant Escape page for 2-hour plans, half-day outings, weekend escapes, food trails, cafe hopping, romantic evenings, hidden gems, solo recharge plans, and rainy-day backups
- Nearby Planner structured JSON output with summary, stops, timing, costs, route coordinates, AI insights, alternates, and map-friendly data
- Premium home and trip-detail UI with route previews, source confidence, bookable options, and budget guardrails
- User signup/login with JWT authentication
- Saved trips, itinerary refinement, version history, and rollback
- LangGraph planning workflow for route resolution, RAG retrieval, live supplier data, quality checks, and generation
- Persistent FAISS vector database with hybrid semantic/lexical retrieval, MMR-style diversity, and online memory
- Live SerpAPI and optional Serper web context for current travel information
- OpenWeather support for destination weather context
- SQLite database for local development
- Deployment-friendly frontend/backend environment configuration

## AI/ML Learning Guide

For a beginner-friendly explanation of the ML, RAG, embeddings, FAISS, LangGraph, Groq LLM calls, live APIs, and budget guardrails used in this project, read:

```text
ML_TECH_STACK.md
```

Note: this project uses `LangGraph`, which is part of the LangChain ecosystem. It does not currently use classic LangChain chains.

For a full product and architecture walkthrough of everything built in the app, read:

```text
PROJECT_EXPLAINED.md
```

## Project Structure

```text
.
|-- ai_core/              # LangGraph planner, Groq adapter, RAG, live search/API helpers
|-- backend/              # FastAPI app, auth, trips, nearby planner, discovery, database setup
|-- datasets/             # Optional local datasets for RAG/travel data
|-- frontend/             # React + Vite frontend
|-- api.py                # Older standalone API entrypoint
|-- Procfile              # PaaS backend start command
|-- requirements.txt      # Main Python dependencies
|-- ML_TECH_STACK.md      # AI/ML architecture notes for learners
|-- PROJECT_EXPLAINED.md  # Full product and architecture walkthrough
`-- README.md
```

## Requirements

- Python 3.11+
- Node.js 18+
- npm
- Groq API key
- Production database for deployment; PostgreSQL is recommended
- Optional: SerpAPI key, Serper API key, OpenWeather API key
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

For production, set:

```env
APP_ENV=production
DATABASE_URL=postgresql://user:password@host:5432/travelai
CORS_ORIGINS=https://your-frontend-domain.com
JWT_SECRET_KEY=replace_with_a_long_random_secret_32_chars_or_more
```

`JWT_SECRET_KEY` must be a strong random value with at least 32 characters in production. The backend intentionally fails fast if production starts with the development secret.

`DATABASE_URL` can be SQLite for local development. For deployment, use PostgreSQL. The backend also normalizes common `postgres://` URLs to SQLAlchemy-compatible `postgresql://` URLs for PaaS providers.

`SERPAPI_KEY` enables flights, hotels, Tripadvisor, and live Google search context. `SERPER_API_KEY` is an optional fallback for live web search. `INDIAN_RAIL_API_KEY` is optional and only enriches train timetable results; bus and train fares can still fall back to cached search estimates or offline budget ranges. If Google Flights or Hotels cannot return a live price, TravelAI tries cached online fare/rate estimates before falling back to clearly marked offline estimates. Live results are also retained into the local FAISS memory so future trips can reuse useful online context faster. If the sentence-transformer model is unavailable locally, RAG falls back to a deterministic local hash embedder so trip generation still works.

## Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Create `frontend/.env` when deploying or when your backend is not local:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Frontend URL is usually:

```text
http://localhost:5173
```

Useful frontend routes:

```text
/          Plan a trip
/nearby    AI Nearby Planner / Instant Escape
/dashboard Saved trips
/command   Travel HQ price watch and refinement center
/india-pulse Latest India travel trends and events
/profile   Traveler profile
```

Production build:

```powershell
cd frontend
npm run build
```

If PowerShell blocks `npm.ps1`, use:

```powershell
npm.cmd run build
```

## Main API Routes

Auth:

```text
POST /auth/signup
POST /auth/login
```

Trips:

```text
POST /trips/create
GET  /trips/my
POST /trips/{trip_id}/refine
GET  /trips/{trip_id}/versions
POST /trips/{trip_id}/rollback
```

Discovery:

```text
GET /trends/india
GET /trends/india?q=events%20in%20Delhi%20this%20weekend
```

Nearby Planner:

```text
POST /nearby/generate
```

Authenticated routes require:

```text
Authorization: Bearer <access_token>
```

## Planning Pipeline

Trip generation uses a LangGraph workflow:

```text
resolve route -> retrieve RAG/live context -> fetch weather/flights/hotels/restaurants -> quality check -> generate itinerary
```

RAG uses FAISS with chunked documents, source-aware retrieval, and retained online memory from SerpAPI/Serper results. The generated itinerary is stored as `travelai_itinerary_v2` JSON for the frontend:

```json
{
  "selected_transport_mode": "flight | train | bus",
  "flights": ["1-2 options"],
  "trains": ["1-2 options"],
  "buses": ["1-2 options"],
  "hotels": ["1-2 options"],
  "days": ["day-wise activities, meals, transport, stay, costs"],
  "cost_summary": "trip totals",
  "sources": "RAG/live/estimate confidence"
}
```

Refinement also has deterministic budget guardrails. If a user says "make the flight under INR 8000", "switch to train", "try bus", "hotel rate less than INR 4000", or "reduce the whole trip to INR 50000", the planner parses the request, adjusts the relevant itinerary prices, recalculates totals, and marks nearest available estimates when exact live prices are unavailable. Flight, train, and bus option cards show per-person fares plus total fare for all travelers.

The AI Nearby Planner uses a separate frontend-friendly object model for local experiences and short escapes:

```json
{
  "summary": "title, duration, budget, distance, weather, best leave time, vibe tags",
  "stops": "timeline stops with images, ETA, cost, crowd, weather fit, coordinates, AI reason",
  "timing": "golden hour, nightlife, traffic, rain fallback windows",
  "costs": "food, transport, tickets, shopping, buffer",
  "route": "mode, radius, optimized order, commute time, map coordinates",
  "insights": "weather, traffic, AQI, crowd, opening-hour notes",
  "alternates": "cheaper, luxury, faster, hidden gems, weather-safe versions",
  "map_coordinates": "array of lat/lng pairs"
}
```

## Deployment Notes

TravelAI is deployment-ready as two services:

- Backend: FastAPI web service from the repository root
- Frontend: static Vite build from `frontend/dist`

Production checklist:

- Set `APP_ENV=production`
- Set a strong `JWT_SECRET_KEY` with at least 32 characters
- Use PostgreSQL for `DATABASE_URL`
- Set `CORS_ORIGINS` to the exact deployed frontend URL
- Set `VITE_API_BASE_URL` to the exact deployed backend URL
- Add `GROQ_API_KEY`; optional live data keys can be added later
- Run frontend lint/build before shipping

Backend web service:

```powershell
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

PaaS start command:

```text
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The included `Procfile` uses the same backend entrypoint for platforms that read Procfiles.

Backend health check:

```text
GET /health
```

Frontend static build:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

Publish directory:

```text
frontend/dist
```

Frontend preview/start command for container-style hosts:

```powershell
npm run start
```

Production environment variables:

```env
APP_ENV=production
GROQ_API_KEY=...
JWT_SECRET_KEY=replace_with_a_long_random_secret_32_chars_or_more
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://your-frontend-domain.com
VITE_API_BASE_URL=https://your-backend-domain.com
SERPAPI_KEY=...
SERPER_API_KEY=...
OPENWEATHER_API_KEY=...
INDIAN_RAIL_API_KEY=...
```

Suggested platform settings:

```text
Backend root: repository root
Backend build: pip install -r requirements.txt
Backend start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT

Frontend root: frontend
Frontend build: npm ci && npm run build
Frontend output: dist
Frontend env: VITE_API_BASE_URL=https://your-backend-domain.com
```

Post-deploy smoke tests:

```text
GET  https://your-backend-domain.com/health
POST https://your-backend-domain.com/nearby/generate
Open https://your-frontend-domain.com/nearby
Create an account, create a trip, open /dashboard, then refine a trip
```

## GitHub Notes

The `.gitignore` excludes secrets, virtual environments, caches, SQLite databases, generated RAG indexes, `node_modules`, and build output. Do not commit `.env`.

To commit:

```powershell
git add .
git commit -m "Update Travel AI Agent"
```
