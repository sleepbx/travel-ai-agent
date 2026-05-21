# TravelAI AI/ML Technical Notes

This file explains the AI, ML, RAG, and orchestration pieces used in this project for someone who is learning machine learning.

## Short Summary

TravelAI is not a classic ML model-training project. It is an AI application that combines:

- A hosted LLM through Groq for itinerary generation and refinement
- LangGraph for a multi-step planning workflow
- FAISS vector search for retrieval-augmented generation
- SentenceTransformer embeddings when available
- A deterministic hashing embedder fallback when local embedding models are unavailable
- Live travel APIs for flights, hotels, web context, weather, and restaurants
- Search-backed train and bus estimates with optional rail timetable enrichment
- Budget guardrails that post-process the AI output so user price requests are respected more reliably
- React/Vite frontend for a premium itinerary UI
- FastAPI backend with JWT auth, trip persistence, refinement, version history, and rollback

## Important Clarification: LangChain vs LangGraph

People often say "LangChain" when they mean the broader ecosystem for building LLM apps.

This project currently uses `LangGraph`, not classic LangChain chains.

LangGraph is part of the LangChain ecosystem, but it is built for graph-style workflows. Instead of one long prompt, TravelAI breaks planning into nodes:

```text
resolve route -> retrieve context -> fetch suppliers -> quality check -> generate itinerary
```

That makes the app easier to debug and safer to extend because every step has a clear job.

## AI/ML Files

Main AI files:

- `ai_core/agent_core.py`
  - Main TravelAI planner
  - LangGraph workflow
  - Groq LLM calls
  - JSON itinerary generation
  - itinerary refinement

- `ai_core/rag_engine.py`
  - FAISS vector database
  - embedding model loading
  - text chunking
  - hybrid semantic and lexical retrieval
  - MMR-style result diversity
  - persistent online memory

- `ai_core/trip_payload.py`
  - deterministic itinerary normalization
  - fallback trip plan generation
  - INR price parsing
  - budget profile creation
  - flight, hotel, daily cost, and total-cost guardrails

- `ai_core/web_search.py`
  - live web enrichment through SerpAPI or Serper

- `ai_core/zapi/flight_api.py`
  - Google Flights via SerpAPI

- `ai_core/zapi/transport_api.py`
  - optional Indian Rail API timetable lookup
  - train and bus fare/duration estimates through cached web search
  - offline fallback ranges for deployment without transport API keys

- `ai_core/zapi/hotel_api.py`
  - Google Hotels via SerpAPI

- `ai_core/zapi/tools_weather.py`
  - weather context

- `ai_core/zapi/tripadvisor_api.py`
  - restaurant and attraction context

## What Is RAG?

RAG means Retrieval-Augmented Generation.

A normal LLM prompt only uses what you put directly into the prompt. RAG improves this by first searching a knowledge base, then giving the most relevant information to the LLM.

In this project:

1. TravelAI receives the trip request.
2. It builds a travel query such as:

```text
goa travel attractions food safety logistics best time beaches budget INR 50000
```

3. The RAG engine searches indexed travel documents and remembered online context.
4. The best chunks are sent to the LLM.
5. The LLM writes a structured itinerary using that context.

## Embeddings

Embeddings turn text into vectors, which are lists of numbers.

Similar meaning should create vectors that are close together. For example:

```text
"budget hotel in Goa"
"affordable stay near beach"
```

These should be closer than:

```text
"airport weather warning"
```

TravelAI tries to use:

```text
sentence-transformers/all-MiniLM-L6-v2
```

configured through:

```env
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

If that model is not available locally, the app falls back to `HashingEmbedder`, a deterministic local embedder in `ai_core/rag_engine.py`.

The fallback is not as semantically powerful as a transformer embedding model, but it lets the app keep working without downloading models.

## FAISS Vector Database

FAISS is used for fast nearest-neighbor search over vectors.

In simple terms:

1. Documents are split into chunks.
2. Each chunk becomes an embedding vector.
3. FAISS stores those vectors.
4. A user query also becomes a vector.
5. FAISS returns the chunks closest to the query vector.

The generated index is stored under:

```text
ai_core/rag_index/
```

That folder is ignored by git because it is generated data.

## Chunking

Long documents are too large to retrieve as one block.

TravelAI chunks documents using:

```env
RAG_CHUNK_SIZE=850
RAG_CHUNK_OVERLAP=140
```

Overlap matters because useful information may sit across chunk boundaries. A little repeated text helps retrieval avoid losing context.

## Hybrid Retrieval

The RAG engine does more than pure vector search.

It combines:

- semantic similarity from embeddings
- lexical overlap from shared query terms
- source weighting for live or online memory
- diversity penalties so repeated chunks do not dominate
- MMR-style selection to return varied but relevant context

This makes retrieval better for travel because users may ask with exact words like:

```text
flight
hotel
budget
food
family
under 50000
```

Exact words matter, but semantic similarity also matters.

## MMR-Style Diversity

MMR means Maximal Marginal Relevance.

The idea:

- choose results that are relevant
- avoid choosing five chunks that all say almost the same thing

TravelAI uses this style inside `RAGEngine._mmr_select`.

This helps the LLM see a broader set of context, such as:

- attractions
- food
- hotels
- safety
- transport
- weather
- live supplier data

## Online Memory

When live web or supplier context is fetched, TravelAI can remember useful snippets in:

```text
ai_core/rag_index/online_memory.jsonl
```

This means later trips can retrieve recent travel context without always depending on the same live API call.

This is not long-term model training. It is retrieval memory.

## LLM Usage

The LLM provider is Groq.

Configuration:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
PLANNER_MAX_TOKENS=4500
```

The planner calls Groq in two main ways:

- `call_groq`
  - normal text completion

- `call_groq_json`
  - asks the model to return a valid JSON object

The project prefers JSON output because the frontend can render flights, hotels, day plans, costs, sources, and tips in a structured premium UI.

## Prompt Engineering

The generation prompt in `ai_core/agent_core.py` gives the LLM:

- trip origin and destination
- dates
- travelers
- cabin class
- interests
- budget
- RAG context
- live web context
- flights
- trains and buses
- hotels
- restaurants
- weather
- quality notes
- exact JSON schema
- strict output rules

The strict schema reduces messy output and makes the frontend more reliable.

## LangGraph Workflow

The graph state is defined as `TripGraphState`.

Main nodes:

### 1. Resolve Node

File:

```text
ai_core/agent_core.py
```

Job:

- normalize city names
- map cities to IATA airport codes
- calculate trip duration

Example:

```text
Bengaluru -> bangalore -> BLR
Goa -> goa -> GOI
```

### 2. Retrieve Node

Job:

- retrieve local RAG context
- fetch live web context
- remember useful online context

### 3. Supplier Node

Job:

- fetch weather
- fetch flights
- fetch train and bus alternatives
- fetch hotels
- fetch restaurants/attractions

It uses `ThreadPoolExecutor` so independent API calls can happen in parallel.

### 4. Quality Node

Job:

- detect missing or unavailable sources
- add notes telling the LLM what is real, estimated, or unavailable

### 5. Generate Node

Job:

- call the LLM
- parse JSON
- normalize the result
- fill missing fields
- apply budget preferences
- return final itinerary JSON

## Budget Guardrails

LLMs can misunderstand price requests. For example, a user may say:

```text
make the hotel rate less
flight under INR 8000
reduce total trip to INR 50000
```

The app now adds deterministic guardrails in `ai_core/trip_payload.py`.

This layer:

- parses INR amounts from user requests
- detects whether the request is about flights, hotels, daily spend, or total trip cost
- starts from a medium comfort flight/hotel profile
- picks live supplier options closest to the target price
- updates flight price labels
- updates selected flight, train, or bus price labels
- updates hotel nightly and total estimates
- updates daily costs
- recalculates the cost summary
- adds `budget_guardrails` metadata for the frontend

