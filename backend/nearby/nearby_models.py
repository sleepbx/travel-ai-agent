from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = 12.9716
    lng: float = 77.5946


class NearbyPlanRequest(BaseModel):
    location: str = ""
    detected_city: str = ""
    coordinates: Coordinates = Field(default_factory=Coordinates)
    duration: str = "4 Hours"
    moods: list[str] = Field(default_factory=lambda: ["Food", "Hidden Gems"])
    budget: int = 1500
    transport: str = "Car"
    radius: str = "Within 20 km"
    group_type: str = "Couple"
    surprise_me: bool = True


class NearbySummary(BaseModel):
    title: str
    location: str
    total_duration: str
    estimated_budget: str
    total_travel_distance: str
    weather_snapshot: str
    best_time_to_leave: str
    vibe_tags: list[str]
    magic_touch: str


class NearbyStop(BaseModel):
    id: str
    sequence: int
    title: str
    image: str
    description: str
    eta: str
    ideal_visit_duration: str
    estimated_cost: str
    travel_time_to_next: str
    crowd_level: str
    weather_suitability: str
    opening_hours: str
    why_ai_picked_this: str
    mood_tags: list[str]
    coordinates: Coordinates
    backup_plan: str


class NearbyTiming(BaseModel):
    generated_at: str
    best_leave: str
    golden_hour: str
    nightlife_window: str
    traffic_note: str
    rainy_day_cutover: str


class NearbyCosts(BaseModel):
    food: str
    transport: str
    tickets: str
    shopping: str
    buffer: str
    total: str


class NearbyRoute(BaseModel):
    mode: str
    radius: str
    optimized_order: list[str]
    estimated_commute_time: str
    transport_aware_routing: str
    traffic_awareness: str
    map_coordinates: list[Coordinates]


class NearbyAlternate(BaseModel):
    id: str
    title: str
    budget: str
    duration: str
    description: str
    tags: list[str]


class NearbyPlanResponse(BaseModel):
    summary: NearbySummary
    stops: list[NearbyStop]
    timing: NearbyTiming
    costs: NearbyCosts
    route: NearbyRoute
    insights: list[str]
    alternates: list[NearbyAlternate]
    map_coordinates: list[Coordinates]
