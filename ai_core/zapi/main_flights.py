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
    cabin_class: str = "premium_economy",
    currency: str = "INR",
    max_results: int = 5,
):
    """
    Round-trip flight search using SerpAPI Google Flights engine.

    origin_airport  : "DEL"
    destination_airport : "HYD"
    depart_date     : "YYYY-MM-DD"
    return_date     : "YYYY-MM-DD"
    cabin_class     : "economy" | "premium_economy" | "business" | "first"
    """

    if not SERPAPI_KEY:
        return {"error": "SERPAPI_KEY missing in .env"}

    url = "https://serpapi.com/search"

    params = {
        "engine": "google_flights",
        "departure_id": origin_airport,
        "arrival_id": destination_airport,
        "outbound_date": depart_date,
        "return_date": return_date,
        "adults": passengers,
        "travel_class": {
            "economy": 1,
            "premium_economy": 2,
            "business": 3,
            "first": 4,
        }.get(cabin_class, 2),
        "type": 1,              # 1 = round trip
        "currency": currency,
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "body": resp.text[:300]}

        data = resp.json()

        flights_raw = data.get("best_flights", []) or data.get("other_flights", [])
        flights_clean = []

        for f in flights_raw[:max_results]:
            segs = f.get("segments", [])
            if not segs:
                continue

            first_seg = segs[0]
            last_seg = segs[-1]

            airline = first_seg.get("airline", "Unknown airline")
            flight_number = first_seg.get("flight_number")
            outbound_time = first_seg.get("departure_time")
            inbound_time = last_seg.get("arrival_time")
            duration = f.get("total_duration")
            stops = f.get("stops")

            price = None
            cur = currency
            if isinstance(f.get("price"), dict):
                price = f["price"].get("raw")
                cur = f["price"].get("currency", cur)

            flights_clean.append(
                {
                    "airline": airline,
                    "flight_number": flight_number,
                    "outbound_departure": outbound_time,
                    "inbound_arrival": inbound_time,
                    "duration": duration,
                    "stops": stops,
                    "price": price,
                    "currency": cur,
                    "passengers": passengers,
                    "cabin_class": cabin_class,
                }
            )

        if not flights_clean:
            return {"error": "No flights returned", "raw": data}

        return {"flights": flights_clean}

    except Exception as e:
        return {"error": f"Exception when calling SerpAPI: {e}"}
