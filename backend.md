# Backend — Complete Interview Guide

## What is backend/?

`backend/` is the FastAPI web layer. It handles HTTP requests, authentication,
database operations, and routing. It does NOT contain any AI logic — that lives
in `ai_core/`. The backend is the interface between the web and the AI brain.

---

## Folder Structure

```
backend/
├── main.py                  ← App entry point, CORS, table creation, router registration
├── core/
│   ├── config.py            ← App settings/configuration
│   └── security.py          ← JWT token validation (FastAPI dependency)
├── auth/
│   ├── auth_models.py       ← SQLAlchemy User model
│   ├── auth_router.py       ← POST /auth/signup, /auth/login
│   ├── auth_schemas.py      ← Pydantic request/response schemas
│   └── auth_service.py      ← Business logic: signup, login, token issuance
├── trips/
│   ├── trip_models.py       ← SQLAlchemy Trip and TripVersion models
│   ├── trip_router.py       ← All /trips/* endpoints
│   └── trip_service.py      ← DB operations for trips and versions
├── ai_adapter/
│   └── planner.py           ← Thin shim: HTTP request → TravelAI agent
├── discovery/
│   └── trends_router.py     ← GET /trends/india — live events/news feed
├── nearby/
│   ├── nearby_models.py     ← Pydantic models for stops, routes, scores
│   ├── nearby_router.py     ← POST /nearby/plan
│   └── nearby_service.py    ← Place search, scoring, Groq explanation
└── database/
    ├── base.py              ← SQLAlchemy declarative base (shared by all models)
    ├── engine.py            ← Creates the database engine from DATABASE_URL
    └── session.py           ← SessionLocal factory + get_db() dependency
```

---

## FILE 1 — main.py

### Purpose
Entry point. Creates the FastAPI app, configures CORS, creates database tables
on startup, and registers all routers.

### Why FastAPI over Flask or Django?
| | FastAPI | Flask | Django REST |
|---|---|---|---|
| Async | Native | Bolted on | Bolted on |
| Validation | Pydantic (automatic) | Manual | Serializers |
| Auto docs | Swagger + ReDoc | None | None |
| Speed | Very fast | Moderate | Moderate |
| Learning curve | Low-medium | Low | High |

We chose FastAPI because:
- The supplier node fetches 6 APIs with `asyncio.gather()` — native async is critical
- Pydantic validates all request bodies automatically
- Swagger docs appear at `/docs` with zero extra code

### Key Code

```python
load_dotenv()   # Load .env into os.environ — must happen before anything reads env vars
```

```python
app = FastAPI(title=..., version="0.1.0")
# title and version appear in Swagger UI at /docs
```

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_origin_regex=local_dev_origin_regex,   # regex for any localhost port in dev
    allow_credentials=not allow_all_origins,      # can't combine * with credentials
)
```

**What is CORS?**
When React (port 5173) calls FastAPI (port 8000), the browser blocks it — different port = different origin = CORS violation. The middleware adds `Access-Control-Allow-Origin` headers to tell the browser the request is permitted.

**The smart CORS logic:**
- `CORS_ORIGINS=*` in .env → allow all origins (public API)
- Otherwise → allow the listed origins PLUS any localhost port via regex (useful because Vite picks a random port if 5173 is busy)
- `allow_credentials=True` only when NOT using wildcard — browser requirement

```python
Base.metadata.create_all(bind=engine)
# Creates all SQLAlchemy tables if they don't exist
# IMPORTANT: Model imports (User, Trip) must happen BEFORE this line
# so SQLAlchemy knows the tables exist
```

This is idempotent — safe to run every startup. NOT a migration tool — if you add a column to a model, it won't add it to existing tables. For that you'd use Alembic.

```python
app.include_router(auth_router)
app.include_router(trip_router)
app.include_router(trends_router)
app.include_router(nearby_router)
# Each router registers its URL prefix internally (e.g. "/auth", "/trips")
```

```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
# Deployment platforms (Render, AWS ECS) ping this to check if service is alive
```

### Common Bugs
- **404 on all routes** → forgot `app.include_router()`
- **CORS error in browser** → origin not in `CORS_ORIGINS`, or `allow_credentials` conflict with wildcard
- **Tables not created** → model imports happen after `create_all()` call

### Interview Questions — main.py
1. **"What is CORS and why does your backend need it?"**
   > CORS is a browser security policy that blocks requests from different origins. My React frontend on port 5173 calls my API on port 8000 — different ports are different origins. The CORSMiddleware adds the correct response headers to tell the browser these requests are allowed.

2. **"What does Base.metadata.create_all() do and what are its limitations?"**
   > It creates all SQLAlchemy model tables in the database if they don't exist. The limitation is it cannot handle schema migrations — if you rename a column, it won't update an existing table. For production you'd use Alembic migrations.

3. **"Why does FastAPI auto-generate API docs?"**
   > FastAPI inspects route decorators, Pydantic schemas, and Python type hints to build an OpenAPI specification. It then serves that spec as interactive Swagger UI at /docs and ReDoc at /redoc.

---

## FILE 2 — database/ (Three files)

### database/base.py
```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```
Creates the base class all SQLAlchemy models inherit from.
All models import this `Base` so SQLAlchemy can track them for `create_all()`.

### database/engine.py
```python
from sqlalchemy import create_engine
engine = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///backend/travelai.db"),
    connect_args={"check_same_thread": False}  # needed for SQLite
)
```
- `DATABASE_URL=sqlite:///...` → SQLite (development)
- `DATABASE_URL=postgresql://...` → PostgreSQL (production)
- `check_same_thread=False` is SQLite-specific: allows the same connection to be used across threads (FastAPI uses threads internally)

