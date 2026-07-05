# AI Core — Complete Interview Guide

## What is ai_core/?

`ai_core/` is the brain of TravelAI. It contains all AI and planning logic with zero FastAPI imports.
This separation means it can be tested in isolation, run as a CLI script, or plugged into a different web framework without touching the AI logic.

---

## Folder Structure

```
ai_core/
├── agent_core.py        ← LangGraph pipeline + TravelAI class (THE BRAIN)
├── rag_engine.py        ← FAISS vector store: chunk, embed, retrieve, rerank
├── rag_documents.py     ← 21-document India travel knowledge base
├── trip_payload.py      ← Budget math, normalization, fallback plan builder
├── web_search.py        ← SerpAPI / Serper web search with TTL cache
├── route_optimizer.py   ← Geographic clustering helper
├── llm/
│   └── groq_llm.py     ← Groq client singleton, call_groq, streaming
└── zapi/
    ├── flight_api.py    ← SerpAPI flight search
    ├── hotel_api.py     ← SerpAPI hotel search
    ├── maps_api.py      ← Google Places + distance matrix
    ├── transport_api.py ← Train and bus search
    └── tools_weather.py ← OpenWeatherMap
```

---

## FILE 1 — agent_core.py

### Purpose
Orchestrates the entire trip planning pipeline using LangGraph.
Contains the TravelAI class, all 5 pipeline nodes, location resolution, and the refinement flow.

### Why LangGraph?
LangGraph is a stateful directed graph framework. Each "node" is a Python function that reads from and writes to a shared state dictionary. Nodes connect via edges forming a pipeline.

**Why not just call functions sequentially?**
- State is automatically passed between steps without manual argument chaining
- Easy to add conditional branching later (e.g. skip RAG if index is empty)
- Graceful fallback: if the compiled graph fails, `_run_graph_fallback()` calls nodes manually in sequence
- Each node has a single responsibility — easier to test and debug independently

**Alternative:** A plain function chain. Simpler, but harder to extend with retries, branches, or parallel sub-graphs later.

---

### TripGraphState

```python
class TripGraphState(TypedDict, total=False):
    # User input
    origin_city, destination_city
    depart_date, return_date
    passengers, cabin_class, transport_mode
    interests, max_budget

    # After resolve node
    origin, dest
    origin_airport, dest_airport
    total_days
    destination_mode        # "coastal_relaxed", "urban_heritage", etc.

    # After supplier node
    weather, flights, hotels
    restaurants, attractions
    ground_transport, clusters
    budget_profile, provider_context

    # After retrieve node
    rag_context             # List[str] — 7 compressed insights

    # After quality node
    quality_notes

    # Final output
    itinerary               # Full JSON string
    error
```

`total=False` means every key is optional. Nodes only write what they produce — they don't need to touch keys from other nodes.

---

### Node 1 — _resolve_node

**What it does:** Normalizes city names, calculates trip duration, looks up IATA codes, detects destination mode.

**Key logic:**
```python
origin = LocationResolver.resolve("hyd")        # → "hyderabad"
dest   = LocationResolver.resolve("bengaluru")  # → "bangalore"
iata   = LocationResolver.iata_for("goa")       # → "GOI"
days   = (return_date - depart_date).days + 1   # capped at 10
mode   = _destination_mode(dest)                # → "cafe_worklife"
```

**LocationResolver — 3-step resolution:**
1. Check alias dict: "vizag" → "visakhapatnam", "bom" → "mumbai"
2. Check state-to-city: "telangana" → "hyderabad", "goa" → "goa"
3. Fuzzy match via `difflib.get_close_matches` (cutoff 0.75) — catches typos

**Destination Modes:**
```
coastal_relaxed  → Goa, Puducherry, Bali
urban_heritage   → Delhi, Agra, Jaipur, Varanasi
food_culture     → Hyderabad
cafe_worklife    → Bangalore, Pune
metro_culture    → Mumbai, Kolkata, Chennai
balanced_city    → everything else
```

Each mode carries planning rules used in the LLM prompt:
```
coastal_relaxed → "slow mornings, sunset, shacks, scooter, cabs costly"
urban_heritage  → "early landmarks, metro, heat-smart afternoons"
food_culture    → "food clusters, old city pacing, cafe evenings"
```

**Interview Q:** "Why cap total_days at 10?"
Groq's output token limit. A 10-day itinerary at full detail fills ~4000 tokens. Beyond 10 days the JSON would get truncated.

---

### Node 2 — _supplier_node (async parallel)

**What it does:** Fetches all live data concurrently using `asyncio.gather()`.

```python
asyncio.gather(
    fetch_flights(),          # SerpAPI
    fetch_hotels(),           # SerpAPI
    fetch_restaurants(),      # Google Maps Places
    fetch_attractions(),      # Google Maps Places
    fetch_weather(),          # OpenWeatherMap
    fetch_ground_transport(), # Train + bus search
)
```

