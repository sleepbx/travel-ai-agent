# TravelAI Project Explained

This file explains what has been built in TravelAI, how the pieces fit together, and what each major feature does.

## Product Summary

TravelAI is a full-stack AI itinerary planner. A user enters origin, destination, dates, travelers, interests, cabin class, and budget. The app creates a structured trip plan with:

- Cheapest-first flight options
- Train and bus alternatives with travel-time aware estimates
- A user-selected transport mode: flight, train, or bus
- Hotel options near the user's budget
- Day-wise itinerary
- Local transport, meals, stays, and activity costs
- Total trip cost summary in INR with intercity transport multiplied by traveler count
- Budget guardrails
- Refinement chat for changes like cheaper flights, lower hotel rates, slower pacing, food-first days, or luxury upgrades
- Saved trips with version history and rollback
- Travel HQ for ongoing trip readiness and price refreshes
- India Pulse for latest and trending India travel places, events, and news

The goal is not just to generate text. The app generates structured JSON so the frontend can show a polished, production-style travel dashboard.

## Main User Flow

1. User signs up or logs in.
2. User creates a trip from the home planner.
3. Backend resolves city names and airport codes.
4. Backend fetches RAG context, live web context, flights, hotels, weather, and restaurants.
5. Groq LLM generates a structured itinerary.
6. Deterministic guardrails normalize prices, fill missing fields, and keep costs near the budget.
7. The itinerary is saved to the database.
8. User opens the trip detail page.
9. User can refine anything, such as flights, hotels, food, budget, safety, pace, or activities.
10. Every refinement creates a new trip version.

## Frontend Pages

### Home

File:

```text
frontend/src/pages/Home.jsx
```

This is the main planner page. It has a usable trip form directly on the first screen. It collects:

- From city
- Destination city
- Depart date
- Return date
- Travelers
- Cabin class
- Preferred transport: flight, train, or bus
- Interests
- Budget in INR

The default cabin is now economy so flight prices start as cheap as possible. Flight prices are displayed as per-person rates and multiplied only when calculating the trip total.

### Dashboard

File:

```text
frontend/src/pages/Dashboard.jsx
```

Shows all saved trips for the logged-in user. Each trip card opens the trip detail page.

### Trip Details

File:

```text
frontend/src/pages/TripDetails.jsx
```

This is the main itinerary experience. It displays:

- Trip hero summary
- Route, days, and total cost
- Selected transport cards for flight, train, or bus
- Flight/train/bus comparison badges
- Hotel cards
- Day tabs
- Activity, transport, food, and stay modules
- Daily cost strips
- Budget guardrails
- Sources and confidence notes
- Refinement box

If a saved trip has missing or pending transport prices, the UI now shows approximate INR ranges instead of blank or pending values. Flight, train, and bus cards show per-person fare and total fare for all travelers.

Images in the itinerary are now destination-relevant. The page builds image queries from the destination and day theme.

### Travel HQ

Files:

```text
frontend/src/pages/TravelCommand.jsx
frontend/src/pages/TravelCommand.css
```

Travel HQ is a recurring page users can visit often after planning. It helps them keep trips ready to book.

It includes:

- Active trip switcher
- Readiness score
- Flight and hotel rate watch
- Budget pressure meter
- Before-booking checklist
- Quick AI commands
- Freeform refinement box

Example commands:

```text
Refresh the latest available flight rates and hotel rates.
Make this trip cheaper without making the days rushed.
Find a better hotel value near a safe central area.
```

### India Pulse

Files:

```text
frontend/src/pages/IndiaPulse.jsx
frontend/src/pages/IndiaPulse.css
backend/discovery/trends_router.py
```

India Pulse is a live discovery page for:

- Trending places in India
- Current events
- Festivals
- Concerts and exhibitions
- Travel news
- User search queries

The user can search from the right-side query panel. Example:

```text
events in Delhi this weekend
trending hill stations in India right now
food festivals in Hyderabad
new tourist attractions in India
```

If live search keys are missing, it returns clearly marked fallback suggestions instead of crashing.

Pulse cards now render real image elements with deterministic travel-image fallbacks. This avoids blank trend cards when a dynamic image endpoint is unavailable.

