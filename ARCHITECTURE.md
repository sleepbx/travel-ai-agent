# TravelAI — Architecture Deep Dive

This document explains every major component of the system: how data flows through it, how the RAG pipeline works, what each file does, and how all the pieces fit together.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Data Flow](#2-high-level-data-flow)
3. [Backend Layer (FastAPI)](#3-backend-layer-fastapi)
4. [AI Core — LangGraph Planning Pipeline](#4-ai-core--langgraph-planning-pipeline)
5. [RAG Engine (Retrieval-Augmented Generation)](#5-rag-engine-retrieval-augmented-generation)
6. [LLM Layer (Groq)](#6-llm-layer-groq)
7. [Live Data APIs](#7-live-data-apis)
8. [Nearby Planner](#8-nearby-planner)
9. [India Pulse (Trends)](#9-india-pulse-trends)
10. [Caching Strategy](#10-caching-strategy)
11. [Database Schema](#11-database-schema)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Configuration Reference](#13-configuration-reference)
14. [Itinerary JSON Schema](#14-itinerary-json-schema)

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (React / Vite)                   │
│   Home  │  PlanTrip  │  TripDetails  │  Dashboard  │  Nearby   │
└──────────────────────────────┬──────────────────────────────────┘
                               │  HTTP / JSON
┌──────────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend (Python)                      │
│                                                                 │
│  /auth/*   /trips/*   /trends/*   /nearby/*   /health           │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Auth Router │  │ Trip Router  │  │  Nearby / Trends     │  │
│  │  JWT / bcrypt│  │ CRUD + ver.  │  │  Routers             │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────┘  │
│                           │                                     │
│               ┌───────────▼──────────┐                         │
│               │   ai_adapter/        │                         │
│               │   planner.py         │  (thin shim)            │
│               └───────────┬──────────┘                         │
└───────────────────────────│─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     ai_core/  (no FastAPI)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              agent_core.py  (TravelAI + LangGraph)      │   │
│  │                                                         │   │
│  │  resolve → suppliers → retrieve → quality → generate    │   │
│  └────────────┬──────────────┬──────────────┬─────────────┘   │
│               │              │              │                   │
│  ┌────────────▼──┐  ┌────────▼───────┐  ┌──▼──────────────┐  │
│  │  rag_engine   │  │  zapi/         │  │  llm/groq_llm   │  │
│  │  FAISS + MMR  │  │  flight, hotel │  │  Groq API       │  │
│  │  rag_documents│  │  maps, weather │  │  llama-3.1-8b   │  │
│  └───────────────┘  └────────────────┘  └─────────────────┘  │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────┐    │
│  │  trip_payload.py │  │  web_search  │  │  cache_utils  │    │
│  │  Budget + norms  │  │  SerpAPI/Ser │  │  TTL cache    │    │
│  └──────────────────┘  └──────────────┘  └───────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  SQLite / DB    │
                   │  users, trips,  │
                   │  trip_versions  │
                   └─────────────────┘
```

---

## 2. High-Level Data Flow

### Trip Creation Request

```
POST /trips/create
{
  origin_city, destination_city,
  depart_date, return_date,
  passengers, cabin_class,
  transport_mode, interests,
  max_budget
}
         │
         ▼
   trip_router.py
   └─ generate_trip_itinerary(data)
         │
         ▼
   ai_adapter/planner.py
   └─ TravelAI().plan_full_trip(...)
         │
         ▼
   agent_core.py — LangGraph graph.invoke(initial_state)
         │
         ├─ [Node 1] resolve_node
         │     Normalize city names (aliases + fuzzy match)
         │     Calculate total_days
         │     Detect destination_mode
         │     Look up IATA codes
         │
         ├─ [Node 2] suppliers_node  ← async parallel fetch
         │     asyncio.gather(
         │       fetch_flights()      → SerpAPI
         │       fetch_hotels()       → SerpAPI
         │       fetch_restaurants()  → Google Maps
         │       fetch_attractions()  → Google Maps
         │       fetch_weather()      → OpenWeatherMap
         │       fetch_ground_transport() → transport_api
         │     )
         │     classify_entities()   → tag each place by type
         │     cluster_places()      → group by neighborhood
         │     build_budget_profile() → per-item budget targets
         │
         ├─ [Node 3] retrieve_node   ← RAG
         │     Build rich semantic query from dest + place names
         │     rag.retrieve(query, top_k=6)
         │       → expand_query()
         │       → FAISS.search(k = top_k × 8)
         │       → hybrid score (semantic + lexical + city + source)
         │       → MMR rerank for diversity
         │     compress_rag_results() → 7 key insights (≤140 chars each)
         │
         ├─ [Node 4] quality_node
         │     Check for missing data keys
         │     Build quality_notes list
         │
         └─ [Node 5] generate_node
               Assemble compact source payload
               call_groq_json(prompt)  → structured JSON
               complete_trip_plan()    → fill gaps, validate schema
               Return itinerary JSON string
         │
         ▼
   trip_router.py
   └─ create_trip(db, user_id, ...)   → save to SQLite
   └─ return { trip_id, itinerary_preview }
```

### Trip Refinement Request

```
POST /trips/{id}/refine  { instruction: "make it cheaper" }
         │
         ▼
   trip_router.py
   └─ load existing itinerary from DB
   └─ refine_trip_itinerary(itinerary, instruction)
         │
         ▼
   TravelAI().refine_itinerary(...)
         │
         ├─ _refresh_supplier_prices_for_refinement()
         │     Parse instruction for intent (flight/hotel/train/bus/price)
         │     extract_budget_constraints() → parse INR targets from text
         │     Selectively re-fetch flights / hotels / ground transport
         │     Normalize and filter by new budget
         │
         └─ call_groq_json(refine_prompt)
               Prompt contains: current itinerary + instruction + fresh prices
               Returns: updated itinerary JSON preserving travelai_v11 schema
         │
         ▼
   Save updated itinerary + save_trip_version() → version history
   Return updated itinerary
```

---

## 3. Backend Layer (FastAPI)

### `backend/main.py`

The FastAPI application entry point. Responsibilities:
- Creates the `FastAPI` app instance
- Configures **CORS** from `CORS_ORIGINS` env var (supports wildcard `*` and regex for local dev)
- Creates all SQLAlchemy tables on startup via `Base.metadata.create_all()`
- Registers four routers: auth, trips, trends, nearby

### `backend/auth/`

| File | Role |
|---|---|
| `auth_models.py` | SQLAlchemy `User` model: `id` (UUID), `email`, `name`, `hashed_password`, `created_at` |
| `auth_schemas.py` | Pydantic `SignupRequest` and `LoginRequest` |
| `auth_service.py` | `signup_user()` — bcrypt hash + DB insert. `login_user()` — verify hash + issue JWT |
| `auth_router.py` | `POST /auth/signup`, `POST /auth/login` |
| `security.py` | `get_current_user_id()` — FastAPI dependency that decodes the Bearer JWT |

JWT tokens use HS256 with `SECRET_KEY`. Token expiry defaults to 60 minutes.

### `backend/trips/`

| File | Role |
|---|---|
| `trip_models.py` | `Trip` (id, user_id, title, destination, itinerary JSON string, created_at) and `TripVersion` (trip_id, version_number, itinerary, instruction, created_at) |
| `trip_service.py` | `create_trip()`, `get_user_trips()`, `save_trip_version()`, `get_trip_versions()`, `get_trip_version_by_number()` |
| `trip_router.py` | All `/trips/*` endpoints. Creates a trip, refines it, rolls back, and lists versions |

**Version numbering**: each refinement or rollback calls `save_trip_version()` which auto-increments `version_number` per trip.

### `backend/ai_adapter/planner.py`

A thin shim with no FastAPI imports. Imports `TravelAI` from `ai_core` and exposes two functions:

```python
generate_trip_itinerary(data) -> str   # Returns itinerary JSON string
refine_trip_itinerary(itinerary, instruction) -> str
```

This separation means `ai_core` can be tested and used independently of the web framework.

### `backend/database/`

- `engine.py` — creates the SQLAlchemy engine from `DATABASE_URL`
- `base.py` — `Base = declarative_base()` shared by all models
- `session.py` — `SessionLocal` factory and `get_db()` FastAPI dependency

---

## 4. AI Core — LangGraph Planning Pipeline

### `ai_core/agent_core.py`

The heart of the system. Contains:

#### `TripGraphState` (TypedDict)

The shared state object passed between LangGraph nodes:

```python
class TripGraphState(TypedDict, total=False):
    # Input
    origin_city, destination_city, depart_date, return_date
    passengers, cabin_class, transport_mode, interests, max_budget

    # Resolved
    origin, dest, origin_airport, dest_airport, total_days
    destination_mode      # e.g. "coastal_relaxed", "urban_heritage"

    # Supplier data
    weather, flights, hotels, restaurants, attractions
    ground_transport, places_raw, clusters, budget_profile

    # RAG
    rag_context           # List[str] — 7 compressed insights

    # Computed
    provider_context      # Compressed payload for LLM prompt
    quality_notes

    # Output
    itinerary             # Final JSON string
    error
```

#### Node 1 — `_resolve_node`

- Normalises city names through `LocationResolver`
  - Handles aliases: "vizag" → "visakhapatnam", "bengaluru" → "bangalore"
  - Fuzzy match via `difflib.get_close_matches` (cutoff 0.75)
  - State-to-city fallback: "telangana" → "hyderabad"
- Looks up IATA airport codes from a hardcoded dict (40+ cities)
- Calculates `total_days` (capped at 10)
- Detects `destination_mode` via keyword matching

**Destination Modes:**
```
coastal_relaxed  → Goa, Puducherry, Pondicherry, Bali
urban_heritage   → Delhi, Agra, Jaipur, Varanasi
food_culture     → Hyderabad
cafe_worklife    → Bangalore, Bengaluru, Pune
metro_culture    → Mumbai, Kolkata, Chennai
balanced_city    → all others
```

Each mode carries a rule string used in the LLM prompt:
```
coastal_relaxed → "slow mornings,sunset,shacks,scooter,cabs costly"
urban_heritage  → "early landmarks,metro,heat-smart afternoons"
food_culture    → "food clusters,old city pacing,cafe evenings"
...
```

#### Node 2 — `_supplier_node`

Runs all external API calls **concurrently** using `asyncio.gather()`:

```python
asyncio.gather(
    fetch_flights()         # SerpAPI flight search
    fetch_hotels()          # SerpAPI hotel search
    fetch_restaurants()     # Google Places
    fetch_attractions()     # Google Places
    fetch_weather()         # OpenWeatherMap
    fetch_ground_transport()# Train + bus search
)
```

After fetching:
- `classify_entities()` — tags each place as landmark, restaurant, café, museum, etc.
- `_cluster_places()` — groups attractions and restaurants by neighbourhood (area field from address), returns up to 5 clusters
- `build_budget_profile()` — allocates the total budget across flights, hotels, transport, food, and activities

**Budget Profile logic** (`trip_payload.py`):
```
If max_budget provided:
  target_flight_per_person = budget × 0.30 / passengers
  target_hotel_per_night   = budget × 0.25 / nights
  target_transport_pp      = budget × 0.10 / passengers
  target_daily_total       = remaining / days

Else: use sensible defaults per cabin class and destination
```

The node then calls `_compress_provider_payload()` to slim down the supplier data before storing in state — removing fields the LLM does not need and capping lists to 2 flights, 2 hotels, 6 restaurants, 8 attractions.

#### Node 3 — `_retrieve_node`

Builds a semantic query from the destination and provider places, runs it through the RAG engine, and compresses results to key insights.

```python
query = (
    f"{dest} travel guide {place_names} "
    f"{cluster_terms} {interests} "
    f"timing crowd transport budget food local tips"
)
rag_results = self.rag.retrieve(query, top_k=6)
rag_context = _compress_rag_results(rag_results, provider_context)
```

`_compress_rag_results()` filters RAG sentences to those mentioning known provider places or general travel terms (crowd, timing, metro, budget, etc.), deduplicates, and returns up to 7 insights capped at 140 characters each.

#### Node 4 — `_quality_node`

Checks all required data keys. If any are missing or errored (e.g. `flights.error`, `hotels.status == "unavailable"`), adds a note. The notes are added to the final itinerary as metadata.

#### Node 5 — `_generate_node`

Assembles the final LLM prompt:

```
TravelAI JSON only. Compact. No markdown.
Trip={"from":..., "to":..., "dates":..., "days":N, "pax":N, ...}
Src={flights, hotels, restaurants, attractions, rag, clusters, mode_rules, ...}
Return compact JSON: {schema_version, pipeline, destination_mode, summary,
                      selected_transport, selected_hotel, days, cost_summary,
                      budget_guardrails, ai_insights}
Rules:
- exact N days
- each day: morning/afternoon/evening activities, breakfast/lunch/dinner, transport
- activity = {time, title, area, cost}
- food = {breakfast: {meal, place, specialty, cost}, lunch: ..., dinner: ...}
- apply destination mode rules
- use clusters to avoid geographic zig-zag
- never place restaurant as landmark
- INR numbers when possible
- under 2500 output tokens
```

If the LLM call succeeds, the raw JSON is parsed and passed to `complete_trip_plan()` which fills in any missing fields from provider data. If the LLM fails, `build_fallback_trip_plan()` generates a deterministic itinerary from provider data without any LLM call.

#### `refine_itinerary()`

Takes an existing itinerary string and a natural language instruction:
1. Parses the existing itinerary JSON
2. Detects what the user wants to change (flight/hotel/train/bus/price) via regex
3. Selectively re-fetches those supplier types with new budget constraints
4. Calls `extract_budget_constraints()` to parse INR values from the instruction text ("under 50000", "₹30k total", "around 5000 per night")
5. Sends the updated itinerary + instruction + fresh prices to Groq as a refinement prompt
6. Applies `apply_budget_preferences()` as a deterministic post-processor

---

## 5. RAG Engine (Retrieval-Augmented Generation)

### `ai_core/rag_engine.py`

The RAG engine uses a local FAISS flat index (no external vector database required). It persists across process restarts.

#### Embedding Model

**Primary:** `all-MiniLM-L6-v2` via SentenceTransformers — a 384-dimensional model trained on semantic similarity. Works entirely locally.

**Fallback:** `HashingEmbedder` — a deterministic 384-dim hash-based embedder using BLAKE2b that works without any ML model download. Enables the planner to function even if transformers is unavailable.

```python
class HashingEmbedder:
    def encode(self, texts):
        # For each token: blake2b(token) → bucket index + sign
        # Accumulate into a 384-dim vector, L2-normalise
```

#### Index Persistence

```
rag_index/
├── faiss.index       Binary flat IP index (384-dim, L2-normalised vectors)
├── metadata.pkl      List of {text, metadata{title, source, city, state, chunk}}
├── manifest.json     {source_hash, embedding_model, chunk_size, chunk_overlap, documents}
└── online_memory.jsonl  One JSON object per line (live context memory)
```

The manifest stores a SHA-256 fingerprint of all document content + embedding config. On startup, `load_docs()` recomputes the fingerprint and skips re-indexing if it matches — making cold starts fast.

#### Chunking Strategy

```python
def _chunk_text(text, chunk_size=850, overlap=140):
    # 1. Collapse whitespace
    # 2. If text fits in one chunk, return it as-is
    # 3. Otherwise: slide window of chunk_size chars
    #    At each window end, try to split at ". " or "; " or ", "
    #    if the split point is > 55% of the chunk (avoids tiny tail chunks)
    # 4. Next window starts at (end - overlap) to maintain context continuity
```

This produces semantically coherent chunks rather than hard character cuts.

#### Title-Prefixed Embedding

Chunks are embedded as `"{Title}: {chunk text}"` — the document title is prepended before encoding. This means the embedding model understands what topic each chunk belongs to. The **stored text** in metadata remains the original chunk (without prefix) so retrieved text is clean.

```python
def _embed_with_title(chunks, titles):
    prefixed = [f"{t}: {c}" for t, c in zip(titles, chunks)]
    return self._embed(prefixed)
```

#### Query Expansion

Rather than always appending every travel term (which dilutes the destination signal), expansion is context-aware:

```python
def _expand_query(query):
    # Always add "india travel guide" if no travel domain terms present
    # Add "budget INR" if no cost terms present
    # Add "local transport" if no transport terms present
    # Add "morning timing crowd" if query mentions a specific landmark type
```

#### Retrieval + Scoring

`retrieve(query, top_k=6)` runs:

```
1. expand_query(query)
2. embed expanded query → 384-dim vector
3. FAISS.search(k = top_k × RAG_SEARCH_MULTIPLIER)   [default: 48 candidates]
4. For each candidate:
      base_score    = FAISS inner product (cosine similarity, since vectors are L2-normalised)
      lexical_bonus = min(|query_terms ∩ chunk_terms| × 0.012, 0.16)   [Jaccard-based]
      city_bonus    = 0.06 if destination tokens appear in chunk title/city metadata
      source_bonus  = 0.04 if source is "online-memory" (live cached context)
      diversity_pen = 0.025 if same title already seen (soft penalty, not hard dedup)
      final_score   = base + lexical + city + source - diversity
5. Sort candidates by final_score descending
6. MMR rerank → return top_k
```

#### MMR Reranking

Maximal Marginal Relevance iteratively selects the best next result that balances relevance and diversity:

```python
mmr_score = (λ × relevance_score) - ((1 - λ) × max_similarity_to_selected)
```

Where `λ = RAG_MMR_LAMBDA = 0.72` (72% relevance, 28% diversity).

Similarity between candidates uses Jaccard on 3+ character tokens from `title + text`.

#### Online Memory

Live search results (from SerpAPI / Serper) are persisted in `online_memory.jsonl`:

```python
rag.remember_online_context(
    query="weather in Hyderabad July",
    context={"temp": 32, "humidity": 85, ...},
    city="hyderabad",
    source="serpapi"
)
```

This:
1. SHA-256 fingerprints the content to deduplicate
2. Appends to `online_memory.jsonl`
3. Immediately adds to the live FAISS index via `add_documents()`

On the next cold start, `_load_memory_docs()` rehydrates the last `RAG_MEMORY_LIMIT` (350) lines back into the index. This means useful live context from past trips improves future retrievals without any re-fetching.

#### Knowledge Base

`rag_documents.py` provides 21 structured documents covering:

| Document | Key Content |
|---|---|
| India Travel Overview | Seasons, currency, SIM, tipping |
| India Transport Overview | Trains, flights, metro cities, cab costs |
| India Budget Guide | INR ranges per budget tier |
| Hyderabad City Guide | Neighborhoods, metro, IT corridors |
| Hyderabad Food & Attractions | Biryani, Charminar, Golconda, INR entry costs |
| Bangalore City Guide | MG Road, Koramangala, Namma Metro, traffic |
| Bangalore Food & Nightlife | Craft beer, darshinis, day trips |
| Mumbai City Guide | Local trains, Bandra, Dharavi, CORS |
| Mumbai Food & Attractions | Vada pav, Gateway, Marine Drive, seafood |
| Delhi City Guide | Old Delhi, Connaught Place, Metro |
| Delhi Food & Heritage | Red Fort, Humayun's Tomb, street food |
| Goa Travel Guide | North vs South, seasons, scooters |
| Goa Food & Beach Life | Shacks, water sports, flea markets |
| Rajasthan Travel Guide | Jaipur/Jodhpur/Udaipur/Jaisalmer overview |
| Jaipur City Guide | Amber Fort, Hawa Mahal, bazaars, INR costs |
| Kerala Travel Guide | Backwaters, Munnar, houseboat pricing |
| Varanasi Travel Guide | Ghats, Ganga Aarti timing, Sarnath |
| South India Travel Guide | Tamil Nadu, Karnataka, AP overview |
| Chennai City Guide | Marina, Kapaleeshwarar, shopping |
| Kolkata City Guide | Victoria Memorial, kathi rolls, Durga Puja |
| India Safety & Practical Tips | Scams, IRCTC booking, emergency numbers |

At 850-char chunk size, these 21 documents produce approximately **35 indexed chunks**.

---

## 6. LLM Layer (Groq)

### `ai_core/llm/groq_llm.py`

A singleton Groq client shared across calls:

```python
_groq_client: Groq | None = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client
```

**`call_groq(prompt, system_prompt, model)`**  
Standard completion. `temperature=0.4`, `max_tokens=1024`. Used by the RAG search summarize path (optional).

**`call_groq_stream(prompt, model)`**  
Generator yielding text chunks as the model streams. `temperature=0.4`, `max_tokens=2048`. Used for the Travel HQ streaming command interface.

### `agent_core.py` — LLM Functions

The main planning pipeline defines its own wrapper functions for itinerary-specific settings:

**`call_groq(prompt, max_tokens)`**  
`temperature=0.32`, `max_tokens=PLANNER_MAX_TOKENS`. Used for free-text generation fallback.

**`call_groq_json(prompt, max_tokens)`**  
`temperature=0.18` (lower for determinism), `response_format={"type": "json_object"}`. Used for all structured itinerary generation. Falls back to `call_groq` if the Groq API doesn't support JSON mode for the selected model.

**Token budget management:**
- `PLANNER_MAX_TOKENS=4500` — output budget
- Prompt is built to be under ~1,500 input tokens
- RAG context compressed to 7 × 140-char insights (~240 tokens)
- Provider data compressed to slim JSON (~400 tokens)
- Rules section is fixed and predictable

---

## 7. Live Data APIs

All live API calls are wrapped in `ai_core/zapi/` and use the shared `TTLCache`.

### Flights — `zapi/flight_api.py`
- Provider: SerpAPI Google Flights endpoint
- Cache TTL: `SERPAPI_CACHE_TTL` (default 6 hours)
- Timeout: `SERPAPI_TIMEOUT` (default 6 seconds)
- Returns normalised list of `{airline, from, to, departure, arrival, duration, price_per_person}`
- Falls back to budget-estimate generation if SerpAPI key is missing

### Hotels — `zapi/hotel_api.py`
- Provider: SerpAPI Google Hotels endpoint
- Same cache and timeout as flights
- Returns `{name, area, address, rating, price_per_night}`
- Budget estimates generated if key missing

### Places (Restaurants + Attractions) — `zapi/maps_api.py`
- Provider: Google Maps Places API (Nearby Search or Text Search)
- Returns `{name, address, rating, price_level, types}`
- `extract_google_restaurants()` / `extract_google_attractions()` filter by place type
- `get_distance()` uses Distance Matrix API for the Nearby Planner

### Weather — `zapi/tools_weather.py`
- Provider: OpenWeatherMap Current Weather API
- Cache TTL: `WEATHER_CACHE_TTL` (default 1 hour)
- Returns compact weather string: temperature, condition, humidity

### Ground Transport — `zapi/transport_api.py`
- Searches for trains and buses between city pairs
- Returns options with mode, route, duration, price_per_person

### Web Search — `ai_core/web_search.py`
- Provider: SerpAPI (priority) or Serper (fallback)
- Cache TTL: `WEB_SEARCH_CACHE_TTL` (default 6 hours)
- Used by: India Pulse trends, Nearby Planner Groq context
- Results also persisted via `rag.remember_online_context()` for future retrieval

---

## 8. Nearby Planner

**`backend/nearby/nearby_service.py`**

The Nearby Planner is a separate AI flow from the main trip planner:

```
POST /nearby/plan
{
  latitude, longitude,
  mood: "Food" | "Adventure" | "Relax" | "Romantic" | ...
  radius_km, time_available_hours
}
         │
         ▼
1. Map mood → search queries (MOOD_QUERIES dict)
   "Food" → ["restaurants", "street food", "cafes"]

2. search_google_places_nearby(lat, lng, query, radius)
   for each query → deduplicate → score → top N stops

3. Score each place:
   - base_score from Google rating
   - indoor/outdoor classification vs. time of day
   - distance penalty (closer = better)
   - diversity bonus (avoid same category twice)

4. get_distance() for each stop pair → build route

5. Build NearbyPlanResponse with:
   - stops: [{name, category, area, walk_time, rating, ...}]
   - route: total distance, estimated_time
   - costs: {entry, food, transport, total}
   - summary: {magic_touch, stop_reasons, insights, alternates}

6. Generate Groq explanation (cached 6h via TTLCache):
   prompt = compact stop + route data
   call_groq(prompt) → {magic_touch, stop_reasons, insights, alternates}
```

**Moods supported:** Relax, Adventure, Food, Romantic, Nature, Nightlife, Shopping, Photography, Hidden Gems, Luxury, Spiritual, Family, Solo Recharge, Rainy Day

---

## 9. India Pulse (Trends)

**`backend/discovery/trends_router.py`**

```
GET /trends/india?q=<optional query>
         │
         ▼
1. Default query: "India travel news events festivals this week"
   or use user-provided q param

2. travel_web_search_json(query) → SerpAPI / Serper results

3. For each result:
   - _category_for(text) → "festival" | "event" | "place" | "travel news"
   - _image_for(text, category) → deterministic image from Unsplash pool

4. Return: [{title, snippet, category, image, link}]
```

No database storage — fully live and cached in-memory for `WEB_SEARCH_CACHE_TTL`.

---

## 10. Caching Strategy

### `cache_utils.py` — `TTLCache`

A simple in-memory dict-based cache with TTL expiry:

```python
cache = TTLCache(ttl_seconds=21600)  # 6 hours
cache.set(value, *key_parts)         # key is a tuple of parts
value = cache.get(*key_parts)        # None if expired or missing
```

Used by:
- `web_search.py` — caches search results keyed by query string
- `tools_weather.py` — caches weather by city name
- `flight_api.py` / `hotel_api.py` — caches by route + date + parameters
- `transport_api.py` — caches by route + date
- `nearby_service.py` — caches Groq explanations by stop hash (6 hours)

**Cache is in-process only** (not shared between workers). For multi-worker production deployments, replace with Redis using the same `get/set` interface.

### RAG Online Memory

A complementary persistent cache specifically for travel search context:
- Stored in `rag_index/online_memory.jsonl` (survives restarts)
- Deduped by SHA-256 content hash
- Retrieved via FAISS semantic search
- TTL not applied (grows indefinitely, trimmed to last 350 entries)

---

## 11. Database Schema

SQLite by default. Configure via `DATABASE_URL` for Postgres.

### `users` table

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR (UUID) | Primary key |
| `email` | VARCHAR | Unique |
| `name` | VARCHAR | |
| `hashed_password` | VARCHAR | bcrypt |
| `created_at` | DATETIME | |

### `trips` table

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR (UUID) | Primary key |
| `user_id` | VARCHAR | FK → users.id |
| `title` | VARCHAR | e.g. "Goa Trip" |
| `destination` | VARCHAR | |
| `itinerary` | TEXT | Full JSON string (travelai_v11) |
| `created_at` | DATETIME | |

### `trip_versions` table

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR (UUID) | Primary key |
| `trip_id` | VARCHAR | FK → trips.id |
| `version_number` | INTEGER | Auto-incrementing per trip |
| `itinerary` | TEXT | Snapshot of itinerary JSON |
| `instruction` | VARCHAR | What the user asked for |
| `created_at` | DATETIME | |

---

## 12. Frontend Architecture

### React SPA (`frontend/src/`)

Single-page application with React Router. All state is local (no Redux/Zustand).

```
App.jsx
└── BrowserRouter
    ├── Navbar.jsx           Fixed top nav with auth state
    ├── /             → Home.jsx
    ├── /planTrip     → PlanTrip.jsx
    ├── /trip/:id     → TripDetails.jsx
    ├── /dashboard    → Dashboard.jsx
    ├── /command      → TravelCommand.jsx
    ├── /india-pulse  → IndiaPulse.jsx
    ├── /nearby       → NearbyPlanner.jsx
    ├── /profile      → Profile.jsx
    ├── /login        → Login.jsx
    └── /signup       → Signup.jsx
```

### `src/lib/api.js`

Centralised API client. All `fetch()` calls go through here:
- Reads `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`)
- Attaches `Authorization: Bearer <token>` from `localStorage` on authenticated routes
- Returns parsed JSON or throws on non-2xx

### Page Responsibilities

| Page | What it does |
|---|---|
| `Home.jsx` | Landing page, feature overview, CTA to plan or explore |
| `PlanTrip.jsx` | Form for trip creation; posts to `/trips/create`; shows loading state during AI generation |
| `TripDetails.jsx` | Renders full itinerary JSON as day timeline cards; has inline refine input; shows version history dropdown |
| `Dashboard.jsx` | Lists all user trips from `/trips/my`; links to TripDetails |
| `TravelCommand.jsx` | Freeform command bar for price watch, trip edits, and refinement in a chat-like interface |
| `IndiaPulse.jsx` | Fetches `/trends/india` and displays travel news/events with category images |
| `NearbyPlanner.jsx` | Lets user pick mood and enter location; shows stops on a simple map with route and cost breakdown |
| `Profile.jsx` | User info and settings |

---

## 13. Configuration Reference

| Variable | Default | Where Used |
|---|---|---|
| `GROQ_API_KEY` | — | `agent_core.py`, `groq_llm.py` |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | All Groq calls |
| `PLANNER_MAX_TOKENS` | `4500` | Generation and refinement prompts |
| `SECRET_KEY` | — | JWT signing in `security.py` |
| `JWT_ALGORITHM` | `HS256` | JWT encoding |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT expiry |
| `DATABASE_URL` | `sqlite:///backend/travelai.db` | SQLAlchemy engine |
| `APP_ENV` | `development` | CORS regex (local dev relaxes origin check) |
| `CORS_ORIGINS` | `http://localhost:5173,...` | FastAPI CORS middleware |
| `SERPAPI_KEY` | — | Flights, hotels, web search |
| `SERPER_API_KEY` | — | Fallback web search |
| `GOOGLE_MAPS_API_KEY` | — | Places and distance matrix |
| `OPENWEATHER_API_KEY` | — | Weather |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model name |
| `RAG_LOCAL_ONLY` | `true` | Prevent transformer model download |
| `RAG_CHUNK_SIZE` | `850` | Max chars per chunk |
| `RAG_CHUNK_OVERLAP` | `140` | Overlap chars between chunks |
| `RAG_HASH_DIM` | `384` | Fallback HashingEmbedder dimension |
| `RAG_TOP_K` | `5` | Default retrieval count (node uses 6) |
| `RAG_SEARCH_MULTIPLIER` | `8` | FAISS over-retrieval factor |
| `RAG_MMR_LAMBDA` | `0.72` | MMR relevance weight (0=diversity, 1=relevance) |
| `RAG_MEMORY_LIMIT` | `350` | Max online memory lines loaded |
| `RAG_SUMMARY_MODEL` | `llama-3.1-8b-instant` | Model for RAG summarize path |
| `WEB_SEARCH_CACHE_TTL` | `21600` | Web search cache (6 h) |
| `WEATHER_CACHE_TTL` | `3600` | Weather cache (1 h) |
| `TRANSPORT_CACHE_TTL` | `21600` | Transport cache (6 h) |
| `WEB_SEARCH_TIMEOUT` | `5` | HTTP timeout for web search |
| `TRANSPORT_API_TIMEOUT` | `6` | HTTP timeout for transport API |
| `NEARBY_SEARCH_LIMIT` | `8` | Max places fetched per nearby query |
| `NEARBY_QUERY_LIMIT` | `5` | Max place queries run per mood |
| `NEARBY_DISTANCE_CALL_LIMIT` | `4` | Max distance matrix calls per plan |

---

## 14. Itinerary JSON Schema

The LLM is instructed to return `schema_version: "travelai_v11"`. Key shape:

```json
{
  "schema_version": "travelai_v11",
  "pipeline": {
    "providers_completed": true,
    "rag_completed": true,
    "compression_completed": true,
    "budget_optimized": true
  },
  "destination_mode": "urban_heritage",
  "source_confidence": "medium",
  "summary": {
    "text": "3-day heritage and food trip to Delhi",
    "days": 3,
    "budget": 45000
  },
  "selected_transport": {
    "mode": "flight",
    "airline": "IndiGo",
    "from": "Hyderabad",
    "to": "Delhi",
    "departure": "07:30",
    "price": 4800
  },
  "selected_hotel": {
    "name": "Hotel Hari Piorko",
    "area": "Paharganj",
    "price_per_night": 2200
  },
  "days": [
    {
      "day": 1,
      "theme": "Old Delhi & Mughal Heritage",
      "daily_total": 4200,
      "activities": [
        { "time": "morning",   "title": "Red Fort",     "area": "Old Delhi",   "cost": 500 },
        { "time": "afternoon", "title": "Jama Masjid",  "area": "Old Delhi",   "cost": 0   },
        { "time": "evening",   "title": "Chandni Chowk walk", "area": "Old Delhi", "cost": 0 }
      ],
      "food": {
        "breakfast": { "meal": "breakfast", "place": "Hotel cafe", "specialty": "Paratha", "cost": 200 },
        "lunch":     { "meal": "lunch",     "place": "Karim's",    "specialty": "Mutton korma", "cost": 600 },
        "dinner":    { "meal": "dinner",    "place": "Al Jawahar", "specialty": "Seekh kebab", "cost": 700 }
      },
      "transport": { "mode": "Metro", "route": "Hotel → Old Delhi", "cost": 80 },
      "stay_cost": 2200
    }
  ],
  "cost_summary": {
    "flights_total": 9600,
    "hotels_total": 6600,
    "activities_total": 1200,
    "food_total": 4200,
    "transport_total": 600,
    "grand_total": 22200
  },
  "budget_guardrails": {
    "target_total": 45000,
    "actual_total": 22200,
    "within_budget": true
  },
  "ai_insights": [
    "Visit Red Fort at 9am before tour groups arrive",
    "Metro Blue Line runs directly to Dwarka Sector 21"
  ]
}
```

`complete_trip_plan()` in `trip_payload.py` validates and fills this structure after the LLM returns it, ensuring required fields exist and costs are numeric.