**Why asyncio.gather?**
These 6 API calls are independent. Running them sequentially would take ~6× longer. `asyncio.gather()` fires all 6 at once and waits for all to finish. Since the APIs are network-bound (not CPU-bound), this is safe and fast.

**After fetching:**
- `classify_entities()` — tags each place: landmark, restaurant, café, museum, etc.
- `_cluster_places()` — groups places by neighborhood (from address field) into up to 5 clusters. This tells the LLM to plan geographically — don't make users zig-zag across the city.
- `build_budget_profile()` — splits `max_budget` into per-category targets

**Budget Profile logic:**
```
target_flight_per_person = max_budget × 30% / passengers
target_hotel_per_night   = max_budget × 25% / nights
target_transport_pp      = max_budget × 10% / passengers
target_daily_total       = remaining / days
```

If no budget given, uses sensible defaults per cabin class.

**`_compress_provider_payload()` — why compress?**
Groq has a token limit. Raw API responses contain dozens of fields. This function keeps only what the LLM needs:
- 2 flights, 2 hotels, 6 restaurants, 8 attractions
- Slim field sets: only name, area, price, rating
This reduces the prompt by ~70%.

**Interview Q:** "What happens if SerpAPI is not configured?"
Each API function has a fallback. If no key is found, it generates budget-estimate placeholders rather than returning an error. The trip still generates — just with estimated rather than live prices.

---

### Node 3 — _retrieve_node (RAG)

**What it does:** Queries the FAISS vector store to retrieve relevant India travel knowledge, then compresses it to key insights.

```python
query = (
    f"{dest} travel guide {place_names} "
    f"{cluster_terms} {interests} "
    f"timing crowd transport budget food local tips"
)
rag_results = self.rag.retrieve(query, top_k=6)
rag_context = _compress_rag_results(rag_results, provider_context)
```

The query is built from:
- Destination name
- Names of places fetched from supplier node (hotels, restaurants, attractions)
- Neighborhood cluster names
- User's interests
- Generic travel terms

**_compress_rag_results():**
Filters retrieved sentences to those that mention known provider places OR contain useful travel terms (crowd, timing, metro, budget, etc.). Returns up to 7 insights capped at 140 characters each.

**Why compress?** The LLM only has a 4500-token output budget. We can't dump all RAG text into the prompt — we compress to the most relevant sentences.

**Interview Q:** "What is RAG and why use it here?"
RAG = Retrieval-Augmented Generation. Instead of relying solely on the LLM's training knowledge (which may be outdated or hallucinated), we store factual travel knowledge locally and inject the most relevant facts into the prompt. This reduces hallucination and improves factual accuracy — e.g. knowing that Charminar entry costs ₹25 or that Goa beach shacks close in monsoon.

---

### Node 4 — _quality_node

**What it does:** Checks for missing or errored data, builds quality notes.

```python
for key in ("rag_context", "flights", "ground_transport", "hotels", "restaurants", "weather"):
    if not state.get(key) or state[key].get("error"):
        missing.append(key)
```

These notes are passed to the LLM as context and stored in the final itinerary metadata. Tells the LLM: "flights data was unavailable, use estimates."

---

### Node 5 — _generate_node (LLM call)

**What it does:** Assembles the final prompt and calls Groq to generate the structured JSON itinerary.

**Prompt structure:**
```
TravelAI JSON only. Compact. No markdown.
Trip={"from": "Hyderabad", "to": "Goa", "days": 3, "pax": 2, ...}
Src={flights, hotels, restaurants, attractions, rag_insights, clusters, mode_rules, budget_profile}
Return compact JSON: {schema_version, days[], cost_summary, budget_guardrails, ai_insights}
Rules:
- exact 3 days
- each day: morning/afternoon/evening activities + breakfast/lunch/dinner + transport
- apply destination mode rules
- use clusters to avoid geographic zig-zag
- never place restaurant as landmark
- INR numbers
- under 2500 output tokens
```

**Why temperature=0.18 for JSON generation?**
Lower temperature = more deterministic output. We need valid JSON every time. Higher temperature increases creativity but also increases JSON syntax errors.

**After LLM returns:**
- `_extract_json_object()` — strips markdown code fences if the LLM added them, parses JSON
- `complete_trip_plan()` — fills in any missing fields from provider data, validates schema

**Fallback:**
If LLM fails or returns non-JSON, `build_fallback_trip_plan()` generates a deterministic itinerary from provider data with no LLM call. The trip still works — it's just less personalized.

---

### refine_itinerary()

**What it does:** Takes an existing itinerary and a natural language instruction and updates it.

**Flow:**
```
1. Parse existing itinerary JSON
2. Detect intent from instruction via regex:
   - mentions "flight/fare/airline" → re-fetch flights
   - mentions "hotel/stay/room" → re-fetch hotels
   - mentions "train/rail" → re-fetch ground transport
   - mentions "price/budget/cheaper" → re-fetch all three
3. extract_budget_constraints() — parse INR values from text:
   "under 50000" → target_total=50000
   "₹30k" → target_total=30000
   "5000 per night" → target_hotel_nightly=5000
4. Re-fetch only the needed supplier types with new budget cap
5. call_groq_json(refine_prompt) — LLM edits only requested fields
6. apply_budget_preferences() — deterministic post-processor for budget enforcement
```