### Profile

File:

```text
frontend/src/pages/Profile.jsx
```

Shows user travel stats, recent trips, total planned days, and planning level.

## Backend

Backend framework:

```text
FastAPI
```

Main entrypoint:

```text
backend/main.py
```

The backend provides:

- Auth routes
- Trip routes
- Discovery/trends routes
- CORS configuration
- Database table creation

## Authentication

Files:

```text
backend/auth/auth_router.py
backend/auth/auth_service.py
backend/auth/auth_models.py
backend/core/security.py
```

The app uses JWT authentication.

Auth routes:

```text
POST /auth/signup
POST /auth/login
```

Protected trip routes require:

```text
Authorization: Bearer <token>
```

## Trip API

Files:

```text
backend/trips/trip_router.py
backend/trips/trip_service.py
backend/trips/trip_models.py
```

Main routes:

```text
POST /trips/create
GET  /trips/my
POST /trips/{trip_id}/refine
GET  /trips/{trip_id}/versions
POST /trips/{trip_id}/rollback
```

Trips are stored in the database with the itinerary JSON as text. Versions are stored separately so users can rollback.

## Discovery API

File:

```text
backend/discovery/trends_router.py
```

Routes:

```text
GET /trends/india
GET /trends/india?q=events%20in%20Delhi%20this%20weekend
```

This powers India Pulse. It uses the live web search layer when configured.

## AI Planning Core

Main file:

```text
ai_core/agent_core.py
```

TravelAI uses a LangGraph-style workflow:

```text
resolve route -> retrieve context -> fetch suppliers -> quality check -> generate itinerary
```

### Resolve

Normalizes city names and gets airport codes.

Examples:

```text
Bengaluru -> bangalore -> BLR
Hyderabad -> hyderabad -> HYD
Goa -> goa -> GOI
```

### Retrieve

Fetches:

- Local RAG documents
- Remembered online context
- Live web context

### Suppliers

Fetches:

- Flights
- Train and bus options
- Hotels
- Weather
- Restaurants and attractions

Calls happen in parallel to make planning faster.

### Quality

Adds notes about missing or unavailable data so the AI knows what must be treated as an estimate.

### Generate

Calls Groq and asks for a strict JSON itinerary.

## RAG System

Files:

```text
ai_core/rag_engine.py
ai_core/rag_documents.py
```

RAG means Retrieval-Augmented Generation.

The app retrieves useful travel context before asking the LLM to generate the itinerary.

It supports:

- FAISS vector search
- SentenceTransformer embeddings when available
- Local hash embedding fallback
- PDF loading
- Chunking
- Source-aware retrieval
- Online memory

Generated indexes and memory live under:

```text
ai_core/rag_index/
```

## Live Search

File:

```text
ai_core/web_search.py
```

The search priority is:

1. SerpAPI Google Search
2. Serper Google Search
3. Offline disabled message

This search layer is used by:

- Trip planning
- Flight fallback estimates
- Hotel fallback estimates
- India Pulse

## Flight Pricing

File:

```text
ai_core/zapi/flight_api.py
```

Flight pricing now follows this chain:

1. Try SerpAPI Google Flights.
2. If unavailable, try online search snippets for fare estimates.
3. If online estimates are unavailable, use an offline budget-aligned INR estimate.

Important rule:

```text
Flights are always selected cheapest-first from usable options.
```

The planner no longer tries to pick a flight near a high comfort target. It picks the cheapest usable fare first, treats that fare as per person, and multiplies it by traveler count only inside `total_price` and `cost_summary`.

## Train And Bus Pricing

File:

```text
ai_core/zapi/transport_api.py
```

Train and bus options follow this chain:

1. Try optional Indian Rail API timetable data for trains when `INDIAN_RAIL_API_KEY` is configured.
2. Use cached web search snippets for train or bus fare and duration estimates.
3. Fall back to offline budget-aligned INR ranges when live/search data is unavailable.

Train and bus rates are also treated as per-person fares. The selected transport mode is saved in `selected_transport_mode`, and the frontend shows the chosen mode while still keeping alternatives in the itinerary JSON.

## Hotel Pricing

File:

```text
ai_core/zapi/hotel_api.py
```