This is important because deterministic logic is more reliable than asking an LLM to do arithmetic perfectly.

## Fallback Planning

If the LLM or an API fails, the app still returns a useful plan.

Fallbacks are handled in:

```text
ai_core/trip_payload.py
```

Fallback plans include:

- estimated flights
- estimated trains and buses
- estimated hotels
- day-wise activities
- meals
- local transport
- daily costs
- cost summary
- source confidence notes

This keeps the user experience stable even when live APIs are missing.

## Live APIs

The app can use:

- SerpAPI Google Flights
- Optional Indian Rail API train timetable enrichment
- SerpAPI Google Hotels
- SerpAPI Google Search
- Serper Google Search fallback
- OpenWeather
- Tripadvisor-style restaurant and attraction search

Environment variables:

```env
SERPAPI_KEY=your_serpapi_key_here
SERPER_API_KEY=optional_serper_key_here
OPENWEATHER_API_KEY=your_openweather_key_here
INDIAN_RAIL_API_KEY=optional_indian_rail_api_key_here
```

If keys are missing, the app marks those parts as estimates instead of crashing.

Transport pricing rule:

```text
Flight, train, and bus fares are stored as per-person prices. Trip totals multiply the selected fare by the traveler count.
```

## Backend

Backend framework:

```text
FastAPI
```

Main backend pieces:

- authentication
- JWT tokens
- trip creation
- trip refinement
- version history
- rollback
- database session management

Important files:

- `backend/main.py`
- `backend/auth/auth_router.py`
- `backend/auth/auth_service.py`
- `backend/trips/trip_router.py`
- `backend/trips/trip_service.py`
- `backend/database/engine.py`

Database:

- local default: SQLite
- deployable option: PostgreSQL through `DATABASE_URL`

## Frontend

Frontend stack:

- React
- Vite
- React Router
- Lucide React icons
- Framer Motion
- CSS modules/pages

The frontend renders structured itinerary JSON into:

- hero dossier
- selected transport cards for flight, train, or bus
- hotels
- day tabs
- daily cost strips
- activity, transport, food, and stay modules
- refine prompt box
- budget guardrail panel
- source confidence panel

The API base URL is deploy-ready through:

```env
VITE_API_BASE_URL=https://your-backend-url.example.com
```

## What This Project Does Not Do Yet

This project currently does not:

- train a custom neural network
- fine-tune an LLM
- use a supervised learning dataset
- use classic LangChain chains
- run a recommender model trained on user behavior
- use reinforcement learning

Those could be future upgrades, but the current project is already a strong modern AI app because it combines LLM reasoning, RAG retrieval, live data, structured outputs, and deterministic guardrails.

## Beginner ML Concepts You Can Learn From This Project

### Embedding

Text becomes numbers so similar text can be searched mathematically.

### Vector Search

FAISS finds chunks whose vectors are closest to the query vector.

### RAG

The LLM receives retrieved knowledge before generating an answer.

### Prompt Engineering

The app gives the LLM a strict role, schema, source data, and rules.

### Orchestration

LangGraph breaks the AI task into reliable nodes.

### Guardrails

Code validates and adjusts the LLM output so it better follows user needs.

### Fallbacks

The app still works when a model or API is unavailable.

## Best Way To Study The Project

Read files in this order:

1. `ai_core/agent_core.py`
2. `ai_core/rag_engine.py`
3. `ai_core/trip_payload.py`
4. `ai_core/web_search.py`
5. `ai_core/zapi/flight_api.py`
6. `ai_core/zapi/transport_api.py`
7. `backend/trips/trip_router.py`
8. `frontend/src/pages/TripDetails.jsx`
9. `frontend/src/pages/Home.jsx`

That order shows the full AI path from user request to rendered itinerary.