### database/session.py
```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
`get_db()` is a **FastAPI dependency** — injected via `Depends(get_db)` into route functions.
The `try/finally` guarantees the session is closed even if the route raises an exception.

**Why autocommit=False?**
Explicit transaction control. Changes are only committed when you call `db.commit()`.
This prevents accidental partial writes if something fails midway.

### Why SQLAlchemy?
| | SQLAlchemy | Peewee | Django ORM |
|---|---|---|---|
| Control | High | Medium | Medium |
| Raw SQL support | Full | Partial | Partial |
| Async | Via asyncio extension | Limited | Limited |
| Migration tool | Alembic | Built-in | Built-in |

SQLAlchemy is the most widely used Python ORM, works with any database, and is
the standard in FastAPI projects.

### Interview Questions — database/
1. **"What is the purpose of get_db() as a dependency?"**
   > It creates a new database session per request and guarantees it's closed when the request ends (via try/finally). Using it as a FastAPI dependency via `Depends(get_db)` means FastAPI injects a fresh session into every route function automatically.

2. **"How would you switch from SQLite to PostgreSQL?"**
   > Change DATABASE_URL in .env to a PostgreSQL connection string. No code changes needed — SQLAlchemy abstracts the database engine. You'd also remove `check_same_thread` since that's SQLite-specific.

---

## FILE 3 — auth/ (Four files)

### auth_models.py

```python
class User(Base):
    __tablename__ = "users"

    id         = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email      = Column(String, unique=True, nullable=False, index=True)
    name       = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Why UUID instead of auto-increment integer?**
- UUIDs don't expose how many users you have
- Safe to generate client-side without a DB round-trip
- Required if you ever shard the database across servers

**Why index on email?**
Login queries filter by email. Without an index, SQLite scans every row.
With an index, it's a B-tree lookup — O(log n) instead of O(n).

### auth_schemas.py

```python
class SignupRequest(BaseModel):
    name: str
    email: EmailStr        # Pydantic validates email format automatically
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

Pydantic schemas define what the request body must look like.
If the request is missing `email` or sends an invalid email format,
FastAPI returns a 422 Unprocessable Entity automatically — no manual validation code.

### auth_service.py

```python
def signup_user(db, name, email, password):
    if db.query(User).filter(User.email == email).first():
        raise ValueError("Email already registered")
    hashed = bcrypt.hash(password)
    user = User(name=name, email=email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db, email, password):
    user = db.query(User).filter(User.email == email).first()
    if not user or not bcrypt.verify(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}