Hotel pricing follows a similar chain:

1. Try SerpAPI Google Hotels.
2. If unavailable, try online search snippets for room-rate estimates.
3. If unavailable, use an offline budget-aligned estimate.

Hotels are selected near the user's budget while still trying to stay practical and central.

## Budget Guardrails

File:

```text
ai_core/trip_payload.py
```

This is one of the most important files.

It handles:

- INR parsing
- Flight price ranges
- Train and bus price ranges
- Selected transport mode normalization
- Hotel price ranges
- Daily cost generation
- Total cost recalculation
- Budget target extraction from user requests
- Fallback itinerary creation
- JSON structure completion

Budget rules now prefer:

- Cheapest usable flight
- Cheapest usable selected transport
- Economy as the default cabin
- Lower flight share of total budget
- More room for stays, food, local transport, and activities
- Clear labels when a price is estimated

If the user gives a budget, the planner tries to keep the grand total near or under it. If exact live prices cannot fit, the plan marks the closest estimate and explains that live checkout prices should be verified.

## Refinement

Refinement lets the user ask natural-language changes after a trip is saved.

Examples:

```text
Make flights cheaper.
Switch to train and account for the extra time.
Try bus if it is cheaper.
Keep hotel under INR 4000 per night.
Reduce total trip under INR 50000.
Add nightlife on day 2.
Make it family friendly.
Refresh latest flight and hotel rates.
```

When a refinement mentions flights, trains, buses, hotels, rates, current prices, or budget, the backend refreshes supplier data or estimates before sending the itinerary back to the LLM.

## Structured Itinerary JSON

TravelAI stores itineraries as JSON with fields like:

```json
{
  "schema_version": "travelai_itinerary_v2",
  "title": "Goa Trip Plan",
  "origin": "Bangalore",
  "destination": "Goa",
  "selected_transport_mode": "train",
  "flights": [],
  "trains": [],
  "buses": [],
  "transport_options": {},
  "hotels": [],
  "days": [],
  "cost_summary": {},
  "sources": [],
  "booking_tips": [],
  "safety_tips": [],
  "budget_guardrails": {}
}
```

The frontend depends on this structure to render premium cards instead of raw text.

## Environment Variables

Important backend variables:

```env
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
JWT_SECRET_KEY=...
DATABASE_URL=sqlite:///backend/travelai.db
SERPAPI_KEY=...
SERPER_API_KEY=...
OPENWEATHER_API_KEY=...
INDIAN_RAIL_API_KEY=...
TRANSPORT_API_TIMEOUT=6
TRANSPORT_CACHE_TTL=21600
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Important frontend variable:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Local Development

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

Production frontend build:

```powershell
cd frontend
npm run build
```

## Deployment Readiness

The app is deployment-friendly because:

- Backend CORS is configurable.
- Frontend API base URL is configurable.
- Database URL is configurable.
- Secrets are stored in environment variables.
- Build output is generated by Vite.
- Live APIs gracefully fall back to estimates.
- Itinerary JSON is stable enough for UI rendering.
- The backend starts without `GROQ_API_KEY`; trip generation falls back to deterministic estimates until the key is configured.
- The production frontend build and lint checks pass.

For production, set:

```env
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://your-frontend-domain.com
VITE_API_BASE_URL=https://your-backend-domain.com
JWT_SECRET_KEY=long-random-secret
GROQ_API_KEY=...
SERPAPI_KEY=...
```

## What Was Added Recently

- Cheapest-first flight selection
- Flight fare per-person accounting with multiplied trip totals
- Flight/train/bus transport selector
- Train and bus search/estimate fallback layer
- Economy default cabin
- Flight online estimate fallback
- Hotel online estimate fallback
- Budget guardrails for flight, hotel, daily, and total costs
- Destination-relevant itinerary images
- Travel HQ page
- India Pulse page
- Reliable image rendering on India Pulse cards
- Discovery trends backend endpoint
- Frontend API base URL helper
- Deployment-focused README updates
- AI/ML explanation document

## Important Testing Commands

```powershell
python -m compileall ai_core backend
cd frontend
npm run lint
npm run build
```

These checks verify Python syntax, frontend linting, and production build readiness.