**Why not just re-run the full pipeline?**
Too slow and too expensive. The user only changed one thing. We selectively refresh only the relevant data and ask the LLM to edit only the requested fields, preserving everything else.

---

### _compact_source_payload() and _compress_provider_payload()

These two functions slim down the state data before it goes into the LLM prompt.

`_compact_source_payload()` — keeps essential fields, limits list sizes
`_compress_provider_payload()` — further reduces to shortest possible strings:
```python
# Flight becomes:
{"airline": "IndiGo", "from": "HYD", "to": "GOI", "departure": "07:30", "price": 4800}

# Hotel becomes:
{"name": "Hotel Sea View", "price": 2200, "area": "Calangute"}
```

This is critical for staying within Groq's token limits on the free tier.

---

### Key Libraries in agent_core.py

**LangGraph:**
- Why: Stateful pipeline with clean node separation and built-in fallback
- Alternative: Manual function chain — simpler but less extensible
- Disadvantage: Adds a dependency, slight overhead, overkill for 5 nodes

**groq (Python SDK):**
- Why: Groq provides the fastest free LLM inference (llama-3.1-8b-instant)
- Alternative: OpenAI API — paid, slower for free use. Ollama — requires local GPU.
- Free tier: 30 req/min, 6000 tokens/min — sufficient for this use case

**asyncio:**
- Why: Concurrent network calls without threading complexity
- Alternative: `concurrent.futures.ThreadPoolExecutor` — works but heavier
- `asyncio.gather()` fires all coroutines simultaneously and awaits all completions

---

### Common Bugs in agent_core.py

1. **LangGraph not installed** — `StateGraph = None` check at top. Graph falls back to `_run_graph_fallback()`. Check by printing `StateGraph` — if None, LangGraph import failed.

2. **asyncio.run() inside an async context** — `_supplier_node` calls `asyncio.run(_supplier_node_async)`. If FastAPI is already in an async context, this can throw "Event loop already running." Fix: use `asyncio.get_event_loop().run_until_complete()` or run the node differently.

3. **JSON parse failure** — LLM returns markdown-wrapped JSON. `_extract_json_object()` handles this by stripping code fences. If itinerary is blank, check `raw` variable before `_extract_json_object`.

4. **Budget not applied** — `build_budget_profile()` only applies if `max_budget` is set. Check `state.get("max_budget")` — it may be None if the frontend sent 0.

---

### Interview Questions — agent_core.py

1. **"Explain the LangGraph pipeline in your project."**
   > Five nodes run in sequence: resolve (normalize inputs), suppliers (parallel API fetch), retrieve (RAG vector search), quality (data validation), generate (Groq LLM). Each node reads from and writes to a shared TypedDict state. If LangGraph is unavailable, a fallback calls the same nodes manually.

2. **"Why do you use asyncio.gather in the supplier node?"**
   > The 6 external API calls are independent of each other. Running them sequentially would take ~6× longer. asyncio.gather fires all coroutines concurrently and waits for all to finish, reducing total supplier time from ~6s to ~1-2s.

3. **"What happens if Groq returns invalid JSON?"**
   > `_extract_json_object()` tries to strip markdown fences and find a JSON object using rfind(). If it still fails, `build_fallback_trip_plan()` generates a deterministic itinerary from provider data — the user still gets a complete trip plan.

4. **"How do you handle budget constraints?"**
   > At planning time, `build_budget_profile()` splits `max_budget` into per-category targets (flights 30%, hotels 25%, transport 10%, rest for food/activities). These targets are passed to each API call as `max_price` filters. The LLM is also instructed not to exceed the budget. Finally, `apply_budget_preferences()` enforces hard caps as a post-processing step.

5. **"What is a destination mode and how is it used?"**
   > Destination mode classifies the city's travel character: coastal_relaxed for Goa, urban_heritage for Delhi, etc. Each mode has a rule string like "slow mornings, sunset, shacks, scooter" that is injected into the LLM prompt. This shapes HOW the LLM plans the day — beach days start slow, heritage cities start early at landmarks.

6. **"How does the refinement differ from re-planning?"**
   > Refinement is surgical. It parses the user's instruction, detects which data needs refreshing (flights, hotels, or transport), re-fetches only those, and asks the LLM to edit only the requested fields. Full re-planning discards everything. Refinement is faster, cheaper, and preserves the user's existing itinerary structure.

7. **"Why separate ai_core from backend?"**
   > Separation of concerns. `ai_core` has no FastAPI imports so it can be run as a CLI, tested in isolation with `pytest`, or mounted in a different web framework. The `ai_adapter/planner.py` is the only translation layer between HTTP and AI concerns.

---

### Modification Scenarios

