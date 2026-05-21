"""
AI Adapter
No FastAPI imports here.
"""

from ai_core.agent_core import TravelAI


def generate_trip_itinerary(data) -> str:
    agent = TravelAI()

    return agent.plan_full_trip(
        origin_city=data.origin_city,
        destination_city=data.destination_city,
        depart_date=data.depart_date,
        return_date=data.return_date,
        passengers=data.passengers,
        cabin_class=data.cabin_class,
        transport_mode=getattr(data, "transport_mode", "flight"),
        interests=data.interests,
        max_budget=data.max_budget,
    )


def refine_trip_itinerary(existing_itinerary: str, user_request: str) -> str:
    agent = TravelAI()
    return agent.refine_itinerary(
        existing_itinerary=existing_itinerary,
        user_request=user_request,
    )
