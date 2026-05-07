# agent_core.py — TravelAI (restaurant-enforced + refinement FIXED)

import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from groq import Groq
from difflib import get_close_matches

from ai_core.rag_engine import RAGEngine
from ai_core.rag_documents import india_travel_docs
from ai_core.zapi.tools_weather import get_weather
from ai_core.zapi.flight_api import search_flights_serpapi
from ai_core.zapi.hotel_api import search_hotels_serpapi
from ai_core.zapi.tripadvisor_api import search_tripadvisor, extract_restaurants


# -------------------------------------------------
# ENV
# -------------------------------------------------
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY missing")

groq_client = Groq(api_key=GROQ_API_KEY)


def call_groq(prompt: str) -> str:
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2048,
    )
    return res.choices[0].message.content.strip()


# -------------------------------------------------
# LOCATION RESOLVER
# -------------------------------------------------
class LocationResolver:
    CITY_TO_IATA = {
        "hyderabad": "HYD",
        "delhi": "DEL",
        "mumbai": "BOM",
        "bangalore": "BLR",
        "chennai": "MAA",
        "kolkata": "CCU",
        "goa": "GOI",
        "kochi": "COK",
        "jaipur": "JAI",
    }

    STATE_TO_CITY = {
        "telangana": "hyderabad",
        "andhra pradesh": "visakhapatnam",
        "tamil nadu": "chennai",
        "karnataka": "bangalore",
        "kerala": "kochi",
        "maharashtra": "mumbai",
        "rajasthan": "jaipur",
        "west bengal": "kolkata",
        "goa": "goa",
        "delhi": "delhi",
    }

    ALIASES = {
        "hyd": "hyderabad",
        "blr": "bangalore",
        "bom": "mumbai",
        "mum": "mumbai",
        "del": "delhi",
        "maa": "chennai",
        "vizag": "visakhapatnam",
    }

    @classmethod
    def resolve(cls, text: str) -> str:
        t = text.strip().lower()

        if t in cls.ALIASES:
            return cls.ALIASES[t]
        if t in cls.CITY_TO_IATA:
            return t
        if t in cls.STATE_TO_CITY:
            return cls.STATE_TO_CITY[t]

        match = get_close_matches(t, cls.CITY_TO_IATA.keys(), n=1, cutoff=0.75)
        if match:
            return match[0]

        raise ValueError(f"Unsupported location: {text}")


# -------------------------------------------------
# TRAVEL AI
# -------------------------------------------------
class TravelAI:
    def __init__(self):
        self.rag = RAGEngine()
        self.rag.load_docs(india_travel_docs)
        self.resolver = LocationResolver()

    def _days(self, s: str, e: str) -> int:
        return (datetime.strptime(e, "%Y-%m-%d") -
                datetime.strptime(s, "%Y-%m-%d")).days + 1

    # -------------------------------------------------
    # MAIN PLANNER
    # -------------------------------------------------
    def plan_full_trip(
        self,
        origin_city: str,
        destination_city: str,
        depart_date: str,
        return_date: str,
        passengers: int = 2,
        cabin_class: str = "economy",
        interests: str = "sightseeing",
        max_budget: Optional[int] = None,
    ) -> str:

        try:
            origin = self.resolver.resolve(origin_city)
            dest = self.resolver.resolve(destination_city)
        except ValueError as e:
            return f"❌ {e}"

        total_days = self._days(depart_date, return_date)

        weather = get_weather(dest)

        flights = search_flights_serpapi(
            origin_airport=self.resolver.CITY_TO_IATA[origin],
            destination_airport=self.resolver.CITY_TO_IATA[dest],
            depart_date=depart_date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
        )

        hotels = search_hotels_serpapi(
            city=dest,
            checkin=depart_date,
            checkout=return_date,
            adults=passengers,
            rooms=1,
        )

        ta_raw = search_tripadvisor(
            city=dest,
            interests="restaurants fine dining",
            max_results=20,
        )

        restaurants = extract_restaurants(ta_raw)

        rag_context = self.rag.search(
            f"Travel tips, safety, best time, food culture of {dest}",
            summarize=True,
        )

        prompt = f"""
You are an expert India travel planner.

FROM: {origin.title()}
TO: {dest.title()}
TOTAL DAYS: {total_days}
BUDGET: {max_budget if max_budget else "Not specified"}

RAG INFO:
{rag_context}

AVAILABLE RESTAURANTS (MANDATORY):
{restaurants}

STRICT RULES:
- Use ONLY restaurant names above
- NO street food
- Always include INR cost

FOR EACH DAY:

Day X:
Places:
- Place — Entrance fee (INR)

Travel:
- Transport — Cost (INR)

Food:
- Breakfast: Restaurant — Cost (INR)
- Lunch: Restaurant — Cost (INR)
- Dinner: Restaurant — Cost (INR)

Daily Estimated Cost: INR ___
"""

        return call_groq(prompt)

    # -------------------------------------------------
    # 🔥 REFINEMENT (FIXED)
    # -------------------------------------------------
    def refine_itinerary(self, existing_itinerary: str, user_request: str) -> str:
        prompt = f"""
You are an expert India travel planner.

CURRENT ITINERARY:
{existing_itinerary}

USER REQUEST:
{user_request}

RULES:
- Modify ONLY what the user asked
- Keep restaurant names realistic
- Preserve daily cost structure
- Return FULL updated itinerary

UPDATED ITINERARY:
"""
        return call_groq(prompt)
