import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("SERPAPI_KEY")


def get_distance(origin: str, destination: str):
    """
    Returns driving distance and duration between two places using SerpAPI Google Maps.
    Example: origin="Hyderabad airport", destination="Charminar"
    """

    url = "https://serpapi.com/search"

    params = {
        "engine": "google_maps",
        "type": "distance_matrix",
        "origins": origin,
        "destinations": destination,
        "api_key": SERPAPI_KEY,
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        row = (data.get("distance_matrix", {})
                    .get("rows", [{}])[0]
                    .get("elements", [{}])[0])

        distance = row.get("distance", {}).get("text")
        duration = row.get("duration", {}).get("text")

        return {
            "origin": origin,
            "destination": destination,
            "distance": distance,
            "duration": duration,
        }

    except:
        return {"error": "Could not fetch distance"}
