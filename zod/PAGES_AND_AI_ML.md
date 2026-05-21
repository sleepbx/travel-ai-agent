# Pages And AI/ML Explanation

This document explains what each page in TravelAI does and how the AI/ML features work in the main intelligent areas: Trip planning, India Pulse, and Nearby Planner.

## Frontend Pages

Routes are defined in `frontend/src/App.jsx`.

## 1. Home Page

Route:

```text
/
```

Main file:

```text
frontend/src/pages/Home.jsx
```

The Home page is the primary trip creation page. It asks the user for:

- origin city
- destination city
- departure date
- return date
- traveler count
- cabin class
- preferred transport mode: flight, train, or bus
- interests
- maximum budget in INR

When the user clicks "Plan my trip", the page sends a request to:

```text
POST /trips/create
```

The backend then generates a complete AI itinerary and saves it to the database. After creation, the user is sent to:

```text
/trip/:id
```

The page also previews the AI planning pipeline using visual sections such as resolve, retrieve, constrain, and refine.

## 2. Plan Trip Page

Route:

```text
/planTrip
```

Main file:

```text
frontend/src/pages/PlanTrip.jsx
```

This page is another trip builder form. It collects the same core trip information as the Home page:

- from city
- destination city
- dates
- passengers
- cabin class
- transport mode
- interests
- budget

It also calls:

```text
POST /trips/create
```

After the backend creates the trip, the user is redirected to the trip details page.

## 3. Trip Details Page

Route:

```text
/trip/:id
```

Main file:

```text
frontend/src/pages/TripDetails.jsx
```

This page displays the generated itinerary as a travel dossier. It shows:

- trip title and summary
- route and number of days
- total estimated cost
- selected transport mode
- flight, train, or bus options
- hotel options
- day-wise itinerary
- activity, transport, food, and stay modules
- daily cost breakdown
- booking tips
- safety tips
- source confidence
- budget guardrail information

The page loads saved trips from:

```text
GET /trips/my
```

It finds the trip matching the route id and parses the saved itinerary JSON.

The page also has an AI refinement box. The user can ask for changes such as:

- cheaper route
- switch to train
- switch to bus
- lower hotel rate
- reduce total cost
- refresh latest rates

Refinement calls:

```text
POST /trips/{trip_id}/refine
```

The updated itinerary replaces the current version on screen and is also saved as a new version in the backend.

## 4. Dashboard Page

Route:

```text
/dashboard
```

Main file:

```text
frontend/src/pages/Dashboard.jsx
```

The Dashboard page is the user's saved trip workspace. It requires login and loads all trips for the current user from:

```text
GET /trips/my
```

It shows:

- total trips planned
- number of destinations
- trip cards
- last updated dates
- links to open each trip

This page does not directly call AI. It displays saved AI-generated trips.

## 5. Travel Command Page

Route:

```text
/command
```

Main file:

```text
frontend/src/pages/TravelCommand.jsx
```

Travel Command is a trip control center. It loads the user's saved trips and lets the user manage readiness before booking.

It shows:

- active trip switcher
- readiness score
- price watch
- selected transport rate
- selected hotel rate
- budget pressure meter
- before-booking checklist
- quick AI commands
- custom AI refinement box

This page uses the same trip refinement endpoint as Trip Details:

```text
POST /trips/{trip_id}/refine
```

So the AI behavior is the same refinement system, but presented as a command center for managing existing trips.

## 6. India Pulse Page

Route:

```text
/india-pulse
```

Main file:

```text
frontend/src/pages/IndiaPulse.jsx
```

India Pulse is a live discovery page for India travel trends. It shows:

- trending travel places
- events
- festivals
- concerts
- exhibitions
- travel news
- search results for user queries

On page load, it calls:

```text
GET /trends/india?limit=9
```

When a user searches, it calls:

```text
GET /trends/india?q=<query>&limit=9
```

The backend returns cards with:

- title
- summary
- source link
- category
- source provider
- freshness label
- image

If live search keys are missing or no results are available, the backend returns clearly marked fallback suggestions.

## 7. Nearby Planner Page

Route:

```text
/nearby
```

Main file:

```text
frontend/src/pages/NearbyPlanner.jsx
```

Nearby Planner creates short local plans and instant escapes. The user can choose:

- location
- duration
- mood
- budget
- transport mode
- travel radius
- group type
- surprise mode

It generates plans for use cases such as:

- 2-hour plans
- half-day outings
- weekend escapes
- food trails
- cafe hopping
- romantic evenings
- hidden gems
- solo recharge
- rainy-day plans

The page calls:

```text
POST /nearby/generate
```

The returned plan includes:

- summary
- stops
- best time to leave
- cost breakdown
- route order
- map coordinates
- weather, traffic, crowd, and AQI-style insights
- alternate versions
- structured JSON output

