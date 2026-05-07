import os
import requests
from dotenv import load_dotenv

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def search_flights_serpapi(
    origin_airport: str,
    destination_airport: str,
    depart_date: str,
    return_date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    currency: str = "INR",
):
    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY missing"}

    params = {
        "engine": "google_flights",
        "departure_id": origin_airport,
        "arrival_id": destination_airport,
        "outbound_date": depart_date,
        "return_date": return_date,
        "adults": passengers,
        "currency": currency,
        "api_key": SERPAPI_KEY,
    }

    resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
    data = resp.json()

    flights_raw = data.get("best_flights", [])[:3]

    flights = []
    for f in flights_raw:
        leg = f["flights"][0]
        flights.append({
            "airline": leg.get("airline"),
            "flight_number": leg.get("flight_number"),
            "from": leg["departure_airport"]["id"],
            "to": leg["arrival_airport"]["id"],
            "departure": leg["departure_airport"]["time"],
            "arrival": leg["arrival_airport"]["time"],
            "duration_min": leg.get("duration"),
            "price": f.get("price"),
        })

    return flights


