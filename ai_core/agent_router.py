# agent_router.py

import re

# -------------------- External Tools --------------------
from zapi.tools_weather import get_weather
from tools_search import web_search


class ToolRouter:
    """
    Intelligence layer that decides:
    - which tools to call
    - in what order
    - how to combine results

    Tools:
    - Weather
    - Web Search
    - RAG (handled in TravelAI)
    """

    def detect_intent(self, query: str) -> dict:
        query_lower = query.lower()

        intent = {
            "use_weather": False,
            "use_search": False,
            "use_rag": False,
            "city": None,
        }

        # -------------------- Weather intent --------------------
        if any(word in query_lower for word in ["weather", "temperature", "climate"]):
            intent["use_weather"] = True

        # -------------------- City extraction --------------------
        match = re.search(r"in\s+([a-zA-Z\s]+)", query_lower)
        if match:
            intent["city"] = match.group(1).strip().title()

        # -------------------- Search intent --------------------
        if any(word in query_lower for word in ["top places", "best places", "things to do"]):
            intent["use_search"] = True

        # -------------------- Trip planning intent --------------------
        if any(word in query_lower for word in ["plan", "itinerary", "trip"]):
            intent["use_weather"] = True
            intent["use_search"] = True
            intent["use_rag"] = True

        # -------------------- Knowledge / RAG intent --------------------
        if any(word in query_lower for word in ["best time", "history", "culture", "tips", "safety"]):
            intent["use_rag"] = True

        # -------------------- Fallback --------------------
        if not any([intent["use_weather"], intent["use_search"], intent["use_rag"]]):
            intent["use_rag"] = True

        return intent

    def run_tools(self, intent: dict, query: str) -> dict:
        results = {}
        city = intent.get("city")

        if intent.get("use_weather") and city:
            try:
                results["weather"] = get_weather(city)
            except Exception as e:
                results["weather"] = f"Weather unavailable: {e}"

        if intent.get("use_search"):
            try:
                results["search"] = web_search(query)
            except Exception as e:
                results["search"] = f"Search failed: {e}"

        # RAG is executed inside TravelAI
        return results