**"Add a new node to the pipeline that checks visa requirements"**
- Create `_visa_node()` method in TravelAI
- Add `graph.add_node("visa", self._visa_node)`
- Change edge from `suppliers → retrieve` to `suppliers → visa → retrieve`
- Add `visa_info` key to TripGraphState

**"Support international destinations in RAG"**
- Add documents to `rag_documents.py` for new countries
- Delete `rag_index/` folder so it rebuilds
- No code changes to the engine needed

**"Add streaming support to trip generation"**
- Change `call_groq_json` to `call_groq_stream` in `_generate_node`
- Return a generator instead of a string
- The router would need to use `StreamingResponse`

---

---

## FILE 2 — rag_engine.py

### Purpose
Implements a local RAG (Retrieval-Augmented Generation) system using FAISS.
Stores travel knowledge as vector embeddings, retrieves the most relevant
chunks for a given query, and reranks for diversity.

### Why RAG?
The LLM (Llama 3.1 8B) knows India travel in general but may:
- Hallucinate specific costs or timings
- Have outdated information
- Miss local nuances (Charminar crowd times, Goa monsoon shack closures)

RAG injects verified, specific facts from our knowledge base directly into
the prompt, grounding the LLM's output in real information.

---

### RAG Pipeline Overview

```
Query string
    ↓
_expand_query()        — add context-aware travel terms
    ↓
_embed([expanded_query]) — 384-dim vector via SentenceTransformers
    ↓
FAISS.search(k = top_k × 8)  — retrieve 48 candidates
    ↓
Hybrid scoring:
  base_score    = FAISS cosine similarity
  lexical_bonus = Jaccard overlap on token sets
  city_bonus    = +0.06 if destination mentioned in chunk metadata
  source_bonus  = +0.04 if chunk is from live online memory
  diversity_pen = -0.025 for repeat document titles
    ↓
Sort by final score
    ↓
_mmr_select(top_k)     — Maximal Marginal Relevance reranking
    ↓
Return List[RAGResult]
```

---

### Embedding Model

**Primary: all-MiniLM-L6-v2 (SentenceTransformers)**
- 384-dimensional embeddings
- Trained on semantic similarity tasks
- Runs fully locally — no API key, no network call
- ~22MB model file, loads in ~1 second

**Why all-MiniLM-L6-v2 over larger models?**
- Fast enough for real-time use
- 384 dims is sufficient for paragraph-level semantic matching
- Larger models (MPNET, e5-large) are slower with marginal gains for our use case

**Fallback: HashingEmbedder**
If SentenceTransformers is unavailable (model not downloaded, import error):
```python
class HashingEmbedder:
    def encode(self, texts):
        # For each token in text:
        #   blake2b(token) → 8 bytes
        #   bytes[0:4] → bucket index (0-383)
        #   bytes[4] % 2 → sign (+1 or -1)
        # Accumulate into 384-dim vector
        # L2-normalize
```
This is deterministic (same text → same vector), fast (no ML), and
enables the planner to work without any model download. Quality is
lower but functional.

---

### Title-Prefixed Chunk Embedding

Chunks are embedded as `"Title: chunk text"` rather than just `"chunk text"`.

```python
def _embed_with_title(chunks, titles):
    prefixed = [f"{t}: {c}" for t, c in zip(titles, chunks)]
    return self._embed(prefixed)
```

**Why?** The embedding model understands context. "Hyderabad City Guide: The Hyderabad Metro covers HITEC City..." produces a better topical embedding than just "The Hyderabad Metro covers HITEC City..." — the title anchors the chunk to its topic.

The **stored text** (in metadata) remains the original chunk without the title prefix, so retrieved text is clean.

---

### Chunking Strategy

```python
def _chunk_text(text, chunk_size=850, overlap=140):
    # 1. Collapse all whitespace to single spaces
    # 2. If text fits in one chunk, return as-is
    # 3. Sliding window of chunk_size characters
    #    At window boundary, look for ". " or "; " or ", "
    #    If found at > 55% of chunk_size, split there (semantic boundary)
    #    Otherwise hard-split at chunk_size
    # 4. Next window starts at (end - overlap)
    #    Overlap = 140 chars ≈ 1-2 sentences of shared context
```

**Why overlap?** Without overlap, a sentence split across two chunks would be truncated and lose meaning. With 140-char overlap, each chunk shares 1-2 sentences with its neighbor, preserving context continuity.

**Why 850 chars?** Roughly 120-150 words — enough for a coherent paragraph but small enough that each chunk is topically focused. Larger chunks dilute the semantic signal; smaller chunks lose context.

---

### FAISS Index

**Type: IndexFlatIP (Flat Inner Product)**
- Exact nearest-neighbor search (not approximate)
- Inner product = cosine similarity when vectors are L2-normalized (which we do)
- 384 dimensions × ~35 vectors = tiny index, exact search is fine

**Why not IVF or HNSW (approximate)?**
Those are for millions of vectors. We have ~35-100 chunks. Exact search
on this scale takes microseconds — no approximation needed.

