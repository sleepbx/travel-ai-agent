# Travel AI Agent

Travel AI Agent is a full-stack trip planning app. It combines a FastAPI backend, a React/Vite frontend, user authentication, saved trips, itinerary refinement, rollback/version history, and an AI planning core powered by Groq.

## Features

- User signup and login with JWT authentication
- AI-generated trip itineraries from origin, destination, dates, interests, cabin class, passengers, and budget
- Saved trips per user
- Itinerary refinement with natural-language instructions
- Trip version history and rollback
- React frontend for planning and managing trips
- SQLite database for local development

## Project Structure

```text
.
|-- ai_core/              # AI agent, Groq LLM adapter, RAG utilities, external API helpers
|-- backend/              # FastAPI app, auth, trips, database setup
|-- datasets/             # Local datasets for RAG or travel data
|-- frontend/             # React + Vite client app
|-- api.py                # Older standalone FastAPI API entrypoint
|-- requirements.txt      # Root Python dependencies for AI/backend utilities
`-- README.md
```

## Requirements

- Python 3.11+
- Node.js 18+
- npm
- A Groq API key

## Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
APP_NAME=TravelAI Backend
JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

`GROQ_MODEL`, `APP_NAME`, `JWT_ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` are optional. Set `JWT_SECRET_KEY` to a long random value for any shared or deployed environment.

## Backend Setup

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Frontend Setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

The frontend currently calls the backend at `http://127.0.0.1:8000`.

## Main API Routes

### Auth

```text
POST /auth/signup
POST /auth/login
```

### Trips

Authenticated trip routes require a bearer token from `/auth/login`.

```text
POST /trips/create
GET  /trips/my
POST /trips/{trip_id}/refine
GET  /trips/{trip_id}/versions
POST /trips/{trip_id}/rollback
```

Example authorization header:

```text
Authorization: Bearer <access_token>
```

## Notes

- The main backend entrypoint is `backend/main.py`.
- The database is SQLite and is created automatically at `backend/travelai.db`.
- `api.py` is an older standalone API that exposes chat and trip planning endpoints without the current auth/trip router structure.
- Do not commit real API keys or secrets.