If the backend request fails, the frontend has a local fallback planner so the user still gets a usable route.

## 8. Profile Page

Route:

```text
/profile
```

Main file:

```text
frontend/src/pages/Profile.jsx
```

The Profile page is for traveler account/profile UI. It is part of the authenticated user experience. It is not a direct AI page.

## 9. Login Page

Route:

```text
/login
```

Main file:

```text
frontend/src/pages/Login.jsx
```

The Login page authenticates an existing user by calling:

```text
POST /auth/login
```

On success, it stores the JWT access token in browser local storage and redirects the user to the Dashboard.

## 10. Signup Page

Route:

```text
/signup
```

Main file:

```text
frontend/src/pages/Signup.jsx
```

The Signup page creates a new account by calling:

```text
POST /auth/signup
```

After signup, the user can log in and create trips.

# AI/ML Used In Trip

Trip planning is the most complete AI workflow in this project.

Important files:

```text
frontend/src/pages/Home.jsx
frontend/src/pages/PlanTrip.jsx
frontend/src/pages/TripDetails.jsx
frontend/src/pages/TravelCommand.jsx
backend/trips/trip_router.py
backend/ai_adapter/planner.py
ai_core/agent_core.py
ai_core/rag_engine.py
ai_core/trip_payload.py
ai_core/web_search.py
ai_core/zapi/
```

## Trip Request Flow

1. The user enters trip details on Home or Plan Trip.
2. The frontend sends the request to `POST /trips/create`.
3. `backend/trips/trip_router.py` receives the request.
4. `backend/ai_adapter/planner.py` creates a `TravelAI` agent.
5. `TravelAI.plan_full_trip(...)` generates the itinerary.
6. The final itinerary is saved in the database.
7. The frontend opens `/trip/:id` and renders the saved itinerary.

## LangGraph Orchestration

The trip planner uses LangGraph, which is part of the LangChain ecosystem. It is not using classic LangChain chains.

The planning workflow is split into nodes:

```text
resolve route -> retrieve context -> fetch suppliers -> quality check -> generate itinerary
```

This makes the planning process easier to control than using one large prompt.

## LLM Usage

The project uses Groq for LLM calls.

Configuration:

```text
GROQ_API_KEY
GROQ_MODEL
PLANNER_MAX_TOKENS
```

The LLM is used to generate structured itinerary JSON. The prompt includes:

- origin and destination
- travel dates
- traveler count
- cabin class
- selected transport mode
- interests
- budget
- retrieved RAG context
- live web context
- flights
- trains and buses
- hotels
- restaurants and attractions
- weather
- quality notes
- required JSON schema

The frontend depends on this structured JSON to render cards, day plans, transport options, hotels, costs, tips, and sources.

## RAG

RAG means Retrieval-Augmented Generation.

In this project, RAG is used so the LLM does not plan only from the prompt. The app first retrieves useful travel context, then gives that context to the LLM.

RAG files:

```text
ai_core/rag_engine.py
ai_core/rag_documents.py
ai_core/rag_dataset_loader.py
ai_core/rag_index/
```

The RAG system uses:

- text chunking
- embeddings
- FAISS vector search
- hybrid semantic and lexical retrieval
- MMR-style diversity
- online memory

## Embeddings And FAISS

Embeddings convert text into numeric vectors. Similar travel text should produce vectors close to each other.

The project tries to use:

```text
sentence-transformers/all-MiniLM-L6-v2
```

If that model is unavailable locally, it uses a deterministic hash-based fallback embedder.

FAISS stores and searches the vectors quickly. The planner retrieves the most relevant chunks and passes them into the LLM prompt.

## Live Travel Data

Trip planning can use live or semi-live context from:

- SerpAPI Google Flights
- SerpAPI Google Hotels
- SerpAPI Google Search
- optional Serper search fallback
- OpenWeather
- optional Indian Rail API
- Tripadvisor-style restaurant and attraction search

If API keys are missing, the app returns estimates instead of crashing.

## Budget Guardrails

The project does not trust the LLM to do all price calculations perfectly.

`ai_core/trip_payload.py` applies deterministic budget logic after generation. It can:

- parse INR amounts from user requests
- detect whether the user wants cheaper flights, hotels, daily spend, or total cost
- switch selected transport mode
- choose nearest available price options
- update per-person fares
- update hotel nightly estimates
- recalculate totals
- add `budget_guardrails` metadata

This is important because code is more reliable than an LLM for arithmetic and strict budget constraints.

## Refinement

Trip Details and Travel Command both support AI refinement.

Flow:

```text
POST /trips/{trip_id}/refine
```

The backend sends the existing itinerary and the user's instruction to `TravelAI.refine_itinerary(...)`.

Examples:

- "Make the trip cheaper."
- "Switch to train."
- "Keep hotel under INR 4000 per night."
- "Reduce total trip to INR 50000."
- "Make it more food focused."

The backend saves every refinement as a new trip version.

# AI/ML Used In India Pulse

India Pulse is not a deep ML planner like Trip. It is a live discovery and search-enrichment feature.

Important files:

```text
frontend/src/pages/IndiaPulse.jsx
backend/discovery/trends_router.py
ai_core/web_search.py
```

## Pulse Request Flow

1. The page loads or the user enters a query.
2. The frontend calls `GET /trends/india`.
3. The backend builds a search query.
4. `travel_web_search_json(...)` searches through SerpAPI or Serper when configured.
5. Results are compacted into frontend cards.
6. The frontend shows the cards with category, source, freshness, image, title, summary, and link.

## What Intelligence Is Used

India Pulse uses:

- live web search
- query expansion for default India travel trends
- result normalization
- simple rule-based categorization
- fallback results when live search is unavailable

The category system is rule-based. For example:

- words like festival, fair, mela, utsav become `Festival`
- words like concert, event, expo become `Event`
- words like beach, hill, temple, fort become `Place`
- everything else becomes `Travel news`

This page does not use the trip RAG pipeline or the LangGraph trip planner. It is closer to live search plus lightweight classification and UI shaping.

# AI/ML Used In Nearby Planner

Nearby Planner is a separate AI feature for short local escapes.

Important files:

```text
frontend/src/pages/NearbyPlanner.jsx
backend/nearby/nearby_router.py
backend/nearby/nearby_service.py
backend/nearby/nearby_models.py
```

## Nearby Request Flow

1. The user chooses duration, moods, budget, transport, radius, group type, and surprise mode.
2. The frontend sends the request to `POST /nearby/generate`.
3. The backend tries to call Groq for a compact JSON plan.
4. The backend validates and normalizes the LLM response.
5. If the LLM fails, the backend generates a deterministic fallback plan.
6. The frontend renders the plan as route cards, map preview, budget panel, insights, alternates, and JSON.

## LLM Usage

Nearby uses Groq with a smaller prompt than Trip.

The prompt asks the model for one compact JSON object containing:

- summary
- stops
- costs
- insights
- alternates

The prompt rules keep the output short:

- maximum 3 unique stops
- practical nearby place or area names
- stay within budget
- compact descriptions
- compact AI reasons
- route should be practical

Nearby does not use RAG and does not call the full trip planning graph.

## Deterministic Fallback And Ranking

Nearby has a strong fallback system in `backend/nearby/nearby_service.py`.

It contains a local library of possible stop types such as:

- skyline viewpoint
- street food lane
- design museum and cafe
- lake loop
- courtyard dinner
- maker market
- temple courtyard
- live music spot
- art walk
- spa and high tea
- science and dessert loop
- nature drive

The fallback ranks stops using:

- mood match
- group type match
- transport match
- radius match
- duration fit
- surprise mode bonus
- budget fit
- deterministic seed bonus

This is not machine learning training. It is rule-based scoring, but it behaves like a recommendation engine because it ranks options based on user preferences.

## Frontend Local Fallback

`frontend/src/pages/NearbyPlanner.jsx` also includes a local plan builder. If the backend request fails, the frontend still builds a usable nearby plan from local logic.

This gives the Nearby page two layers of resilience:

- backend LLM or backend deterministic fallback
- frontend deterministic fallback if the API cannot be reached

## Nearby Output

The final Nearby plan includes:

- title
- location
- duration
- budget
- travel distance
- weather snapshot
- best leave time
- mood tags
- timeline stops
- stop costs
- crowd level
- weather suitability
- opening-hour notes
- AI reason for each stop
- backup plan
- cost breakdown
- optimized route order
- traffic notes
- alternates
- coordinates for map rendering

# Simple Comparison

| Feature | Uses LLM | Uses RAG | Uses Live Web/API | Uses Rule-Based Logic | Main Purpose |
|---|---:|---:|---:|---:|---|
| Trip | Yes | Yes | Yes | Yes | Full multi-day itinerary |
| India Pulse | No direct trip LLM | No | Yes | Yes | Trending India discovery |
| Nearby | Yes | No | No direct live place API currently | Yes | Short local escape planner |

# What This Project Does Not Do

The current project does not train a custom ML model. It also does not fine-tune an LLM.

Instead, it builds an AI application using:

- hosted LLM calls
- prompt engineering
- structured JSON outputs
- LangGraph orchestration
- RAG retrieval
- embeddings
- FAISS vector search
- live web/API enrichment
- deterministic scoring
- budget guardrails
- fallback planning

This is a practical modern AI architecture: the LLM handles generation and reasoning, while code handles retrieval, validation, ranking, pricing rules, persistence, and UI rendering.