**Persistence:**
```
rag_index/
├── faiss.index     → binary vector index
├── metadata.pkl    → list of {text, metadata{title, source, city, chunk}}
├── manifest.json   → SHA-256 fingerprint of all docs + config
└── online_memory.jsonl → live search context cache (one JSON per line)
```

**Cache invalidation via manifest:**
On startup, `load_docs()` computes a SHA-256 of all document content + embedding model name + chunk config. If it matches `manifest.json`, skip re-indexing. If different (e.g. you added a document), rebuild. This makes cold starts fast.

---

### Query Expansion

```python
def _expand_query(query):
    # Add "india travel guide" if no travel domain words present
    # Add "budget INR" if no cost words present
    # Add "local transport" if no transport words present
    # Add "morning timing crowd" if query mentions a landmark type
```

**Why context-aware instead of fixed terms?**
The old approach appended all 13 travel terms to every query. This diluted the destination signal. "Hyderabad Charminar" + 13 generic terms makes the embedding look like a generic travel planning query rather than a Hyderabad-specific query.

The new approach adds only what's missing from the query — preserving the specific signal while anchoring to the travel domain.

---

### Hybrid Scoring

```
final_score = semantic_score + lexical_bonus + city_bonus + source_bonus - diversity_penalty
```

**semantic_score:** FAISS inner product (cosine similarity). Captures meaning, not just keywords.

**lexical_bonus:** Jaccard similarity on 3+ character token sets:
```python
lexical_overlap = len(query_terms & chunk_terms)
lexical_bonus   = min(lexical_overlap * 0.012, 0.16)
```
Catches cases where semantic similarity misses exact keyword matches (place names, INR amounts).

**city_bonus (+0.06):** If any 4+ character token from the query appears in the chunk's title or city metadata. Ensures Hyderabad-specific guides rank above generic India guides for a Hyderabad query.

**source_bonus (+0.04):** Live online memory chunks (from actual web searches) get a small bonus over static knowledge base chunks. Fresher information is slightly preferred.

**diversity_penalty (-0.025):** If the same document title has already been seen in the candidate set, penalize repeat entries. Soft penalty — doesn't exclude, just pushes down.

---

### MMR Reranking (Maximal Marginal Relevance)

```python
def _mmr_select(candidates, top_k):
    selected = []
    while remaining and len(selected) < top_k:
        for item in remaining:
            similarity_to_selected = max(jaccard(item, chosen) for chosen in selected)
            mmr_score = (λ × item.score) - ((1-λ) × similarity_to_selected)
        select item with highest mmr_score
```

**λ = 0.72:** 72% weight on relevance, 28% on diversity.

**Why MMR?**
Without it, the top-6 results might all be from the same document (e.g. 6 chunks of "Hyderabad City Guide"). MMR ensures diversity — you get Hyderabad transport, Hyderabad food, Hyderabad attractions as separate insights rather than 6 variations of the same paragraph.

**Jaccard similarity:** Used instead of cosine similarity between embeddings because:
- Faster to compute (set intersection / union)
- Works on already-retrieved text (no second embedding call)
- Sufficient for diversity detection at this scale

---

### Online Memory

```python
rag.remember_online_context(
    query="weather in Hyderabad July",
    context={"temp": 32, "humidity": 85},
    city="hyderabad",
    source="serpapi"
)
```

**What it does:**
1. SHA-256 fingerprints content to check for duplicates
2. Appends to `online_memory.jsonl` (survives process restarts)
3. Immediately adds to live FAISS index via `add_documents()`

**Why?**
Live search results fetched for one user's trip can benefit future users planning similar trips. If someone searched "weather in Goa in December," that result is cached and immediately retrievable for the next person planning a Goa trip — without another API call.

**On cold start:**
`_load_memory_docs()` reads the last 350 lines from `online_memory.jsonl` and re-indexes them. This rehydrates the "learned" context from past trips.

---

### Key Libraries in rag_engine.py

**FAISS:**
- What: Facebook AI Similarity Search — fast vector nearest-neighbor search
- Why: Local, no external service, battle-tested, Python bindings
- Alternative: Chroma, Pinecone, Weaviate — all require external services or Docker
- Disadvantage: No built-in metadata filtering; we implement our own

**SentenceTransformers:**
- What: Library for computing dense sentence embeddings
- Why: High-quality semantic embeddings, runs locally, many pretrained models
- Alternative: OpenAI embeddings API (paid, requires network), BERT (raw, harder to use)
- Disadvantage: First load downloads ~22MB model; slow on CPU for large batches

---

### Common Bugs in rag_engine.py

1. **Index out of sync with docs** — if you change `rag_documents.py` but the old `faiss.index` is still on disk, the manifest hash won't match and it will rebuild. If it doesn't rebuild, delete the `rag_index/` folder manually.

2. **HashingEmbedder producing poor results** — if SentenceTransformer fails to load and falls back to HashingEmbedder, retrieval quality drops significantly. Check `rag._embedder.name` — if it's "local-hashing-embedder", the ML model didn't load.