```

**Why bcrypt?**
- bcrypt is the industry standard for password hashing
- It's slow by design — makes brute-force attacks expensive
- Automatically salts passwords — same password produces different hashes
- Alternative: Argon2 (newer, slightly better) — both are acceptable

**Never store plaintext passwords.** This seems obvious but is the most common auth mistake.

```python
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**JWT Structure:**
```
header.payload.signature

payload = {
    "sub": "user-uuid-here",
    "exp": 1234567890        # Unix timestamp: when token expires
}
```

The token is signed with `SECRET_KEY`. Anyone can decode the payload (it's base64) but cannot forge it without the secret.

### core/security.py

```python
def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

This is a **FastAPI dependency** used in all authenticated routes:
```python
@router.post("/trips/create")
def create_trip(user_id: str = Depends(get_current_user_id), ...):
    # user_id is automatically extracted from the Bearer token
```

**JWT vs Sessions:**
| | JWT | Sessions |
|---|---|---|
| Storage | Client (localStorage) | Server (DB/Redis) |
| Stateless | Yes | No |
| Revocation | Hard (need blacklist) | Easy (delete session) |
| Scaling | Easy (no shared state) | Needs shared session store |
| Size | ~200-500 bytes | Just a session ID |

We use JWT because the app is stateless — no need for a session store, works across multiple servers.

### auth_router.py

```python
@router.post("/auth/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = signup_user(db, data.name, data.email, data.password)
        return {"id": user.id, "email": user.email, "name": user.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        result = login_user(db, data.email, data.password)
        return result   # {"access_token": "...", "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

**Notice the pattern:**
Router → calls Service → Service raises ValueError on business logic errors → Router converts ValueError to HTTPException.

This keeps HTTP concerns out of the service layer. The service doesn't know it's being called from an HTTP endpoint.

### Common Bugs in auth/
1. **"Email already registered" on valid new email** — duplicate email check is case-sensitive. "Test@gmail.com" and "test@gmail.com" would both pass. Fix: `email.lower()` before storing.
2. **Token not sent by frontend** — check `Authorization: Bearer <token>` header. Missing "Bearer " prefix is a common mistake.
3. **Token expires during use** — `ACCESS_TOKEN_EXPIRE_MINUTES=60`. Consider refresh tokens for long sessions.
4. **SECRET_KEY not set** — `jwt.encode` with an empty/missing secret is a security vulnerability. Check this is set in .env.

### Interview Questions — auth/
1. **"How does JWT authentication work in your project?"**
   > On login, the server creates a JWT token containing the user's UUID in the `sub` claim, signed with a secret key. The frontend stores this token in localStorage. On every subsequent request, the frontend sends `Authorization: Bearer <token>`. The `get_current_user_id()` FastAPI dependency decodes and validates the token, extracting the user ID. No database lookup is needed for validation — the signature proves authenticity.

2. **"Why bcrypt for passwords?"**
   > bcrypt is deliberately slow (configurable work factor), making brute-force attacks expensive. It automatically generates a unique salt per password, so identical passwords produce different hashes. The hash contains the salt, so you only store one value.

3. **"What is a FastAPI dependency and how do you use it for auth?"**
   > A dependency is a function FastAPI calls before the route handler and injects the result as a parameter. `get_current_user_id` extracts and validates the JWT token. Any route that includes `user_id: str = Depends(get_current_user_id)` is automatically protected — FastAPI returns 401 if the token is invalid before the route function even runs.

4. **"What are the tradeoffs between JWT and session-based auth?"**
   > JWT is stateless — no server-side storage, scales horizontally easily. The downside is you can't immediately revoke a token without a blacklist. Sessions are stateful — easy to revoke by deleting the session, but require a shared session store (Redis) when scaling horizontally. For this project, JWT is appropriate since we don't need instant revocation.

5. **"How would you implement token refresh?"**
   > Issue two tokens on login: a short-lived access token (15 min) and a long-lived refresh token (7 days). Store the refresh token in an httpOnly cookie. When the access token expires, the frontend calls `POST /auth/refresh` with the cookie. The server validates the refresh token, issues a new access token. Optionally rotate the refresh token too.

---

## FILE 4 — trips/ (Three files)

### trip_models.py

```python
class Trip(Base):
    __tablename__ = "trips"

    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    title       = Column(String)                    # e.g. "Goa Trip"
    destination = Column(String)
    itinerary   = Column(Text)                      # Full JSON string
    created_at  = Column(DateTime, default=datetime.utcnow)


class TripVersion(Base):
    __tablename__ = "trip_versions"

    id             = Column(String, primary_key=True, default=lambda: str(uuid4()))
    trip_id        = Column(String, ForeignKey("trips.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    itinerary      = Column(Text)                   # Snapshot of itinerary JSON
    instruction    = Column(String)                 # What the user asked for
    created_at     = Column(DateTime, default=datetime.utcnow)
```

**Why store itinerary as Text (JSON string) instead of a proper JSON column or relational tables?**
- The itinerary schema evolves frequently (new fields, renamed keys)
- A relational schema would require migrations every time the AI output changes
- JSON string is flexible — the schema is defined by the AI output, not the DB
- SQLite doesn't have a native JSON column type anyway
- Downside: can't query inside the itinerary (e.g. "find all trips to Goa")

**Version history design:**
Each refinement or rollback creates a new `TripVersion` row with an auto-incremented `version_number` per trip. The `Trip.itinerary` always holds the current version. `TripVersion` holds snapshots for rollback.

### trip_service.py

```python
def create_trip(db, user_id, title, destination, itinerary):
    trip = Trip(user_id=user_id, title=title,
                destination=destination, itinerary=itinerary)
    db.add(trip)
    db.commit()
    db.refresh(trip)      # Refresh loads auto-generated fields (id, created_at)
    return trip

def save_trip_version(db, trip_id, itinerary, instruction):
    last = db.query(TripVersion).filter(
        TripVersion.trip_id == trip_id
    ).order_by(TripVersion.version_number.desc()).first()
    
    next_version = (last.version_number + 1) if last else 1
    version = TripVersion(
        trip_id=trip_id,
        version_number=next_version,
        itinerary=itinerary,
        instruction=instruction
    )
    db.add(version)
    db.commit()

def get_user_trips(db, user_id):
    return db.query(Trip).filter(Trip.user_id == user_id)\
             .order_by(Trip.created_at.desc()).all()
```

**Why `db.refresh(trip)` after commit?**
After `db.commit()`, SQLAlchemy expires all attributes on the object. `db.refresh(trip)` reloads them from the database. This is needed to access auto-generated fields like `id` (UUID generated by the default lambda) and `created_at` after the commit.

### trip_router.py

```python
@router.post("/trips/create")
def create_trip_api(
    data: CreateTripRequest,
    user_id: str = Depends(get_current_user_id),   # Auth required
    db: Session = Depends(get_db),                  # DB session injected
):
    itinerary = generate_trip_itinerary(data)       # Calls AI pipeline
    trip = create_trip(db, user_id, ...)            # Saves to DB
    return {"trip_id": trip.id, "itinerary_preview": itinerary[:400]}
```

```python
@router.post("/trips/{trip_id}/refine")
def refine_trip_api(trip_id, data, user_id, db):
    # 1. Load trip from DB, verify ownership (user_id must match)
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 2. Call AI refinement
    updated = refine_trip_itinerary(trip.itinerary, data.instruction)

    # 3. Update current itinerary
    trip.itinerary = updated
    db.commit()

    # 4. Save version snapshot
    save_trip_version(db, trip.id, updated, data.instruction)
    return {"trip_id": trip.id, "updated_itinerary": updated}
```

**Security note:** The filter `Trip.user_id == user_id` ensures users can only access their own trips. Without this, user A could refine user B's trip just by knowing the trip UUID. This is called **broken object level authorization (BOLA)** — one of OWASP's top API vulnerabilities.

```python
@router.post("/trips/{trip_id}/rollback")
def rollback_trip_api(trip_id, data: RollbackTripRequest, user_id, db):
    # 1. Verify trip ownership
    # 2. Load the specific version by version_number
    version = get_trip_version_by_number(db, trip_id, data.version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # 3. Restore current itinerary to that version
    trip.itinerary = version.itinerary
    db.commit()

    # 4. Save the rollback itself as a new version
    save_trip_version(db, trip.id, version.itinerary, f"Rollback to version {data.version_number}")
```

**Why save rollback as a new version?**
Maintains a complete audit trail. If you rollback from v3 to v1, that action is recorded as v4. You can always see what happened and undo the rollback.

### Common Bugs in trips/
1. **404 on valid trip** — `Trip.user_id == user_id` check fails if `user_id` is from a different token format. Check that `get_current_user_id` returns the same ID format stored in the DB.
2. **Version numbers not incrementing** — if two requests come in simultaneously, they might both read the same `last.version_number` and create duplicate version numbers. In production, use a database sequence or unique constraint.
3. **Itinerary truncated** — SQLite `Text` type has no size limit, but check that the JSON string isn't being truncated by the API response (the route returns `itinerary_preview: itinerary[:400]` — this is just the preview, the full thing is in the DB).

### Interview Questions — trips/
1. **"How does your version history and rollback work?"**
   > Every refinement and rollback saves a new `TripVersion` row with the itinerary snapshot and the instruction that triggered it. The `Trip` table always holds the current version. Rollback loads a specific version by number, sets it as the current itinerary, and saves the rollback itself as a new version for a complete audit trail.

2. **"Why store itinerary as a JSON string instead of a relational schema?"**
   > The itinerary schema evolves with the AI model — new fields, renamed keys, structural changes. A relational schema would require a migration every time the LLM output format changes. Text storage is flexible, and we only read/write the full object — we never query inside the JSON.

3. **"How do you prevent users from accessing other users' trips?"**
   > Every query includes a `user_id` filter: `Trip.id == trip_id AND Trip.user_id == user_id`. If the trip exists but belongs to another user, the query returns None and we raise a 404 — not a 403. Returning 403 would confirm the trip ID exists, which is an information leak.

4. **"What is the purpose of db.refresh() after db.commit()?"**
   > SQLAlchemy expires all object attributes after commit. `db.refresh()` reloads the object from the database so you can access auto-generated values like the UUID primary key and the `created_at` timestamp in the response.

---

## FILE 5 — ai_adapter/planner.py

### Purpose
A thin shim between the HTTP world (FastAPI) and the AI world (TravelAI agent).

```python
from ai_core.agent_core import TravelAI

def generate_trip_itinerary(data) -> str:
    agent = TravelAI()
    return agent.plan_full_trip(
        origin_city=data.origin_city,
        destination_city=data.destination_city,
        ...
    )

def refine_trip_itinerary(existing_itinerary: str, user_request: str) -> str:
    agent = TravelAI()
    return agent.refine_itinerary(existing_itinerary, user_request)
```

### Why have this adapter at all?
- `ai_core/` has **no FastAPI imports** — it's framework-agnostic
- `planner.py` is the only place that knows about both worlds
- If you replace FastAPI with Flask or Django, only `planner.py` needs to change
- `agent_core.py` can be tested independently without starting an HTTP server

**Design pattern: Adapter Pattern**
The adapter converts one interface (FastAPI request object) to another (keyword arguments for TravelAI). It also means the HTTP contract and the AI contract can evolve independently.

### Common Bugs
- **TravelAI() creates a new instance on every request** — this means the RAG engine loads fresh each time. Fix: use a module-level singleton `_agent = TravelAI()` so the FAISS index loads once.

### Interview Questions — ai_adapter/
1. **"Why do you have an adapter between the router and the AI agent?"**
   > Separation of concerns. The AI core has no knowledge of FastAPI — it can be tested as a Python library. The adapter is the only translation layer. If we switch web frameworks, only the adapter changes. If we change the AI pipeline signature, only the adapter changes. The two sides evolve independently.

---

## FILE 6 — nearby/

### Purpose
A separate AI feature from trip planning. Given a GPS location and a mood,
find and explain nearby places for a short outing.

### nearby_models.py

Pydantic models for the structured nearby plan response:
```python
class NearbyStop(BaseModel):
    name: str
    category: str          # "café", "park", "museum"
    area: str
    walk_time_minutes: int
    rating: float
    coordinates: Coordinates
    indoor: bool

class NearbyRoute(BaseModel):
    total_distance_km: float
    estimated_time_hours: float
    stops: List[NearbyStop]

class NearbyPlanResponse(BaseModel):
    summary: NearbySummary
    stops: List[NearbyStop]
    route: NearbyRoute
    costs: NearbyCosts
    diagnostics: NearbyDiagnostics
```

Using Pydantic response models means FastAPI validates the output structure.
If `nearby_service.py` returns a dict missing a required field, FastAPI raises an
error at the boundary — not silently sending malformed data to the frontend.

### nearby_service.py — Flow

```
POST /nearby/plan { latitude, longitude, mood, radius_km, time_available_hours }
            │
            ▼
1. Map mood → search queries:
   "Food"      → ["restaurants", "street food", "cafes"]
   "Adventure" → ["adventure activities", "sports complex", "trekking"]
   "Spiritual" → ["temples", "churches", "spiritual places"]
   ...14 moods total

2. search_google_places_nearby(lat, lng, query, radius)
   for each query (up to NEARBY_QUERY_LIMIT=5)
   Deduplicate results by place name

3. Score each place:
   base_score      = Google rating / 5.0
   indoor_bonus    = +0.1 if indoor and time is evening/rainy
   distance_penalty = proportional to distance from user
   diversity_bonus  = +0.15 for first of each category

4. get_distance() via Google Distance Matrix
   Build realistic route between top stops

5. Build NearbyPlanResponse with stops, route, costs, timing

6. Generate Groq explanation (cached 6h):
   prompt = compact stops + route data
   call_groq() → {magic_touch, stop_reasons, insights, alternates}
   Cache keyed by SHA-256 of stop names + mood
```

### MOOD_QUERIES dict
```python
MOOD_QUERIES = {
    "Relax":        ["parks", "cafes", "spa"],
    "Adventure":    ["adventure activities", "sports complex", "trekking"],
    "Food":         ["restaurants", "street food", "cafes"],
    "Romantic":     ["romantic restaurants", "view points", "gardens"],
    "Nature":       ["parks", "lakes", "nature attractions"],
    "Nightlife":    ["pubs", "live music", "nightlife"],
    "Shopping":     ["markets", "shopping mall", "boutiques"],
    "Photography":  ["tourist attractions", "view points", "art galleries"],
    "Hidden Gems":  ["tourist attractions", "art galleries", "cafes"],
    "Luxury":       ["fine dining", "luxury spa", "premium restaurants"],
    "Spiritual":    ["temples", "churches", "spiritual places"],
    "Family":       ["family attractions", "museums", "parks"],
    "Solo Recharge":["book cafes", "parks", "museums"],
    "Rainy Day":    ["museums", "indoor activities", "cafes"],
}
```

### Common Bugs in nearby/
1. **Google Places returns empty** — GOOGLE_MAPS_API_KEY not set or Places API not enabled in Google Cloud Console.
2. **Distance matrix costs money** — each `get_distance()` call uses the paid Distance Matrix API. `NEARBY_DISTANCE_CALL_LIMIT=4` caps the number of calls per request.
3. **Groq explanation not cached** — cache key is built from stop names. If place names change between requests (API returns slightly different results), cache misses. Consider keying on lat/lng + mood instead.

### Interview Questions — nearby/
1. **"How do you implement mood-based discovery?"**
   > Each mood maps to 2-3 Google Places search queries. We run all queries, deduplicate results, then score each place on rating, distance, indoor/outdoor appropriateness for the time of day, and category diversity. The top N stops are assembled into a route using the Distance Matrix API. A Groq call generates a human-readable explanation of why each stop was chosen.

2. **"How do you avoid making a Groq call on every nearby request?"**
   > The Groq explanation is cached in a TTLCache keyed by a hash of the stop names + mood, with a 6-hour TTL. If the same mood near the same location is requested again within 6 hours, the cached explanation is returned without a Groq call.

---

## FILE 7 — discovery/trends_router.py

### Purpose
Live India travel news and events feed powered by web search.

```python
@router.get("/trends/india")
def india_trends(q: str = Query(default=None)):
    query = q or "India travel news events festivals this week"
    results = travel_web_search_json(query, max_results=8)
    
    return [
        {
            "title": item["title"],
            "snippet": item["snippet"],
            "category": _category_for(item["title"]),   # "festival", "event", "place", "travel news"
            "image": _image_for(item["title"], category),
            "link": item["link"],
        }
        for item in results
    ]
```

**Image assignment logic:**
```python
pool = PULSE_IMAGE_POOLS[category]          # 2-3 Unsplash images per category
index = sum(ord(c) for c in text) % len(pool)  # Deterministic: same title → same image
return pool[index]
```

This is a simple hash — the same news title always gets the same image, so the feed looks consistent across page reloads, without storing any image mappings.

No database involvement — entirely live and cached for `WEB_SEARCH_CACHE_TTL` seconds.

### Interview Questions — discovery/
1. **"How does India Pulse work?"**
   > It sends a search query to SerpAPI (or Serper as fallback), receives web results, classifies each result by category (festival, event, place, travel news) using keyword matching, assigns a deterministic Unsplash image based on a hash of the title, and returns the enriched feed. Results are cached for 6 hours.

---

## Complete API Reference

### Auth Endpoints
```
POST /auth/signup
Body: { name, email, password }
Response: { id, email, name }
Auth: None
Errors: 400 email already registered

POST /auth/login
Body: { email, password }
Response: { access_token, token_type: "bearer" }
Auth: None
Errors: 401 invalid credentials
```

### Trip Endpoints (all require Authorization: Bearer <token>)
```
POST /trips/create
Body: {
  origin_city, destination_city,
  depart_date (YYYY-MM-DD), return_date (YYYY-MM-DD),
  passengers (int), cabin_class (economy/business),
  transport_mode (flight/train/bus),
  interests (string), max_budget (int, optional)
}
Response: { trip_id, message, itinerary_preview }
Errors: 401 unauthorized

GET /trips/my
Response: [{ id, title, destination, created_at }, ...]
Errors: 401 unauthorized

POST /trips/{trip_id}/refine
Body: { instruction: "make it cheaper" }
Response: { trip_id, message, updated_itinerary }
Errors: 401 unauthorized, 404 trip not found

POST /trips/{trip_id}/rollback
Body: { version_number: 2 }
Response: { trip_id, message, current_itinerary }
Errors: 401 unauthorized, 404 trip/version not found

GET /trips/{trip_id}/versions
Response: [{ version, instruction, created_at }, ...]
Errors: 401 unauthorized, 404 trip not found
```

### Discovery Endpoints
```
GET /trends/india
GET /trends/india?q=festivals+in+Rajasthan
Response: [{ title, snippet, category, image, link }, ...]
Auth: None
```

### Nearby Endpoints
```
POST /nearby/plan
Body: {
  latitude, longitude,
  mood: "Food" | "Relax" | "Adventure" | ...
  radius_km (float), time_available_hours (float)
}
Response: { summary, stops, route, costs, diagnostics }
Auth: None
```

### Health
```
GET /health
Response: { status: "ok", service: "TravelAI Backend" }
```

---

## Request Flow — Full Journey

```
1. User signs up:
   POST /auth/signup → auth_router → signup_user() → bcrypt hash → DB insert → return user

2. User logs in:
   POST /auth/login → auth_router → login_user() → bcrypt verify → JWT issue → return token

3. User creates a trip:
   POST /trips/create
   → JWT validated by get_current_user_id() dependency
   → CreateTripRequest validated by Pydantic
   → generate_trip_itinerary(data) in ai_adapter/planner.py
   → TravelAI().plan_full_trip(...)
   → LangGraph: resolve → suppliers → retrieve → quality → generate
   → Returns itinerary JSON string
   → create_trip() saves to SQLite
   → Returns trip_id + preview

4. User refines:
   POST /trips/{id}/refine { instruction: "switch to train" }
   → JWT validated, trip ownership verified
   → refine_trip_itinerary(current_itinerary, instruction)
   → TravelAI().refine_itinerary()
   → Detect intent → re-fetch ground transport → Groq edit
   → Update trip + save version snapshot
   → Return updated itinerary

5. User rolls back:
   POST /trips/{id}/rollback { version_number: 1 }
   → Load version 1 from trip_versions
   → Restore to trip.itinerary
   → Save rollback as new version
   → Return restored itinerary
```

---

## Database Schema

```
users
├── id              VARCHAR (UUID, PK)
├── email           VARCHAR (UNIQUE, INDEXED)
├── name            VARCHAR
├── hashed_password VARCHAR (bcrypt)
└── created_at      DATETIME

trips
├── id              VARCHAR (UUID, PK)
├── user_id         VARCHAR (FK → users.id)
├── title           VARCHAR
├── destination     VARCHAR
├── itinerary       TEXT (full JSON string)
└── created_at      DATETIME

trip_versions
├── id              VARCHAR (UUID, PK)
├── trip_id         VARCHAR (FK → trips.id)
├── version_number  INTEGER (auto-incremented per trip)
├── itinerary       TEXT (snapshot)
├── instruction     VARCHAR (what triggered this version)
└── created_at      DATETIME
```

---

## Security Checklist

| Concern | Implementation |
|---|---|
| Password storage | bcrypt with automatic salt |
| Auth tokens | JWT HS256, expires in 60 min |
| Route protection | `Depends(get_current_user_id)` on all trip routes |
| Object-level auth | All DB queries filter by `user_id` |
| CORS | Configured, no wildcard in production |
| SQL injection | SQLAlchemy ORM (parameterized queries) |
| Input validation | Pydantic on all request bodies |

---

## Common Interview Questions — Backend Overall

1. **"Walk me through what happens when a user plans a trip."**
   > The frontend POSTs to /trips/create with the trip parameters and a Bearer token. FastAPI validates the JWT and the request body via Pydantic. The router calls the AI adapter which instantiates TravelAI and runs the LangGraph pipeline: resolve city names, fetch live flights/hotels/weather/places concurrently, retrieve relevant knowledge from the FAISS vector store, quality-check the data, and finally call Groq to generate a structured JSON itinerary. The itinerary is saved to SQLite and the trip ID is returned.

2. **"How would you scale this backend?"**
   > Three changes: (1) Replace SQLite with PostgreSQL — SQLite doesn't support concurrent writes. (2) Replace the in-memory TTLCache with Redis — shared across multiple worker processes. (3) Add a task queue (Celery + Redis) for trip generation — currently synchronous, which blocks the HTTP worker thread for 3-10 seconds.

3. **"What security vulnerabilities did you consider?"**
   > BOLA (Broken Object Level Authorization) — all trip queries filter by user_id. SQL injection — prevented by SQLAlchemy ORM. Password security — bcrypt hashing. Token security — JWT with expiry and signature validation. CORS — configured with explicit origins.

4. **"How does your project handle errors when external APIs are down?"**
   > Each API wrapper in zapi/ has a fallback. If SerpAPI is unavailable, flight_api.py generates budget estimates. If Google Maps fails, trip_payload.py uses hardcoded seed places for known cities. The LangGraph pipeline has a `_run_graph_fallback()` and `build_fallback_trip_plan()` for complete LLM failures. The user always gets a response.

5. **"Why is ai_core/ separate from backend/?"**
   > Separation of concerns and testability. ai_core/ has no FastAPI imports — it's a pure Python library. It can be tested with pytest without starting an HTTP server. It can be called from a CLI script. If we switch from FastAPI to Django, only the adapter and routers change. The AI pipeline is completely decoupled from the HTTP layer.

---

## Modification Scenarios

**"Add rate limiting to the /trips/create endpoint"**
- Install `slowapi` library
- Add `@limiter.limit("5/minute")` to the route decorator
- No changes to service or ai_core needed

**"Add trip sharing (public link)"**
- Add `is_public: bool` column to Trip model
- Add `GET /trips/{trip_id}/public` endpoint without auth dependency
- Query: `Trip.id == trip_id AND Trip.is_public == True`

**"Add email verification on signup"**
- Add `is_verified: bool` column to User model
- On signup: generate a verification token, send email
- Add `GET /auth/verify?token=...` endpoint
- Block login if `user.is_verified == False`

**"Switch to async SQLAlchemy for better performance"**
- Change `create_engine` to `create_async_engine`
- Change `SessionLocal` to `AsyncSession`
- Change all route functions to `async def`
- Change all `db.query()` to `await db.execute(select(...))`
