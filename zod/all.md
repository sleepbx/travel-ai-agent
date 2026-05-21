# TravelAI Deployment Readiness Log

This file summarizes the latest project-wide update and the current deploy posture.

## Latest User-Facing Changes

- Added the **AI Nearby Planner / Instant Escape** feature at `/nearby`.
- Added a premium mobile-first nearby planning experience with location detection, duration, mood, budget, transport, radius, group type, and Surprise Me controls.
- Added cinematic loading states, route generation visuals, progressive itinerary cards, smart map visualization, budget breakdown, AI insights, alternate plans, and social actions.
- Added structured Nearby Planner JSON with `summary`, `stops`, `timing`, `costs`, `route`, `insights`, `alternates`, and `map_coordinates`.
- Fixed itinerary day image cards in Trip Details by replacing flaky dynamic background URLs with real image elements and deterministic fallbacks.
- Added the Nearby link to the main navigation.

## Existing Product Surface

- Home trip planner with flight, train, or bus transport selection.
- Authenticated dashboard for saved trips.
- Trip detail page with selected transport cards, hotel cards, day-wise itinerary, budget guardrails, and refinement prompts.
- Travel HQ for rate refreshes, readiness tasks, and quick AI commands.
- India Pulse for trending India places, events, festivals, and query-based discovery.
- User authentication with JWT login/signup.
- Saved trips, itinerary refinement, version history, and rollback.

## Backend Changes

- Added `backend/nearby/` with modular FastAPI routing, Pydantic models, and a reusable nearby planning service.
- Added `POST /nearby/generate`.
- Registered the Nearby router in `backend/main.py`.
- Normalized common `postgres://` database URLs to SQLAlchemy-compatible `postgresql://`.
- Added `pool_pre_ping` for non-SQLite production database connections.
- Added production JWT hardening: when `APP_ENV=production`, the backend fails fast if `JWT_SECRET_KEY` is missing, weak, or still using the dev fallback.
- Added `Procfile` for PaaS backend startup.

## Frontend Changes

- Added `frontend/src/pages/NearbyPlanner.jsx`.
- Added `frontend/src/pages/NearbyPlanner.css`.
- Added `/nearby` route in `frontend/src/App.jsx`.
- Added Nearby navigation item in `frontend/src/components/Navbar.jsx`.
- Updated Trip Details image handling in `TripDetails.jsx` and `TripDetails.css`.
- Added `npm run start` as a Vite preview command for container-style frontend hosts.
- Updated Vite preview config to bind to `0.0.0.0` and respect `PORT`.

## Deployment Readiness

The app is designed to deploy as two services:

```text
Backend:  FastAPI service from repository root
Frontend: Static Vite site from frontend/dist
```

Required production environment:

```env
APP_ENV=production
GROQ_API_KEY=...
JWT_SECRET_KEY=replace_with_a_long_random_secret_32_chars_or_more
DATABASE_URL=postgresql://...
CORS_ORIGINS=https://your-frontend-domain.com
VITE_API_BASE_URL=https://your-backend-domain.com
```

Optional live-data environment:

```env
SERPAPI_KEY=...
SERPER_API_KEY=...
OPENWEATHER_API_KEY=...
INDIAN_RAIL_API_KEY=...
```

Backend deploy commands:

```text
Build: pip install -r requirements.txt
Start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
Health: GET /health
```

Frontend deploy commands:

```text
Root: frontend
Build: npm ci && npm run build
Output: dist
Env: VITE_API_BASE_URL=https://your-backend-domain.com
```

## API Surface

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

## Verification Completed

Latest local checks:

```text
npm.cmd run lint
npm.cmd run build
python -m compileall backend\nearby
Nearby planner backend smoke test
GET http://127.0.0.1:5175/nearby -> 200
```

## Post-Deploy Smoke Test Checklist

- Open backend `/health`.
- Open frontend `/nearby`.
- Generate a nearby escape and confirm the timeline, map, budget, insights, alternates, and JSON sections render.
- Sign up or log in.
- Create a normal trip.
- Open `/dashboard`.
- Open a trip details page and confirm all day image cards load.
- Refine a trip from Trip Details or Travel HQ.

## Notes

- SQLite remains fine for local development.
- PostgreSQL is recommended for deployment.
- The backend can start without optional live-data keys, but `GROQ_API_KEY` is required for full AI trip generation.
- Nearby Planner has a frontend fallback generator, so the page remains interactive if the backend is temporarily unavailable.