3. **Empty results despite documents** — `state` filter in `retrieve()` is too strict. If you pass `state="Telangana"` but documents have `state=""`, nothing matches. Always check what's in your metadata. The pipeline uses `state=None` which bypasses this filter.

4. **Memory growing unbounded** — `online_memory.jsonl` appends forever. `RAG_MEMORY_LIMIT=350` controls how many lines are loaded on startup, but the file itself keeps growing. Rotate or trim the file periodically in production.

---

### Interview Questions — rag_engine.py

1. **"What is RAG and why does your project use it?"**
   > RAG stands for Retrieval-Augmented Generation. Instead of relying solely on the LLM's training knowledge, we store factual travel knowledge in a local vector database (FAISS) and inject the most relevant facts into each prompt. This reduces hallucination — the LLM has verified data about Charminar entry costs, Goa beach shack timings, Bangalore traffic patterns — rather than guessing.

2. **"How does FAISS work?"**
   > FAISS stores documents as dense vectors (384-dimensional arrays). A query is embedded into the same space. FAISS computes cosine similarity between the query vector and all document vectors and returns the top-k closest matches. It's essentially a very fast nearest-neighbor search in high-dimensional space.

3. **"What is MMR reranking and why do you use it?"**
   > Maximal Marginal Relevance balances relevance and diversity. Without it, the top results might all be very similar — e.g. 6 chunks from the same Hyderabad guide. MMR iteratively selects the next result that is both relevant to the query AND different from already-selected results. We use λ=0.72 meaning 72% relevance, 28% diversity.

4. **"What is the difference between semantic search and lexical search? Why do you use both?"**
   > Semantic search (FAISS + embeddings) understands meaning — "cheap accommodation" matches "budget hotel". Lexical search (Jaccard on tokens) matches exact words — "Charminar" in the query matches "Charminar" in the chunk. We use both because semantic search can miss specific place names or INR amounts, while lexical search misses synonyms. Combining them gives better recall.

5. **"How do you handle the case when no relevant documents exist?"**
   > `retrieve()` returns an empty list if the FAISS index has zero vectors. `_retrieve_node` calls `_compress_rag_results()` which returns an empty list. The LLM prompt receives `rag: []` and falls back to generating from provider data alone. The trip still generates — RAG is augmentation, not a hard dependency.

6. **"What is chunk overlap and why is it important?"**
   > Overlap means consecutive chunks share 140 characters (~1-2 sentences). Without overlap, a sentence split across a chunk boundary would be truncated in both chunks. With overlap, each chunk contains its neighbor's context, making each chunk more semantically complete and independently meaningful.

---

---

## FILE 3 — groq_llm.py

### Purpose
Provides a singleton Groq client and helper functions for text generation and streaming.
Used by `rag_engine.py`'s summarize path and by `nearby_service.py`.
The main planning pipeline in `agent_core.py` has its own wrapper functions
with planning-specific settings (lower temperature, JSON mode).

### Key Code

```python
_groq_client: Groq | None = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client
```

**Singleton pattern:** The Groq client maintains an HTTP connection pool. Creating it once and reusing avoids connection overhead on every LLM call.

```python
def call_groq(prompt, system_prompt=None, model=None):
    # temperature=0.4, max_tokens=1024
    # Used for: RAG summarization, nearby explanations

def call_groq_stream(prompt, model=None):
    # Generator: yields text chunks as LLM streams
    # temperature=0.4, max_tokens=2048
    # Used for: Travel HQ streaming command interface
```

### Why Groq over OpenAI?
- Free tier with no credit card: 30 req/min, 14,400 req/day
- Fastest inference available (uses custom LPU hardware)
- Llama 3.1 8B is capable enough for structured itinerary generation
- OpenAI GPT-4o is more capable but costs money and has rate limits

### Why Llama 3.1 8B?
- Small enough to fit in Groq's free tier
- Capable of following complex JSON schema instructions
- Fast: typically returns in 1-3 seconds
- Alternative: Llama 3.1 70B is more capable but hits token/minute limits faster

### Interview Questions — groq_llm.py

1. **"Why did you choose Groq over the OpenAI API?"**
   > Groq offers a free tier with no credit card required, making it accessible for a demo project. It uses custom LPU (Language Processing Unit) hardware that gives it the fastest inference speed available. The quality of Llama 3.1 8B is sufficient for structured itinerary generation with clear prompt instructions.

2. **"What is the singleton pattern here and why use it?"**
   > The `_groq_client` module-level variable holds one Groq instance across the entire process lifetime. The `get_groq_client()` function creates it only on the first call. This avoids re-initializing the HTTP connection pool on every LLM call, which is expensive.

3. **"Why use streaming for the Travel HQ but not for trip generation?"**
   > Trip generation produces a single structured JSON blob — streaming JSON mid-generation would break parsing. The Travel HQ is a conversational interface where the user expects to see words appearing progressively (better UX). Streaming is appropriate when output is consumed incrementally by humans, not when it needs to be parsed as a whole.

