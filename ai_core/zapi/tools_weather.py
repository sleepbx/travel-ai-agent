import os

import requests
from dotenv import load_dotenv

from cache_utils import TTLCache

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_TIMEOUT = int(os.getenv("OPENWEATHER_TIMEOUT", "5"))
_weather_cache = TTLCache(ttl_seconds=int(os.getenv("WEATHER_CACHE_TTL", "3600")))


def get_weather(city: str) -> str:
    """
    Simple wrapper around OpenWeather current weather API.
    Returns a short human-readable summary string.
    """
    if not OPENWEATHER_API_KEY:
        return "Weather API key missing. Please set OPENWEATHER_API_KEY in .env."

    city = city.strip()
    if not city:
        return "Please provide a valid city name."

    cache_key = city.lower()
    cached = _weather_cache.get(cache_key)
    if cached:
        return cached

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        resp = requests.get(url, timeout=OPENWEATHER_TIMEOUT)

        if resp.status_code != 200:
            return f"Could not fetch weather for '{city}'. (status {resp.status_code})"

        data = resp.json()
        name = data.get("name", city)
        country = data.get("sys", {}).get("country", "")
        main = data.get("weather", [{}])[0].get("description", "unknown").capitalize()
        temp = data.get("main", {}).get("temp")
        feels = data.get("main", {}).get("feels_like")
        humidity = data.get("main", {}).get("humidity")

        result = (
            f"Weather in {name}, {country}: {main}. "
            f"Temperature {temp} C (feels like {feels} C). "
            f"Humidity {humidity}%."
        )
        _weather_cache.set(result, cache_key)
        return result
    except Exception as e:
        return f"Error fetching weather: {e}"