---

## FILE 4 — rag_documents.py

### Purpose
A static Python dictionary containing 21 structured travel knowledge documents.
This is the RAG knowledge base — the facts the LLM is grounded in.

### Structure
```python
india_travel_docs = {
    "Document Title": """
    Multi-paragraph content with specific facts...
    """,
    ...
}
```

When `load_docs(india_travel_docs)` is called, this dict is:
1. Normalized into a list of `{title, content, source}` dicts
2. Each document is chunked into 850-char pieces
3. Each chunk is embedded as `"Title: chunk text"`
4. Vectors stored in FAISS, text stored in metadata.pkl

### What Makes a Good RAG Document?
- **Specific facts:** INR costs, timings, crowd patterns — not just "Hyderabad is nice"
- **Self-contained sentences:** Each sentence should make sense out of context (after chunking)
- **Consistent terminology:** Use the same city/area names as the place APIs return

### Interview Questions — rag_documents.py

1. **"How do you ensure RAG facts are accurate?"**
   > These are curated facts based on common travel knowledge — entry costs, transport routes, seasonal timing. For a production system, you'd source from authoritative travel APIs or regularly update from travel databases. The key benefit is that even approximate facts are better than the LLM hallucinating completely wrong information.

2. **"How would you keep this knowledge base updated?"**
   > Three approaches: (1) Add a web scraper that periodically updates the static docs. (2) Use the online memory feature — live search results are automatically stored in FAISS and retrieved in future queries. (3) Build an admin endpoint to POST new documents to `rag.add_documents()` at runtime without restart.

---

## FILE 5 — trip_payload.py

### Purpose
Contains all budget math, data normalization, and fallback plan generation.
Deliberately kept out of `agent_core.py` to keep that file focused on orchestration.

### Key Functions

**`build_budget_profile(days, passengers, cabin_class, max_budget, transport_mode)`**
Splits the total budget into per-category targets:
- Flights: 30% of total / passengers
- Hotels: 25% of total / nights
- Transport: 10% of total / passengers
- Food + Activities: remaining / days

**`extract_budget_constraints(user_request, current_total)`**
Parses INR values from natural language:
```
"under 50000"           → target_total=50000
"₹30k total"            → target_total=30000
"5000 per night"        → target_hotel_nightly=5000
"cheaper flights"       → no specific value, use percentage reduction
```

**`apply_budget_preferences(plan, user_request)`**
Post-processing step that enforces budget constraints on the generated itinerary.
If the LLM generated a hotel at ₹8000/night but the budget says ₹3000, this function corrects it.

**`build_fallback_trip_plan(state, source_payload, error_msg)`**
If the LLM fails, this generates a complete deterministic itinerary from provider data.
No LLM call. Uses seed data for the destination, formats it into the `travelai_v11` schema.

**`destination_place_seed(city)`**
Returns hardcoded seed places for well-known cities. Used as fallback when Google Maps returns no results.

### Interview Questions — trip_payload.py

1. **"What is your fallback if the LLM call fails?"**
   > `build_fallback_trip_plan()` generates a complete itinerary from provider data (flights, hotels, attractions) using deterministic logic — no LLM required. The output follows the same JSON schema. Users still get a usable trip plan, just without personalized descriptions and activity sequencing.

2. **"How do you parse budget from natural language like '₹30k'?"**
   > `extract_budget_constraints()` uses regex patterns to extract numbers and multipliers. "30k" → 30,000, "1.5L" → 150,000 (lakh), "30000" → 30000. It handles ₹ symbol, "INR" prefix, "k" and "L" suffixes, and phrases like "under", "within", "around".

---

## FILE 6 — zapi/ (External API Integrations)

### What is zapi/?
A collection of API wrapper modules. Each file wraps one external service with:
- TTL caching to avoid repeated calls
- Timeout handling
- Fallback/estimate generation when keys are missing
- Normalization to a consistent output format

### flight_api.py
- Provider: SerpAPI Google Flights
- Cache key: origin + destination + dates + passengers
- Returns: `[{airline, from, to, departure, arrival, duration, price_per_person}]`
- Fallback: Generates budget estimates based on distance and cabin class

### hotel_api.py
- Provider: SerpAPI Google Hotels
- Cache key: city + checkin + checkout + adults
- Returns: `[{name, area, address, rating, price_per_night}]`
- Fallback: Budget estimates based on destination tier

### maps_api.py
- Provider: Google Maps Places API
- `search_google_places(city, query_type)` — text search for restaurants/attractions
- `search_google_places_nearby(lat, lng, query, radius)` — used by Nearby Planner
- `get_distance(origins, destinations)` — Distance Matrix API for Nearby Planner routing
- Returns normalized `{name, address, rating, price_level, types}`

### tools_weather.py
- Provider: OpenWeatherMap Current Weather
- Cache TTL: 1 hour (weather changes more frequently than prices)
- Returns compact string: "32°C, Partly Cloudy, Humidity: 75%"

### transport_api.py
- Searches for trains and buses between city pairs
- Returns `[{mode, route, duration, price_per_person}]`

### Interview Questions — zapi/

1. **"What happens if all your external APIs are unavailable?"**
   > Each API function has a fallback path. `flight_api.py` generates budget estimates based on the route. `hotel_api.py` generates estimates based on destination category. `maps_api.py` falls back to `destination_place_seed()` — hardcoded places for known cities. The trip pipeline always produces output.

2. **"Why wrap all external calls in the zapi/ folder instead of calling them directly?"**
   > Separation of concerns and testability. `agent_core.py` doesn't know or care how flights are fetched. You can swap SerpAPI for another provider by changing only `flight_api.py`. You can also mock `zapi/` functions in tests without mocking the entire pipeline.

---

## FILE 7 — web_search.py

### Purpose
Wraps SerpAPI and Serper for general web search queries.
Used by: India Pulse trends, Nearby Planner context generation, and online memory.

```python
def travel_web_search_json(query, max_results=5):
    # Try SerpAPI first (if SERPAPI_KEY set)
    # Fall back to Serper (if SERPER_API_KEY set)
    # Cache result for WEB_SEARCH_CACHE_TTL seconds
    # Return list of {title, snippet, link}
```

**Why two providers?**
Redundancy. If SerpAPI is down or rate-limited, Serper handles the request.
Both return similar result formats — the normalization layer hides the difference.

---

## Groq Free Tier Management

Every design decision in the AI core is shaped by staying within Groq's free tier:

| Limit | Value | How we manage it |
|---|---|---|
| Requests/minute | 30 | 1-2 calls per trip, never batched |
| Tokens/minute | 6,000 | Prompt compressed to ~1,500 input tokens |
| Output tokens | max 4,500 | `PLANNER_MAX_TOKENS=4500` env var |

**Token budget per trip generation call:**
- System/instruction section: ~400 tokens
- Trip metadata: ~100 tokens
- Provider data (compressed): ~400 tokens
- RAG insights (7 × 140 chars): ~250 tokens
- Output schema template: ~200 tokens
- Rules: ~300 tokens
- **Total input: ~1,650 tokens**
- **Max output: 2,500 tokens** (itinerary JSON)
- **Total per call: ~4,150 tokens** — well within 6,000/minute

---

## Full Data Flow Diagram

```
User: "Plan Hyderabad → Goa, 3 days, ₹40,000, 2 people"
                │
                ▼
        agent_core.TravelAI.plan_full_trip()
                │
    ┌───────────▼───────────┐
    │     resolve_node       │
    │  "hyd" → "hyderabad"  │
    │  "goa" → "goa" / GOI  │
    │  days = 3              │
    │  mode = coastal_relaxed│
    └───────────┬───────────┘
                │
    ┌───────────▼────────────────────────┐
    │          supplier_node             │
    │  asyncio.gather(                   │
    │    flights: HYD→GOI ₹4,800/pp     │
    │    hotels: Sea View ₹2,200/night   │
    │    restaurants: 8 places           │
    │    attractions: 10 places          │
    │    weather: 30°C, Sunny            │
    │    transport: bus ₹800             │
    │  )                                 │
    │  classify + cluster + budget_profile│
    └───────────┬────────────────────────┘
                │
    ┌───────────▼────────────────────────┐
    │          retrieve_node (RAG)        │
    │  query = "goa travel guide         │
    │           Baga Sea View Curlies     │
    │           timing crowd transport"  │
    │                                    │
    │  FAISS search (48 candidates)      │
    │  Hybrid score + MMR rerank         │
    │                                    │
    │  rag_context = [                   │
    │    "Goa beach shacks serve grilled │
    │     seafood for INR 400-1000",     │
    │    "Renting a scooter is the best  │
    │     way to explore: INR 300-500/d",│
    │    ...7 total insights             │
    │  ]                                 │
    └───────────┬────────────────────────┘
                │
    ┌───────────▼────────────────────────┐
    │          quality_node               │
    │  All keys present ✓                │
    │  quality_notes = [                 │
    │    "APIs finished before RAG",     │
    │    "Use compressed provider facts" │
    │  ]                                 │
    └───────────┬────────────────────────┘
                │
    ┌───────────▼────────────────────────┐
    │          generate_node              │
    │  Assemble prompt:                  │
    │    Trip={"from":"Hyderabad",...}    │
    │    Src={flights,hotels,rag,...}     │
    │    Rules=[45 formatting rules]     │
    │                                    │
    │  call_groq_json(prompt)            │
    │  → Groq Llama 3.1 8B              │
    │  → Structured JSON                 │
    │                                    │
    │  complete_trip_plan()              │
    │  → Fill gaps, validate schema      │
    └───────────┬────────────────────────┘
                │
                ▼
        itinerary JSON string
        saved to SQLite, returned to user
```
