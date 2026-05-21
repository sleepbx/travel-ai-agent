import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote_plus


DEFAULT_TRAVEL_STYLE = "balanced_comfort"
BUDGET_REDUCTION_FACTOR = 0.82
LUXURY_INCREASE_FACTOR = 1.18
TRANSPORT_MODES = {"flight", "train", "bus"}
INVALID_FIELD_PHRASES = (
    "llm fill",
    "timing tba",
    "local attraction",
    "popular restaurant",
    "viewpoint stop",
    "local hops",
    "live duration unavailable",
)
VALID_ENTITY_TYPES = {
    "landmark",
    "fort",
    "museum",
    "café",
    "restaurant",
    "nightlife",
    "shopping",
    "park",
    "viewpoint",
    "market",
    "hotel",
    "transport",
    "heritage",
    "cultural area",
    "sunset",
    "food",
    "scenic walk",
}
ACTIVITY_BLOCKED_TYPES = {"restaurant", "hotel", "transport"}
MORNING_TYPES = {"landmark", "fort", "heritage", "viewpoint", "park"}
AFTERNOON_TYPES = {"museum", "market", "shopping", "café", "cultural area", "fort", "heritage"}
EVENING_TYPES = {"sunset", "food", "nightlife", "scenic walk", "café", "viewpoint", "market"}


def classify_entity(value: Any) -> str:
    if isinstance(value, dict):
        text = " ".join(
            _clean_text(value.get(key))
            for key in ("entity_type", "type", "category", "price_level", "name", "title")
            if value.get(key)
        ).lower()
    else:
        text = _clean_text(value).lower()

    checks = (
        ("hotel", ("hotel", "stay", "resort", "hostel")),
        ("restaurant", ("restaurant", "biryani", "thali", "dining", "kitchen", "dhaba", "eatery", "grill")),
        ("café", ("cafe", "café", "coffee", "bakery", "roastery")),
        ("nightlife", ("bar", "pub", "brewery", "club", "nightlife", "lounge")),
        ("fort", ("fort", "qila")),
        ("museum", ("museum", "gallery", "science centre", "planetarium")),
        ("market", ("market", "bazaar", "haat", "flea")),
        ("shopping", ("mall", "shopping", "store", "boutique")),
        ("park", ("park", "garden", "bagh", "sanctuary", "lake")),
        ("viewpoint", ("viewpoint", "point", "peak", "hill", "promenade", "drive")),
        ("sunset", ("sunset", "beach", "ghat", "riverfront", "seaface")),
        ("landmark", ("temple", "palace", "mahal", "gate", "monument", "tomb", "minar", "church", "cathedral")),
        ("heritage", ("heritage", "old city", "historic", "archaeological")),
        ("cultural area", ("art", "culture", "cultural", "street", "quarter")),
        ("transport", ("metro", "train", "bus", "cab", "airport", "station")),
    )
    for entity_type, terms in checks:
        if any(term in text for term in terms):
            return entity_type
    return "landmark"


def classify_entities(items: list[dict[str, Any]], fallback_type: str | None = None) -> list[dict[str, Any]]:
    classified = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        entity_type = fallback_type or classify_entity(item)
        cloned = {**item, "entity_type": entity_type if entity_type in VALID_ENTITY_TYPES else "landmark"}
        classified.append(cloned)
    return classified


def _slot_allows(slot: str, entity_type: str) -> bool:
    if entity_type in ACTIVITY_BLOCKED_TYPES:
        return False
    if slot == "Morning":
        return entity_type in MORNING_TYPES
    if slot == "Afternoon":
        return entity_type in AFTERNOON_TYPES
    if slot == "Night":
        return entity_type in EVENING_TYPES
    return False


def _invalid_field(value: Any) -> bool:
    text = _clean_text(value).lower()
    return not text or any(phrase in text for phrase in INVALID_FIELD_PHRASES)


def destination_mode_for(destination: Any) -> str:
    text = _clean_text(destination).lower()
    if any(name in text for name in ("goa", "puducherry", "pondicherry", "bali")):
        return "coastal_relaxed"
    if any(name in text for name in ("delhi", "agra", "jaipur", "varanasi")):
        return "urban_heritage"
    if "hyderabad" in text:
        return "food_culture"
    if any(name in text for name in ("bangalore", "bengaluru", "pune")):
        return "cafe_worklife"
    if any(name in text for name in ("mumbai", "kolkata", "chennai")):
        return "metro_culture"
    return "balanced_city"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_keep_order(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        k = _clean_text(item.get(key)).lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out


def place_image_url(
    title: Any,
    area: Any = "",
    destination: Any = "",
    category: Any = "",
    width: int = 1200,
    height: int = 800,
) -> str:
    title_text = _clean_text(title)
    if title_text.lower().startswith(("http://", "https://")):
        return title_text
    query = " ".join(
        part
        for part in (
            title_text,
            _clean_text(area),
            _clean_text(destination),
            _clean_text(category),
            "travel",
        )
        if part
    )
    return f"https://source.unsplash.com/{width}x{height}/?{quote_plus(query)}"


DESTINATION_PLACE_SEEDS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "goa": {
        "attractions": [
            {"name": "Fontainhas", "address": "Panjim", "category": "heritage"},
            {"name": "Fort Aguada", "address": "Candolim", "category": "fort"},
            {"name": "Chapora Fort", "address": "Vagator", "category": "view"},
            {"name": "Anjuna Flea Market", "address": "Anjuna", "category": "market"},
            {"name": "Basilica Bom Jesus", "address": "Old Goa", "category": "heritage"},
            {"name": "Miramar Beach", "address": "Panjim", "category": "beach"},
            {"name": "Dona Paula", "address": "Panjim", "category": "view"},
            {"name": "Divar Island", "address": "Old Goa", "category": "hidden"},
            {"name": "Reis Magos Fort", "address": "Verem", "category": "fort"},
            {"name": "Salim Ali Sanctuary", "address": "Chorao", "category": "nature"},
            {"name": "Palolem Beach", "address": "Canacona", "category": "beach"},
            {"name": "Arambol Beach", "address": "Arambol", "category": "beach"},
        ],
        "restaurants": [
            {"name": "Ritz Classic", "address": "Panjim", "price_level": "seafood"},
            {"name": "Vinayak Family Restaurant", "address": "Assagao", "price_level": "local"},
            {"name": "Mum's Kitchen", "address": "Panjim", "price_level": "Goan"},
            {"name": "Gunpowder", "address": "Assagao", "price_level": "coastal"},
            {"name": "Artjuna", "address": "Anjuna", "price_level": "cafe"},
            {"name": "Baba Au Rhum", "address": "Anjuna", "price_level": "cafe"},
            {"name": "Thalassa", "address": "Siolim", "price_level": "sunset"},
            {"name": "Martin's Corner", "address": "Betalbatim", "price_level": "Goan"},
        ],
    },
    "delhi": {
        "attractions": [
            {"name": "Humayun's Tomb", "address": "Nizamuddin", "category": "heritage"},
            {"name": "Lodhi Garden", "address": "Lodhi Estate", "category": "park"},
            {"name": "Red Fort", "address": "Old Delhi", "category": "fort"},
            {"name": "Chandni Chowk", "address": "Old Delhi", "category": "market"},
            {"name": "India Gate", "address": "Central Delhi", "category": "landmark"},
            {"name": "Qutub Minar", "address": "Mehrauli", "category": "heritage"},
        ],
        "restaurants": [
            {"name": "Karim's", "address": "Old Delhi", "price_level": "Mughlai"},
            {"name": "Saravana Bhavan", "address": "CP", "price_level": "South Indian"},
            {"name": "Big Chill", "address": "Khan Market", "price_level": "cafe"},
            {"name": "Indian Accent", "address": "Lodhi Road", "price_level": "premium"},
        ],
    },
    "agra": {
        "attractions": [
            {"name": "Taj Mahal", "address": "Taj Ganj", "category": "landmark"},
            {"name": "Agra Fort", "address": "Agra Fort Area", "category": "fort"},
            {"name": "Mehtab Bagh", "address": "Taj Ganj", "category": "sunset"},
            {"name": "Kinari Bazaar", "address": "Agra Fort Area", "category": "market"},
            {"name": "Itmad-ud-Daulah", "address": "Yamuna Bank", "category": "heritage"},
            {"name": "Taj Museum", "address": "Taj Ganj", "category": "museum"},
            {"name": "Sadar Bazaar", "address": "Sadar", "category": "shopping"},
            {"name": "Ram Bagh", "address": "Yamuna Bank", "category": "park"},
        ],
        "restaurants": [
            {"name": "Pinch of Spice", "address": "Civil Lines", "price_level": "Mughlai"},
            {"name": "Joney's Place", "address": "Taj Ganj", "price_level": "breakfast"},
            {"name": "Dasaprakash", "address": "Sadar", "price_level": "South Indian"},
            {"name": "Mama Chicken", "address": "Sadar", "price_level": "Mughlai"},
        ],
    },
    "jaipur": {
        "attractions": [
            {"name": "Amber Fort", "address": "Amer", "category": "fort"},
            {"name": "City Palace", "address": "Pink City", "category": "palace"},
            {"name": "Hawa Mahal", "address": "Pink City", "category": "landmark"},
            {"name": "Jantar Mantar", "address": "Pink City", "category": "heritage"},
            {"name": "Nahargarh Fort", "address": "Aravalli", "category": "view"},
            {"name": "Patrika Gate", "address": "Jawahar Circle", "category": "photo"},
        ],
        "restaurants": [
            {"name": "LMB", "address": "Johari Bazaar", "price_level": "Rajasthani"},
            {"name": "Spice Court", "address": "Civil Lines", "price_level": "Rajasthani"},
            {"name": "Tapri Central", "address": "C Scheme", "price_level": "cafe"},
            {"name": "Bar Palladio", "address": "Narain Niwas", "price_level": "premium"},
        ],
    },
    "mumbai": {
        "attractions": [
            {"name": "Gateway of India", "address": "Colaba", "category": "landmark"},
            {"name": "Kala Ghoda", "address": "Fort", "category": "art"},
            {"name": "Marine Drive", "address": "Churchgate", "category": "promenade"},
            {"name": "Bandra Fort", "address": "Bandra", "category": "view"},
            {"name": "Crawford Market", "address": "Fort", "category": "market"},
            {"name": "Sanjay Gandhi Park", "address": "Borivali", "category": "nature"},
        ],
        "restaurants": [
            {"name": "Kyani Bakery", "address": "Marine Lines", "price_level": "Irani"},
            {"name": "Britannia", "address": "Ballard Estate", "price_level": "Parsi"},
            {"name": "Swati Snacks", "address": "Tardeo", "price_level": "snacks"},
            {"name": "Bastian", "address": "Bandra", "price_level": "premium"},
        ],
    },
    "hyderabad": {
        "attractions": [
            {"name": "Charminar", "address": "Old City", "category": "landmark"},
            {"name": "Chowmahalla Palace", "address": "Old City", "category": "palace"},
            {"name": "Golconda Fort", "address": "Ibrahim Bagh", "category": "fort"},
            {"name": "Qutb Shahi Tombs", "address": "Ibrahim Bagh", "category": "heritage"},
            {"name": "Shilparamam", "address": "Hitec City", "category": "market"},
            {"name": "Hussain Sagar", "address": "Tank Bund", "category": "lake"},
        ],
        "restaurants": [
            {"name": "Shah Ghouse", "address": "Tolichowki", "price_level": "biryani"},
            {"name": "Cafe Niloufer", "address": "Lakdikapul", "price_level": "chai"},
            {"name": "Paradise", "address": "Secunderabad", "price_level": "biryani"},
            {"name": "Jewel of Nizam", "address": "Golkonda", "price_level": "premium"},
        ],
    },
    "bangalore": {
        "attractions": [
            {"name": "Cubbon Park", "address": "CBD", "category": "park"},
            {"name": "Bangalore Palace", "address": "Vasanth Nagar", "category": "palace"},
            {"name": "KR Market", "address": "Chickpet", "category": "market"},
            {"name": "Lalbagh", "address": "Mavalli", "category": "garden"},
            {"name": "Church Street", "address": "CBD", "category": "food"},
            {"name": "Ulsoor Lake", "address": "Ulsoor", "category": "lake"},
        ],
        "restaurants": [
            {"name": "CTR", "address": "Malleshwaram", "price_level": "dosa"},
            {"name": "MTR", "address": "Lalbagh", "price_level": "meals"},
            {"name": "Koshy's", "address": "St Marks", "price_level": "classic"},
            {"name": "Toit", "address": "Indiranagar", "price_level": "pub"},
        ],
    },
}


def destination_place_seed(destination: Any) -> dict[str, list[dict[str, Any]]]:
    text = _clean_text(destination).lower()
    for key, value in DESTINATION_PLACE_SEEDS.items():
        if key in text:
            return value
    return {"attractions": [], "restaurants": []}


def _merge_named_items(primary: list[dict[str, Any]], fallback: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return _dedupe_keep_order([*(primary or []), *(fallback or [])], "name")[:limit]


def _fill_days_from_provider(
    days: list[dict[str, Any]],
    destination: str,
    hotel_name: str,
    restaurants: list[dict[str, Any]] | None,
    attractions: list[dict[str, Any]] | None,
    default_costs: dict[str, int] | None = None,
):
    """
    Deterministic guardrail: never invent place names.
    If the LLM output is generic/missing, fill using provider lists.
    """
    restaurants = _dedupe_keep_order(classify_entities(restaurants or [], "restaurant"), "name")
    attractions = _dedupe_keep_order(classify_entities(attractions or []), "name")
    slot_order = ("Morning", "Afternoon", "Night")
    meal_order = ("Breakfast", "Lunch", "Dinner")
    used_activity_titles: set[str] = set()
    used_meal_names: set[str] = set()
    fallback_activity_titles = [
        "Heritage quarter",
        "Art district",
        "City museum",
        "Heritage square",
        "Central market",
        "Riverfront walk",
        "Beach promenade",
        "Sunset promenade",
        "Night bazaar",
        "Cafe street",
        "Botanical garden",
        "Hill overlook",
    ]
    fallback_breakfasts = [
        "Hotel breakfast",
        "Bakery breakfast",
        "Cafe breakfast",
        "Local breakfast",
        "South Indian breakfast",
        "Fruit bowl stop",
        "Tea breakfast",
        "Market breakfast",
    ]
    fallback_lunches = [
        "Seafood lunch",
        "Thali lunch",
        "Market lunch",
        "Cafe lunch",
        "Street food lunch",
        "Coastal lunch",
        "Heritage lunch",
        "Garden lunch",
    ]
    fallback_dinners = [
        "Rooftop dinner",
        "Local dinner",
        "Beachside dinner",
        "Courtyard dinner",
        "Bistro dinner",
        "Grill dinner",
        "Cafe dinner",
        "Sunset dinner",
    ]

    def slot_label(value: Any) -> str | None:
        text = _clean_text(value).lower()
        if text.startswith("morn"):
            return "Morning"
        if text.startswith("after"):
            return "Afternoon"
        if text.startswith("night") or text.startswith("even"):
            return "Night"
        return None

    def meal_label(value: Any) -> str | None:
        text = _clean_text(value).lower()
        if text.startswith("break"):
            return "Breakfast"
        if text.startswith("lunch"):
            return "Lunch"
        if text.startswith("dinner"):
            return "Dinner"
        return None

    def is_placeholder(title: str) -> bool:
        text = title.lower()
        blocked = (
            "priority",
            "deep dive",
            "local culture",
            "market route",
            "scenic dinner",
            "area walk",
            "market stop",
            "dinner walk",
        )
        return _invalid_field(title) or any(item in text for item in blocked)

    def compact_words(value: Any, limit: int) -> str:
        words = _clean_text(value).split()
        return " ".join(words[:limit])

    def cost_label(value: Any, fallback: str) -> str:
        parsed = parse_price(value)
        if parsed:
            return format_inr(parsed)
        text = _clean_text(value)
        return text or fallback

    def title_key(value: Any) -> str:
        return re.sub(r"\s+", " ", _clean_text(value).lower())

    def next_attraction(start_index: int, label: str) -> dict[str, Any] | None:
        if not attractions:
            return None
        for offset in range(len(attractions)):
            pick = attractions[(start_index + offset) % len(attractions)]
            name = title_key(pick.get("name"))
            entity_type = pick.get("entity_type") or classify_entity(pick)
            if name and name not in used_activity_titles and _slot_allows(label, entity_type):
                return pick
        return None

    def next_restaurant(start_index: int, reserved: set[str] | None = None) -> dict[str, Any] | None:
        if not restaurants:
            return None
        reserved = reserved or set()
        for offset in range(len(restaurants)):
            pick = restaurants[(start_index + offset) % len(restaurants)]
            name = title_key(pick.get("name"))
            if name and name not in used_meal_names and name not in reserved:
                return pick
        return None

    def next_fallback_activity(index: int, label: str) -> str:
        for offset in range(len(fallback_activity_titles)):
            title = fallback_activity_titles[(index + offset) % len(fallback_activity_titles)]
            key = title_key(title)
            if key not in used_activity_titles and not _invalid_field(title):
                return title
        suffix = {"Morning": "heritage walk", "Afternoon": "market lane", "Night": "evening walk"}[label]
        return f"{destination.title()} {suffix}"

    def next_breakfast(index: int) -> str:
        for offset in range(len(fallback_breakfasts)):
            title = fallback_breakfasts[(index + offset) % len(fallback_breakfasts)]
            key = title_key(title)
            if key not in used_meal_names and not _invalid_field(title):
                return title
        return f"{destination.title()} breakfast"

    def next_meal_fallback(options: list[str], index: int, label: str) -> str:
        for offset in range(len(options)):
            title = options[(index + offset) % len(options)]
            key = title_key(title)
            if key not in used_meal_names and not _invalid_field(title):
                return title
        return f"{destination.title()} {label.lower()}"

    for i, day in enumerate(days):
        if not isinstance(day, dict):
            continue

        # Ensure exactly 3 time slots: Morning / Afternoon / Night.
        daily_cost = day.get("daily_cost") if isinstance(day.get("daily_cost"), dict) else {}
        default_costs = default_costs or {}
        act_budget = parse_price(daily_cost.get("activities")) or default_costs.get("activities_day", 900)
        food_budget = parse_price(daily_cost.get("food")) or default_costs.get("food_day", 1000)
        transport_budget = parse_price(daily_cost.get("transport")) or default_costs.get("transport_day", 700)
        transport_budget = int(round(transport_budget * (0.86 + (i % 4) * 0.08))) if transport_budget else 0
        default_stay = default_costs.get("hotel_per_night", 0) if i < max(len(days) - 1, 1) else 0
        stay_budget = parse_price(daily_cost.get("stay")) or default_stay
        act_costs = {
            "Morning": int(round(act_budget * (0.42 + (i % 3) * 0.04))) if act_budget else 0,
            "Afternoon": int(round(act_budget * (0.3 + (i % 2) * 0.05))) if act_budget else 0,
            "Night": 0,
        }
        act_costs["Night"] = max(act_budget - act_costs["Morning"] - act_costs["Afternoon"], 0)

        activities = day.get("activities") if isinstance(day.get("activities"), list) else []
        fixed_by_slot: dict[str, dict[str, Any]] = {}
        for act in activities:
            if not isinstance(act, dict):
                continue
            title = _clean_text(act.get("title"))
            label = slot_label(act.get("time"))
            key = title_key(title)
            if not label or label in fixed_by_slot or is_placeholder(title) or key in used_activity_titles:
                continue
            location = _clean_text(act.get("location") or act.get("area") or destination)
            category = classify_entity(act)
            if not _slot_allows(label, category):
                continue
            fixed_by_slot[label] = {
                "time": label,
                "title": compact_words(title, 4),
                "location": location,
                "category": category,
                "cost": cost_label(act.get("cost"), format_inr(act_costs[label])),
                "notes": compact_words(act.get("notes") if not _invalid_field(act.get("notes")) else "Provider matched", 6),
                "image": act.get("image") or place_image_url(title, location, destination, category),
            }
            used_activity_titles.add(key)

        for slot_index, label in enumerate(slot_order):
            if label in fixed_by_slot:
                continue
            pick = next_attraction(i * 3 + slot_index, label)
            if pick and _clean_text(pick.get("name")):
                name = compact_words(pick.get("name"), 4)
                location = _clean_text(pick.get("address") or destination)
                category = pick.get("entity_type") or classify_entity(pick)
                fixed_by_slot[label] = {
                    "time": label,
                    "title": name,
                    "location": location,
                    "category": category,
                    "cost": format_inr(act_costs[label]) if act_costs[label] else "INR estimate",
                    "notes": "Provider place",
                    "image": pick.get("image") or place_image_url(name, location, destination, category),
                }
                used_activity_titles.add(title_key(pick.get("name")))
            else:
                title = next_fallback_activity(i * 3 + slot_index, label)
                category = classify_entity(title)
                if not _slot_allows(label, category):
                    category = {"Morning": "landmark", "Afternoon": "market", "Night": "scenic walk"}[label]
                    title = {"Morning": "Heritage landmark", "Afternoon": "Local market", "Night": "Scenic walk"}[label]
                used_activity_titles.add(title_key(title))
                fixed_by_slot[label] = {
                    "time": label,
                    "title": title,
                    "location": destination if label != "Night" else (hotel_name or destination),
                    "category": category,
                    "cost": format_inr(act_costs[label]) if act_costs[label] else "INR estimate",
                    "notes": "Cluster repair",
                    "image": place_image_url(title, destination, destination, "travel"),
                }

        day["activities"] = [fixed_by_slot[label] for label in slot_order]
        day["image"] = day["activities"][0].get("image") or day.get("image") or place_image_url(
            day["activities"][0].get("title"),
            day["activities"][0].get("location"),
            destination,
            day["activities"][0].get("category"),
        )
        day["image_prompt"] = f"{day['activities'][0].get('title')} {destination} travel"

        # Meals: always Breakfast / Lunch / Dinner.
        meals = day.get("meals") if isinstance(day.get("meals"), list) else []
        meal_costs = {
            "Breakfast": int(round(food_budget * (0.22 + (i % 2) * 0.04))) if food_budget else 0,
            "Lunch": int(round(food_budget * (0.32 + (i % 3) * 0.03))) if food_budget else 0,
            "Dinner": 0,
        }
        meal_costs["Dinner"] = max(food_budget - meal_costs["Breakfast"] - meal_costs["Lunch"], 0)
        meals_by_slot: dict[str, dict[str, Any]] = {}
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            label = meal_label(meal.get("type") or meal.get("meal"))
            name = _clean_text(meal.get("name") or meal.get("place"))
            key = title_key(name)
            if not label or not name or label in meals_by_slot or key in used_meal_names:
                continue
            if _invalid_field(name):
                continue
            meals_by_slot[label] = {
                "type": label,
                "name": compact_words(name, 5),
                "cost": meal.get("cost") or (format_inr(meal_costs[label]) if meal_costs[label] else "INR estimate"),
                "notes": compact_words(meal.get("notes") or meal.get("specialty") or "Local", 4),
            }
            used_meal_names.add(key)

        lunch = next_restaurant(i * 2)
        reserved_lunch = {title_key(lunch.get("name"))} if lunch else set()
        dinner = next_restaurant(i * 2 + 1, reserved_lunch)
        breakfast = next_breakfast(i)
        fallback_names = {
            "Breakfast": breakfast,
            "Lunch": compact_words(lunch.get("name"), 5) if lunch else next_meal_fallback(fallback_lunches, i, "Lunch"),
            "Dinner": compact_words(dinner.get("name"), 5) if dinner else next_meal_fallback(fallback_dinners, i, "Dinner"),
        }
        fallback_notes = {
            "Breakfast": "Hotel",
            "Lunch": compact_words((lunch or {}).get("price_level") or (lunch or {}).get("rating") or "Estimate", 4),
            "Dinner": compact_words((dinner or {}).get("price_level") or (dinner or {}).get("rating") or "Estimate", 4),
        }
        for label in meal_order:
            fallback_key = title_key(fallback_names[label])
            if label not in meals_by_slot:
                meals_by_slot[label] = {
                    "type": label,
                    "name": fallback_names[label],
                    "cost": format_inr(meal_costs[label]) if meal_costs[label] else "INR estimate",
                    "notes": fallback_notes[label],
                }
                used_meal_names.add(fallback_key)

        day["meals"] = [meals_by_slot[label] for label in meal_order]

        # Keep local movement present and compact.
        transport = day.get("transport") if isinstance(day.get("transport"), list) else []
        valid_transport = []
        for item in transport:
            if not isinstance(item, dict):
                continue
            route = item.get("route")
            duration = item.get("duration")
            if _invalid_field(route):
                route = f"Hotel to {day['activities'][0].get('location') or destination}"
            if _invalid_field(duration):
                duration = "45-75m"
            valid_transport.append(
                {
                    **item,
                    "route": route,
                    "duration": duration,
                    "notes": "" if _invalid_field(item.get("notes")) else item.get("notes", ""),
                }
            )
        transport = valid_transport
        if not transport:
            transport = [
                {
                    "mode": "Metro/cab",
                    "route": f"Hotel to {day['activities'][0].get('location') or destination}",
                    "cost": format_inr(transport_budget) if transport_budget else "INR estimate",
                    "duration": "45-75m",
                    "notes": "Cluster route",
                }
            ]
        day["transport"] = transport[:2]

        # Stay name should always be set.
        if isinstance(day.get("stay"), dict):
            day["stay"]["name"] = day["stay"].get("name") or day["stay"].get("hotel") or hotel_name or destination
            day["stay"]["hotel"] = day["stay"].get("hotel") or day["stay"]["name"]
            day["stay"]["cost"] = day["stay"].get("cost") or (format_inr(stay_budget) if stay_budget else "INR 0")
            day["stay"]["notes"] = compact_words(day["stay"].get("notes") or "Base stay", 6)
        else:
            day["stay"] = {"name": hotel_name or destination, "cost": day.get("stay", "INR 0"), "notes": "Base stay."}

        activity_total = sum(parse_price(a.get("cost")) or 0 for a in day["activities"])
        food_total = sum(parse_price(m.get("cost")) or 0 for m in day["meals"])
        transport_total = sum(parse_price(t.get("cost")) or 0 for t in day["transport"])
        stay_total = parse_price(day["stay"].get("cost")) or stay_budget
        daily_cost = daily_cost or {}
        daily_cost.setdefault("activities", format_inr(activity_total) if activity_total else "INR estimate")
        daily_cost.setdefault("transport", format_inr(transport_total) if transport_total else "INR estimate")
        daily_cost.setdefault("food", format_inr(food_total) if food_total else "INR estimate")
        daily_cost.setdefault("stay", format_inr(stay_total) if stay_total else "INR 0")
        total = sum(parse_price(daily_cost.get(key)) or 0 for key in ("activities", "transport", "food", "stay"))
        daily_cost.setdefault("total", format_inr(total) if total else "INR estimate")
        day["daily_cost"] = daily_cost


def normalize_transport_mode(value: Any) -> str:
    text = str(value or "flight").strip().lower()
    if text in {"rail", "railway", "train"}:
        return "train"
    if text in {"coach", "road", "bus"}:
        return "bus"
    return "flight"


def format_inr(amount: float | int | None, fallback: str = "INR estimate pending") -> str:
    if amount is None:
        return fallback
    return f"INR {int(round(amount)):,}"


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _normalize_price_text(value: Any) -> str:
    return str(value or "").replace("\u20b9", "INR ").replace("rs.", "INR ")


def parse_price_range(value: Any) -> tuple[int | None, int | None]:
    if value is None:
        return None, None

    if isinstance(value, (int, float)):
        parsed = _positive_int(value)
        return parsed, parsed

    if isinstance(value, dict):
        for key in (
            "extracted_lowest_price",
            "extracted_price",
            "lowest_price",
            "price",
            "rate_per_night",
        ):
            low, high = parse_price_range(value.get(key))
            if low:
                return low, high or low
        return None, None

    numbers = [
        int(match.replace(",", ""))
        for match in re.findall(r"([0-9][0-9,]{2,})", _normalize_price_text(value))
    ]
    if not numbers:
        return None, None
    return min(numbers), max(numbers)


def parse_price(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, dict):
        for key in (
            "extracted_lowest_price",
            "extracted_price",
            "lowest_price",
            "price",
        ):
            parsed = parse_price(value.get(key))
            if parsed:
                return parsed
        return None

    text = str(value)
    match = re.search(r"(?:INR|Rs\.?)?\s*([0-9][0-9,]{2,})", text, re.I)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def price_midpoint(value: Any) -> int | None:
    low, high = parse_price_range(value)
    if low is None:
        return None
    return int(round(((high or low) + low) / 2))


def estimate_trip_costs(total_days: int, travelers: int, cabin_class: str) -> dict[str, int]:
    cabin = (cabin_class or "economy").lower()
    cabin_factor = 1.18
    hotel_per_night = 4700
    food_per_day = 1150
    activities_per_day = 1000
    transport_per_day = 1050

    if "economy" in cabin and "premium" not in cabin:
        cabin_factor = 1.0
        hotel_per_night = 3600
        food_per_day = 950
        activities_per_day = 850
        transport_per_day = 900
    elif "premium" in cabin or "comfort" in cabin:
        cabin_factor = 1.45
        hotel_per_night = 5600
        food_per_day = 1350
        activities_per_day = 1150
    elif "business" in cabin or "luxury" in cabin:
        cabin_factor = 2.7
        hotel_per_night = 9200
        food_per_day = 1900
        activities_per_day = 1600
        transport_per_day = 1500

    nights = max(total_days - 1, 1)
    flight_low_per_person = int(4200 * cabin_factor)
    flight_high_per_person = int(7800 * cabin_factor)
    return {
        "flight_low_per_person": flight_low_per_person,
        "flight_high_per_person": flight_high_per_person,
        "flight_low": flight_low_per_person * max(travelers, 1),
        "flight_high": flight_high_per_person * max(travelers, 1),
        "train_low_per_person": 550,
        "train_high_per_person": 1900,
        "bus_low_per_person": 650,
        "bus_high_per_person": 2200,
        "hotel_per_night": hotel_per_night,
        "hotel_total": hotel_per_night * nights,
        "food_day": food_per_day * travelers,
        "activities_day": activities_per_day * travelers,
        "transport_day": transport_per_day,
    }


def build_budget_profile(
    total_days: int,
    travelers: int,
    cabin_class: str,
    max_budget: int | None = None,
    transport_mode: str = "flight",
) -> dict[str, Any]:
    costs = estimate_trip_costs(total_days, travelers, cabin_class)
    nights = max(total_days - 1, 1)
    travelers = max(travelers, 1)
    selected_mode = normalize_transport_mode(transport_mode)
    selected_per_person = costs.get(f"{selected_mode}_low_per_person", costs["flight_low_per_person"])
    selected_total = selected_per_person * travelers
    medium_daily = (
        costs["food_day"]
        + costs["activities_day"]
        + costs["transport_day"]
        + costs["hotel_per_night"]
    )

    profile = {
        "style": DEFAULT_TRAVEL_STYLE,
        "max_budget": max_budget,
        "transport_mode": selected_mode,
        "target_transport_per_person": selected_per_person,
        "target_transport_total": selected_total,
        "target_flight_per_person": costs["flight_low_per_person"],
        "target_flight_total": costs["flight_low"],
        "target_train_per_person": costs["train_low_per_person"],
        "target_bus_per_person": costs["bus_low_per_person"],
        "target_hotel_per_night": costs["hotel_per_night"],
        "target_hotel_total": costs["hotel_per_night"] * nights,
        "target_daily_total": medium_daily,
        "target_trip_total": selected_total + medium_daily * total_days,
    }

    if max_budget:
        flight_share = 0.22 if total_days <= 4 else 0.2
        if selected_mode in {"train", "bus"}:
            flight_share = 0.1 if total_days <= 4 else 0.08
        hotel_share = 0.34 if total_days <= 4 else 0.36
        daily_share = max(0.18, 1 - flight_share - hotel_share)
        target_transport_total = max(int(max_budget * flight_share), travelers * 450)
        profile.update(
            {
                "target_transport_total": target_transport_total,
                "target_transport_per_person": max(int(target_transport_total / travelers), 450),
                "target_flight_total": max(int(max_budget * (0.22 if total_days <= 4 else 0.2)), travelers * 1800),
                "target_flight_per_person": max(
                    int(max_budget * (0.22 if total_days <= 4 else 0.2) / travelers),
                    1800,
                ),
                "target_hotel_total": max(int(max_budget * hotel_share), nights * 1800),
                "target_hotel_per_night": max(int((max_budget * hotel_share) / nights), 1800),
                "target_daily_total": max(int((max_budget * daily_share) / max(total_days, 1)), travelers * 900),
                "target_trip_total": max_budget,
            }
        )

    return profile


def _select_price_aligned_items(
    items: list[dict[str, Any]],
    price_getter,
    target_price: int | None = None,
    max_price: int | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    priced: list[tuple[dict[str, Any], int | None]] = [
        (item, price_midpoint(price_getter(item))) for item in items if isinstance(item, dict)
    ]

    if not priced:
        return []

    numeric_prices = sorted(price for _, price in priced if price)
    medium_price = numeric_prices[len(numeric_prices) // 2] if numeric_prices else None
    anchor = target_price or medium_price

    def rank(row: tuple[dict[str, Any], int | None]) -> tuple[int, int, int]:
        _, price = row
        if not price:
            return (2, 10**9, 10**9)

        over_cap = 1 if max_price and price > max_price else 0
        distance = abs(price - anchor) if anchor else price
        return (over_cap, distance, price)

    return [item for item, _ in sorted(priced, key=rank)[:limit]]


def _select_cheapest_items(
    items: list[dict[str, Any]],
    price_getter,
    max_price: int | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    priced: list[tuple[dict[str, Any], int | None]] = [
        (item, price_midpoint(price_getter(item))) for item in items if isinstance(item, dict)
    ]

    if not priced:
        return []

    def rank(row: tuple[dict[str, Any], int | None]) -> tuple[int, int]:
        _, price = row
        if not price:
            return (2, 10**9)
        return (1 if max_price and price > max_price else 0, price)

    return [item for item, _ in sorted(priced, key=rank)[:limit]]


def _target_price_label(target_price: int | None, fallback: str) -> str:
    if not target_price:
        return fallback
    low = max(int(target_price * 0.92), 1)
    high = int(target_price * 1.08)
    return f"{format_inr(low)} - {format_inr(high)} target range"


def _multiply_price_label(value: Any, multiplier: int, fallback: str = "Total estimate pending") -> str:
    low, high = parse_price_range(value)
    if low is None:
        return fallback
    multiplier = max(multiplier, 1)
    if high and high != low:
        return f"{format_inr(low * multiplier)} - {format_inr(high * multiplier)}"
    return format_inr(low * multiplier)


def _option_price_per_person(option: dict[str, Any]) -> int | None:
    return price_midpoint(
        option.get("price_per_person")
        or option.get("per_person_price")
        or option.get("price")
        or option.get("fare")
    )


def _option_total_price(option: dict[str, Any], travelers: int) -> int | None:
    total = price_midpoint(option.get("total_price") or option.get("total_estimate"))
    if total:
        return total
    per_person = _option_price_per_person(option)
    return per_person * max(travelers, 1) if per_person else None


def _has_usable_price_option(items: Any, *price_fields: str) -> bool:
    if isinstance(items, dict):
        raw_items = items.get("flights") or items.get("hotels") or items.get("options")
    else:
        raw_items = items
    if not isinstance(raw_items, list):
        return False

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        for field in price_fields:
            text = str(item.get(field) or "").lower()
            if parse_price_range(item.get(field))[0] and not any(
                marker in text for marker in ("pending", "unavailable", "tba")
            ):
                return True

    return False


def _budget_match_note(
    actual_price: int | None,
    target_price: int | None,
    max_price: int | None,
    label: str,
    default_note: str,
) -> str:
    if not target_price and not max_price:
        return default_note

    cap = max_price or target_price
    if actual_price and cap and actual_price <= cap:
        return f"Within {format_inr(cap)}."

    if actual_price and cap:
        return f"Nearest {format_inr(actual_price)}."

    return f"Target {format_inr(cap or target_price)}."


def normalize_flight_options(
    flights: Any,
    origin: str,
    destination: str,
    origin_airport: str,
    destination_airport: str,
    travelers: int,
    cabin_class: str,
    target_total: int | None = None,
    max_total: int | None = None,
    target_per_person: int | None = None,
    max_per_person: int | None = None,
) -> list[dict[str, Any]]:
    raw_options = flights.get("flights", []) if isinstance(flights, dict) else flights
    options = []
    travelers = max(travelers, 1)
    target_per_person = target_per_person or (int(target_total / travelers) if target_total else None)
    max_per_person = max_per_person or (int(max_total / travelers) if max_total else None)

    if isinstance(raw_options, list):
        selected_options = _select_cheapest_items(
            raw_options,
            lambda item: item.get("price_per_person") or item.get("price"),
            max_price=max_per_person,
            limit=2,
        ) or raw_options[:2]

        for item in selected_options:
            if not isinstance(item, dict):
                continue

            duration = item.get("duration")
            if not duration and item.get("duration_min"):
                minutes = item.get("duration_min")
                duration = f"{int(minutes) // 60}h {int(minutes) % 60}m"

            price = parse_price(item.get("price_per_person") or item.get("price"))
            raw_price = item.get("price_per_person") or item.get("price")
            price_label = (
                str(raw_price)
                if isinstance(raw_price, str) and ("-" in raw_price or "estimate" in raw_price.lower())
                else format_inr(
                    price,
                    _target_price_label(
                        target_per_person,
                        "INR 4,200 - INR 7,800 approximate fare range per person",
                    ),
                )
            )
            total_label = item.get("total_price") or _multiply_price_label(
                price_label,
                travelers,
                "Total fare estimate pending",
            )
            options.append(
                {
            "airline": item.get("airline") or "Live fare option",
                    "flight_number": item.get("flight_number") or "",
                    "route": f"{item.get('from') or origin_airport or origin} to {item.get('to') or destination_airport or destination}",
                    "departure": item.get("departure") or "Check current schedule",
                    "arrival": item.get("arrival") or "Check current schedule",
                    "duration": duration or "Check schedule",
                    "price": price_label,
                    "price_per_person": price_label,
                    "total_price": total_label,
                    "passengers": travelers,
                    "pricing_unit": "per_person",
                    "booking_note": _budget_match_note(
                        price,
                        target_per_person,
                        max_per_person,
                        "flight fare per person",
                        item.get("booking_note")
                        or "Live fare; recheck.",
                    ),
                    "source": item.get("source") or "SerpAPI Google Flights",
                }
            )

    if options:
        return options[:2]

    estimates = estimate_trip_costs(1, travelers, cabin_class)
    low = estimates["flight_low_per_person"]
    high = estimates["flight_high_per_person"]
    first_price = _target_price_label(
        target_per_person,
        f"{format_inr(low)} - {format_inr(high)} per person",
    )
    second_price = _target_price_label(
        int(target_per_person * 1.08) if target_per_person else None,
        f"{format_inr(int(low * 1.15))} - {format_inr(int(high * 1.25))} per person",
    )
    return [
        {
            "airline": "Best fare watch",
            "flight_number": "",
            "route": f"{origin_airport or origin} to {destination_airport or destination}",
            "departure": "Morning or evening",
            "arrival": "Same day",
            "duration": "Varies by route",
            "price": first_price,
            "price_per_person": first_price,
            "total_price": _multiply_price_label(first_price, travelers),
            "passengers": travelers,
            "pricing_unit": "per_person",
            "booking_note": "Estimate; recheck.",
            "source": "Fallback estimate",
        },
        {
            "airline": "Flexible timing option",
            "flight_number": "",
            "route": f"{origin_airport or origin} to {destination_airport or destination}",
            "departure": "Flexible",
            "arrival": "Flexible",
            "duration": "Varies by route",
            "price": second_price,
            "price_per_person": second_price,
            "total_price": _multiply_price_label(second_price, travelers),
            "passengers": travelers,
            "pricing_unit": "per_person",
            "booking_note": "Fallback range.",
            "source": "Fallback estimate",
        },
    ]


def normalize_ground_transport_options(
    transport_result: Any,
    mode: str,
    origin: str,
    destination: str,
    travelers: int,
    target_per_person: int | None = None,
    max_per_person: int | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    mode = normalize_transport_mode(mode)
    if mode == "flight":
        return []

    raw_options = []
    if isinstance(transport_result, dict):
        mode_payload = transport_result.get(mode)
        if isinstance(mode_payload, dict):
            raw_options = mode_payload.get("options") or []
        elif isinstance(mode_payload, list):
            raw_options = mode_payload
        else:
            raw_options = transport_result.get("options") or []
    elif isinstance(transport_result, list):
        raw_options = transport_result

    travelers = max(travelers, 1)
    options = []
    if isinstance(raw_options, list):
        selected_options = _select_cheapest_items(
            raw_options,
            lambda item: item.get("price_per_person") or item.get("price"),
            max_price=max_per_person,
            limit=limit,
        ) or raw_options[:limit]

        for item in selected_options:
            if not isinstance(item, dict):
                continue
            price_label = str(
                item.get("price_per_person")
                or item.get("price")
                or _target_price_label(target_per_person, "INR estimate pending")
            )
            per_person = parse_price(price_label)
            options.append(
                {
                    "mode": mode,
                    "operator": item.get("operator") or ("Indian Railways" if mode == "train" else "Bus operator"),
                    "service_name": item.get("service_name") or item.get("name") or f"{mode.title()} option",
                    "route": item.get("route") or f"{origin} to {destination}",
                    "departure": item.get("departure") or "Check live timetable",
                    "arrival": item.get("arrival") or "Check live timetable",
                    "duration": item.get("duration") or "Timing varies by route",
                    "price": price_label,
                    "price_per_person": price_label,
                    "total_price": item.get("total_price") or _multiply_price_label(price_label, travelers),
                    "passengers": travelers,
                    "pricing_unit": "per_person",
                    "booking_note": _budget_match_note(
                        per_person,
                        target_per_person,
                        max_per_person,
                        f"{mode} fare per person",
                        item.get("booking_note") or "Verify operator.",
                    ),
                    "source": item.get("source") or f"{mode.title()} search estimate",
                    "estimate_confidence": item.get("estimate_confidence") or "Low",
                }
            )

    if options:
        return options[:limit]

    estimates = estimate_trip_costs(1, travelers, "economy")
    low = estimates[f"{mode}_low_per_person"]
    high = estimates[f"{mode}_high_per_person"]
    label = _target_price_label(target_per_person, f"{format_inr(low)} - {format_inr(high)} per person")
    return [
        {
            "mode": mode,
            "operator": f"Cheapest {mode} watch",
            "service_name": f"{mode.title()} estimate",
            "route": f"{origin} to {destination}",
            "departure": "Flexible",
            "arrival": "Check live timetable",
            "duration": "6-18h by route" if mode == "train" else "5-16h by route",
            "price": label,
            "price_per_person": label,
            "total_price": _multiply_price_label(label, travelers),
            "passengers": travelers,
            "pricing_unit": "per_person",
            "booking_note": f"Offline {mode} estimate.",
            "source": "Fallback estimate",
            "estimate_confidence": "Low",
        }
    ]


def normalize_hotel_options(
    hotels: Any,
    destination: str,
    total_days: int,
    travelers: int,
    cabin_class: str,
    target_nightly: int | None = None,
    max_nightly: int | None = None,
) -> list[dict[str, Any]]:
    raw_hotels = hotels.get("hotels", []) if isinstance(hotels, dict) else hotels
    nights = max(total_days - 1, 1)
    options = []

    if isinstance(raw_hotels, list):
        selected_hotels = _select_price_aligned_items(
            raw_hotels,
            lambda item: item.get("price") or item.get("price_per_night"),
            target_price=target_nightly,
            max_price=max_nightly,
            limit=2,
        ) or raw_hotels[:2]

        for item in selected_hotels:
            if not isinstance(item, dict):
                continue

            nightly = parse_price(item.get("price") or item.get("price_per_night"))
            raw_nightly = item.get("price") or item.get("price_per_night")
            nightly_label = (
                str(raw_nightly)
                if isinstance(raw_nightly, str) and ("-" in raw_nightly or "estimate" in raw_nightly.lower())
                else format_inr(nightly, str(item.get("price") or "Live rate unavailable"))
            )
            nightly_low, nightly_high = parse_price_range(raw_nightly)
            total = nightly * nights if nightly else None
            total_label = (
                f"{format_inr(nightly_low * nights)} - {format_inr((nightly_high or nightly_low) * nights)}"
                if nightly_low and nightly_high and nightly_high != nightly_low
                else format_inr(total, "Total depends on room availability")
            )
            options.append(
                {
                    "name": item.get("name") or f"{destination.title()} hotel option",
                    "area": item.get("area") or item.get("address") or "Well-connected area",
                    "rating": item.get("rating") or "Rating unavailable",
                    "reviews": item.get("reviews") or "",
                    "price_per_night": nightly_label,
                    "total_estimate": total_label,
                    "image": item.get("image")
                    or place_image_url(
                        item.get("name") or f"{destination.title()} hotel",
                        item.get("area") or item.get("address") or destination,
                        destination,
                        "hotel",
                        900,
                        600,
                    ),
                    "why": _budget_match_note(
                        nightly,
                        target_nightly,
                        max_nightly,
                        "hotel rate",
                        item.get("why")
                        or "Good route access.",
                    ),
                    "source": item.get("source") or "SerpAPI Google Hotels",
                }
            )

    if options:
        return options[:2]

    estimates = estimate_trip_costs(total_days, travelers, cabin_class)
    nightly = estimates["hotel_per_night"]
    return [
        {
            "name": f"Central {destination.title()} stay",
            "area": "Central or well-connected neighborhood",
            "rating": "Estimated 3.5+",
            "reviews": "",
            "price_per_night": _target_price_label(
                target_nightly,
                f"{format_inr(nightly)} - {format_inr(int(nightly * 1.35))}",
            ),
            "total_estimate": _target_price_label(
                target_nightly * nights if target_nightly else None,
                f"{format_inr(nightly * nights)} - {format_inr(int(nightly * 1.35) * nights)}",
            ),
            "image": place_image_url(f"Central {destination.title()} hotel", destination, destination, "hotel", 900, 600),
            "why": "Short transfers.",
            "source": "Fallback estimate",
        },
        {
            "name": f"Comfort {destination.title()} hotel",
            "area": "Quieter base near main transport",
            "rating": "Estimated 4.0+",
            "reviews": "",
            "price_per_night": _target_price_label(
                int(target_nightly * 1.08) if target_nightly else None,
                f"{format_inr(int(nightly * 1.25))} - {format_inr(int(nightly * 1.7))}",
            ),
            "total_estimate": _target_price_label(
                int(target_nightly * 1.08) * nights if target_nightly else None,
                f"{format_inr(int(nightly * 1.25) * nights)} - {format_inr(int(nightly * 1.7) * nights)}",
            ),
            "image": place_image_url(f"Comfort {destination.title()} hotel", destination, destination, "hotel", 900, 600),
            "why": "Comfort upgrade.",
            "source": "Fallback estimate",
        },
    ]


def build_day_plans(
    destination: str,
    start_date: str,
    total_days: int,
    travelers: int,
    cabin_class: str,
    restaurants: list[dict[str, Any]] | None,
    attractions: list[dict[str, Any]] | None,
    hotel_name: str,
    selected_transport_mode: str = "flight",
) -> list[dict[str, Any]]:
    costs = estimate_trip_costs(total_days, travelers, cabin_class)
    restaurants = restaurants or []
    attractions = attractions or []
    days = []

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        start = None

    themes = [
        ("Arrival + reset", "Light route, early night."),
        ("Icons + local food", "Morning sights, cooler evening."),
        ("Neighborhoods + cafes", "Slow pacing, short transfers."),
        ("Views + evening walk", "Heat-smart, golden hour focus."),
        ("Wrap-up + buffer", "Flexible, departure-ready."),
    ]
    extra_themes = [
        "Beach + cafes",
        "Fort + sunset",
        "Old quarter",
        "Nature loop",
        "Market + music",
        "Island pause",
        "Food trail",
        "Photo walk",
    ]

    for index in range(total_days):
        title, summary = themes[index] if index < len(themes) else (
            extra_themes[(index - len(themes)) % len(extra_themes)],
            "Paced sights, food, buffers.",
        )
        date = (start + timedelta(days=index)).strftime("%Y-%m-%d") if start else ""
        lunch = restaurants[index % len(restaurants)] if restaurants else None
        dinner = restaurants[(index + 1) % len(restaurants)] if len(restaurants) > 1 else lunch
        morning_spot = attractions[(index * 3) % len(attractions)] if attractions else None
        afternoon_spot = attractions[(index * 3 + 1) % len(attractions)] if len(attractions) > 1 else None
        evening_spot = attractions[(index * 3 + 2) % len(attractions)] if len(attractions) > 2 else afternoon_spot or morning_spot
        activities_cost = costs["activities_day"]
        transport_cost = costs["transport_day"]
        food_cost = costs["food_day"]
        stay_cost = costs["hotel_per_night"] if index < max(total_days - 1, 1) else 0
        total = activities_cost + transport_cost + food_cost + stay_cost

        local_transport = [
            {
                "mode": "Cab/metro/walk",
                "route": f"Hotel base to {destination.title()} daily route",
                "cost": format_inr(transport_cost),
                "duration": "30-90m",
                "notes": "Traffic buffer.",
            }
        ]
        if index == 0:
            selected_label = normalize_transport_mode(selected_transport_mode).title()
            local_transport.insert(
                0,
                {
                    "mode": selected_label,
                    "route": f"Arrival by selected {selected_label.lower()} option",
                    "cost": "Included in selected intercity transport total",
                    "duration": "See option",
                    "notes": "Counted in totals.",
                },
            )

        days.append(
            {
                "day": index + 1,
                "date": date,
                "title": title,
                "summary": summary,
                "image_prompt": f"{destination} travel landmark food street hotel",
                "activities": [
                    *(
                        [
                            {
                                "time": "morning",
                                "title": morning_spot.get("name"),
                                "location": (morning_spot.get("address") or destination.title()),
                                "duration": "2h",
                                "cost": int(activities_cost * 0.45),
                                "type": "landmark",
                            }
                        ]
                        if morning_spot
                        else []
                    ),
                    *(
                        [
                            {
                                "time": "afternoon",
                                "title": afternoon_spot.get("name"),
                                "location": (afternoon_spot.get("address") or destination.title()),
                                "duration": "2h",
                                "cost": int(activities_cost * 0.35),
                                "type": "market",
                            }
                        ]
                        if afternoon_spot
                        else []
                    ),
                    {
                        "time": "Night",
                        "title": (evening_spot.get("name") if isinstance(evening_spot, dict) else "") or "Sunset promenade",
                        "location": ((evening_spot.get("address") if isinstance(evening_spot, dict) else None) or destination.title()),
                        "duration": "1h 30m",
                        "cost": int(activities_cost * 0.20),
                        "type": "nightlife",
                    },
                ][:3],
                "transport": local_transport,
                "meals": [
                    {
                        "type": "Breakfast",
                        "name": "Hotel breakfast",
                        "cost": format_inr(int(food_cost * 0.25)),
                        "notes": "Hotel",
                    },
                    *(
                        [
                            {
                                "type": "Lunch",
                                "name": lunch.get("name"),
                                "cost": format_inr(int(food_cost * 0.35)),
                                "notes": str(lunch.get("price_level") or lunch.get("rating") or "Local"),
                            }
                        ]
                        if lunch and lunch.get("name")
                        else [
                            {
                                "type": "Lunch",
                                "name": "Local lunch",
                                "cost": format_inr(int(food_cost * 0.35)),
                                "notes": "Estimate",
                            }
                        ]
                    ),
                    *(
                        [
                            {
                                "type": "Dinner",
                                "name": dinner.get("name"),
                                "cost": format_inr(int(food_cost * 0.4)),
                                "notes": str(dinner.get("price_level") or dinner.get("rating") or "Local"),
                            }
                        ]
                        if dinner and dinner.get("name")
                        else [
                            {
                                "type": "Dinner",
                                "name": "Local dinner",
                                "cost": format_inr(int(food_cost * 0.4)),
                                "notes": "Estimate",
                            }
                        ]
                    ),
                ],
                "stay": {
                    "name": hotel_name,
                    "cost": format_inr(stay_cost) if stay_cost else "Included before departure / no overnight stay",
                    "notes": "Base stay.",
                },
                "daily_cost": {
                    "activities": format_inr(activities_cost),
                    "transport": format_inr(transport_cost),
                    "food": format_inr(food_cost),
                    "stay": format_inr(stay_cost) if stay_cost else "INR 0",
                    "total": format_inr(total),
                },
            }
        )

    return days


def extract_budget_constraints(
    user_request: str = "",
    current_total: int | None = None,
) -> dict[str, Any]:
    text = (user_request or "").lower().replace("\u20b9", "inr")
    constraints: dict[str, Any] = {
        "has_budget_request": False,
        "make_cheaper": bool(
            re.search(
                r"\b(cheap|cheaper|less|lower|reduce|under|below|cap)\b",
                text,
            )
        ),
        "make_premium": bool(re.search(r"\b(premium|luxury|luxurious|upgrade|better|business)\b", text)),
        "hold_near_budget": bool(
            re.search(r"\b(near|close to|around|within|keep|stay near|match)\b.{0,24}\bbudget\b", text)
            or re.search(r"\bbudget\b.{0,24}\b(near|close|around|matched|aligned)\b", text)
        ),
        "target_total": None,
        "target_flight": None,
        "target_transport": None,
        "target_hotel_nightly": None,
        "target_daily": None,
    }

    if not text:
        return constraints

    amount_matches = [
        (match.start(), int(match.group(1).replace(",", "")))
        for match in re.finditer(
            r"(?:inr|rs\.?|\u20b9)?\s*([0-9][0-9,]{2,})(?:\s*(?:inr|rs\.?))?",
            text,
        )
    ]

    keyword_patterns = {
        "flight": r"\b(flight|airfare|airline|plane)\b",
        "transport": r"\b(train|rail|bus|coach|transport|ticket|fare)\b",
        "hotel": r"\b(hotel|stay|room|night|nightly|rate)\b",
        "daily": r"\b(day|daily|food|meal|activity|transport|local)\b",
        "total": r"\b(total|trip|overall|complete|whole)\b",
    }

    def nearest_budget_label(position: int) -> tuple[str | None, str]:
        start = max(0, position - 56)
        end = min(len(text), position + 56)
        window = text[start:end]
        nearest_label = None
        nearest_distance = 10**9

        for label, pattern in keyword_patterns.items():
            for keyword_match in re.finditer(pattern, window):
                keyword_position = start + keyword_match.start()
                distance = abs(position - keyword_position)
                if distance < nearest_distance:
                    nearest_label = label
                    nearest_distance = distance

        return nearest_label, window

    for position, amount in amount_matches:
        label, window = nearest_budget_label(position)
        if label == "flight":
            constraints["target_flight"] = amount
        elif label == "transport":
            constraints["target_transport"] = amount
        elif label == "hotel":
            if re.search(r"\b(total|trip|overall|complete)\b", window):
                constraints["target_total"] = amount
            else:
                constraints["target_hotel_nightly"] = amount
        elif label == "daily":
            constraints["target_daily"] = amount
        else:
            constraints["target_total"] = amount

    if constraints["make_cheaper"] and not any(
        constraints.get(key)
        for key in ("target_total", "target_flight", "target_transport", "target_hotel_nightly", "target_daily")
    ):
        if current_total:
            constraints["target_total"] = int(current_total * BUDGET_REDUCTION_FACTOR)
        constraints["has_budget_request"] = True

    if constraints["hold_near_budget"] and not constraints.get("target_total") and current_total:
        constraints["target_total"] = current_total
        constraints["has_budget_request"] = True

    if constraints["make_premium"] and current_total and not constraints["target_total"]:
        constraints["target_total"] = int(current_total * LUXURY_INCREASE_FACTOR)

    if any(
        constraints.get(key)
        for key in ("target_total", "target_flight", "target_transport", "target_hotel_nightly", "target_daily")
    ):
        constraints["has_budget_request"] = True

    return constraints


def _set_price_target(option: dict[str, Any], field: str, target: int, label: str):
    current = price_midpoint(option.get(field))
    option[field] = _target_price_label(target, option.get(field) or format_inr(target))
    note_key = "booking_note" if label == "flight fare" else "why"
    option[note_key] = _budget_match_note(
        current,
        target,
        target,
        label,
        option.get(note_key, ""),
    )
    option["budget_target"] = format_inr(target)
    if current and current > target:
        option["budget_status"] = "nearest_above_requested_price"
    else:
        option["budget_status"] = "within_requested_price"


def _set_transport_price_target(option: dict[str, Any], target_per_person: int, travelers: int, label: str):
    current = _option_price_per_person(option)
    price_label = _target_price_label(target_per_person, option.get("price_per_person") or format_inr(target_per_person))
    option["price"] = price_label
    option["price_per_person"] = price_label
    option["total_price"] = _multiply_price_label(price_label, travelers)
    option["budget_target"] = format_inr(target_per_person)
    option["booking_note"] = _budget_match_note(
        current,
        target_per_person,
        target_per_person,
        label,
        option.get("booking_note", ""),
    )
    if current and current > target_per_person:
        option["budget_status"] = "nearest_above_requested_price"
    else:
        option["budget_status"] = "within_requested_price"


def _set_daily_cost(day: dict[str, Any], target_total: int, include_stay: bool = True):
    if target_total <= 0:
        return

    shares = {
        "activities": 0.24,
        "transport": 0.18,
        "food": 0.28,
        "stay": 0.30 if include_stay else 0,
    }
    active_total = sum(shares.values()) or 1
    amounts = {key: int(target_total * (share / active_total)) for key, share in shares.items()}
    amounts["total"] = sum(amounts.values())

    day["daily_cost"] = {
        "activities": format_inr(amounts["activities"]),
        "transport": format_inr(amounts["transport"]),
        "food": format_inr(amounts["food"]),
        "stay": format_inr(amounts["stay"]),
        "total": format_inr(amounts["total"]),
    }

    if day.get("stay") and isinstance(day["stay"], dict):
        day["stay"]["cost"] = format_inr(amounts["stay"])
        day["stay"]["notes"] = "Budget matched."

    day["budget_note"] = "Daily budget matched."


def _sum_day_totals(days: list[dict[str, Any]]) -> int:
    return sum(parse_price(day.get("daily_cost", {}).get("total")) or 0 for day in days)


def recalculate_cost_summary(plan: dict[str, Any], note: str | None = None) -> dict[str, Any]:
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    flights = plan.get("flights") if isinstance(plan.get("flights"), list) else []
    hotels = plan.get("hotels") if isinstance(plan.get("hotels"), list) else []
    trains = plan.get("trains") if isinstance(plan.get("trains"), list) else []
    buses = plan.get("buses") if isinstance(plan.get("buses"), list) else []
    travelers = int(plan.get("travelers") or 1)
    selected_mode = normalize_transport_mode(plan.get("selected_transport_mode"))
    selected_options = {"flight": flights, "train": trains, "bus": buses}.get(selected_mode, flights)

    flight_total = _option_total_price(flights[0], travelers) if flights else None
    selected_transport_total = _option_total_price(selected_options[0], travelers) if selected_options else None
    hotel_total = price_midpoint(hotels[0].get("total_estimate")) if hotels else None
    daily_total = _sum_day_totals(days)
    grand_total = (selected_transport_total or 0) + daily_total

    summary = {
        "transport_mode": selected_mode,
        "selected_transport": format_inr(selected_transport_total) if selected_transport_total else "Transport estimate pending",
        "flights": format_inr(flight_total) if flight_total else "Flight estimate pending",
        "flight_per_person": flights[0].get("price_per_person") if flights else "Flight estimate pending",
        "hotels": format_inr(hotel_total) if hotel_total else "Hotel estimate pending",
        "daily_spend": format_inr(daily_total) if daily_total else "Daily estimate pending",
        "grand_total": format_inr(grand_total) if grand_total else "Estimate pending",
        "notes": note
        or "Verify live prices.",
    }
    plan["cost_summary"] = summary
    return summary


def apply_budget_preferences(
    plan: dict[str, Any],
    max_budget: int | None = None,
    user_request: str = "",
    source: str = "planner",
) -> dict[str, Any]:
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    flights = plan.get("flights") if isinstance(plan.get("flights"), list) else []
    hotels = plan.get("hotels") if isinstance(plan.get("hotels"), list) else []
    trains = plan.get("trains") if isinstance(plan.get("trains"), list) else []
    buses = plan.get("buses") if isinstance(plan.get("buses"), list) else []
    travelers = int(plan.get("travelers") or 1)
    selected_mode = normalize_transport_mode(plan.get("selected_transport_mode"))
    selected_options = {"flight": flights, "train": trains, "bus": buses}.get(selected_mode, flights)

    current_total = (
        parse_price(plan.get("cost_summary", {}).get("grand_total"))
        if isinstance(plan.get("cost_summary"), dict)
        else None
    ) or ((_option_total_price(selected_options[0], travelers) if selected_options else 0) + _sum_day_totals(days))
    guardrail_total = (
        parse_price(plan.get("budget_guardrails", {}).get("target_total"))
        if isinstance(plan.get("budget_guardrails"), dict)
        else None
    )
    near_budget_request = bool(
        re.search(r"\b(near|close to|around|within|keep|stay near|match)\b.{0,24}\bbudget\b", user_request or "", re.I)
        or re.search(r"\bbudget\b.{0,24}\b(near|close|around|matched|aligned)\b", user_request or "", re.I)
    )

    constraints = extract_budget_constraints(
        user_request,
        current_total=(guardrail_total or current_total) if near_budget_request else (current_total or None),
    )
    if max_budget:
        constraints["target_total"] = max_budget
        constraints["has_budget_request"] = True

    if not constraints["has_budget_request"]:
        plan["budget_guardrails"] = {
            "style": DEFAULT_TRAVEL_STYLE,
            "status": "balanced",
            "note": "Cheapest practical first.",
        }
        return plan

    target_total = constraints.get("target_total")
    target_flight = constraints.get("target_flight")
    target_transport = constraints.get("target_transport")
    target_hotel = constraints.get("target_hotel_nightly")
    target_daily = constraints.get("target_daily")
    explicit_transport_target = bool(target_transport)

    if target_total:
        existing_transport = _option_total_price(selected_options[0], travelers) if selected_options else None
        if not target_transport:
            share = 0.22 if selected_mode == "flight" else 0.1
            target_transport = min(existing_transport or int(target_total * share), int(target_total * (share + 0.02)))
        else:
            target_transport = target_transport * max(travelers, 1)
        if selected_mode == "flight" and not target_flight:
            target_flight = max(int(target_transport / max(travelers, 1)), 1)
        remaining = max(target_total - (target_transport or 0), 0)
        if days and not target_daily:
            target_daily = max(int(remaining / len(days)), 900)
        if target_daily and hotels and not target_hotel:
            target_hotel = max(int(target_daily * 0.3), 1200)

    if target_flight and flights:
        for index, flight in enumerate(flights[:2]):
            adjusted_target = int(target_flight * (1 + index * 0.08))
            current_price = _option_price_per_person(flight)
            if current_price and current_price <= adjusted_target:
                flight["budget_target"] = format_inr(adjusted_target)
                flight["budget_status"] = "cheapest_within_requested_price"
                flight["total_price"] = _multiply_price_label(
                    flight.get("price_per_person") or flight.get("price"),
                    travelers,
                )
                flight["booking_note"] = _budget_match_note(
                    current_price,
                    adjusted_target,
                    adjusted_target,
                    "flight fare per person",
                    flight.get("booking_note", ""),
                )
            else:
                _set_transport_price_target(flight, adjusted_target, travelers, "flight fare per person")

    if target_transport and selected_options and selected_mode != "flight":
        target_per_person = (
            target_transport
            if explicit_transport_target and not target_total
            else max(int(target_transport / max(travelers, 1)), 1)
        )
        for index, option in enumerate(selected_options[:2]):
            adjusted_target = int(target_per_person * (1 + index * 0.08))
            _set_transport_price_target(
                option,
                adjusted_target,
                travelers,
                f"{selected_mode} fare per person",
            )

    if target_hotel and hotels:
        nights = max(len(days) - 1, 1)
        for index, hotel in enumerate(hotels[:2]):
            nightly_target = int(target_hotel * (1 + index * 0.08))
            _set_price_target(hotel, "price_per_night", nightly_target, "hotel rate")
            hotel["total_estimate"] = _target_price_label(
                nightly_target * nights,
                hotel.get("total_estimate") or format_inr(nightly_target * nights),
            )

        for index, day in enumerate(days):
            if index < max(len(days) - 1, 1) and day.get("stay"):
                day["stay"]["cost"] = _target_price_label(target_hotel, format_inr(target_hotel))
                daily_cost = day.get("daily_cost") if isinstance(day.get("daily_cost"), dict) else {}
                old_stay = parse_price(daily_cost.get("stay")) or 0
                old_total = parse_price(daily_cost.get("total")) or 0
                new_total = max(old_total - old_stay + target_hotel, target_hotel)
                daily_cost["stay"] = format_inr(target_hotel)
                daily_cost["total"] = format_inr(new_total)
                day["daily_cost"] = daily_cost

    if target_daily and days:
        for index, day in enumerate(days):
            include_stay = index < max(len(days) - 1, 1)
            _set_daily_cost(day, int(target_daily), include_stay=include_stay)

    summary_note = (
        "Refined near budget."
        if source == "refine"
        else "Budget guardrail applied."
    )
    recalculate_cost_summary(plan, summary_note)

    plan["budget_guardrails"] = {
        "style": DEFAULT_TRAVEL_STYLE,
        "status": "applied",
        "request": user_request or ("initial max budget" if max_budget else ""),
        "target_total": format_inr(target_total) if target_total else "",
        "target_transport": format_inr(target_transport) if target_transport else "",
        "target_transport_per_person": (
            format_inr(target_transport if explicit_transport_target and not target_total else int(target_transport / max(travelers, 1)))
            if target_transport
            else ""
        ),
        "target_flight": format_inr(target_flight) if target_flight else "",
        "target_hotel_per_night": format_inr(target_hotel) if target_hotel else "",
        "target_daily": format_inr(target_daily) if target_daily else "",
        "note": "Fares per person.",
    }

    tips = plan.get("booking_tips") if isinstance(plan.get("booking_tips"), list) else []
    budget_tip = "Use budget as ceiling."
    if budget_tip not in tips:
        plan["booking_tips"] = [budget_tip, *tips][:5]

    return plan


def complete_trip_plan(plan: dict[str, Any], state: dict[str, Any], source_payload: dict[str, Any]) -> dict[str, Any]:
    total_days = int(state.get("total_days") or 1)
    travelers = int(state.get("passengers") or 2)
    cabin_class = state.get("cabin_class", "economy")
    origin = str(state.get("origin") or state.get("origin_city") or "Origin").title()
    destination = str(state.get("dest") or state.get("destination_city") or "Destination").title()
    selected_transport_mode = normalize_transport_mode(
        state.get("transport_mode") or plan.get("selected_transport_mode") or "flight"
    )
    costs = estimate_trip_costs(total_days, travelers, cabin_class)
    max_budget = _positive_int(state.get("max_budget"))
    budget_profile = build_budget_profile(
        total_days,
        travelers,
        cabin_class,
        max_budget=max_budget,
        transport_mode=selected_transport_mode,
    )

    plan_flights = plan.get("flights")
    supplier_flights = source_payload.get("flights") or source_payload.get("flights_top")
    flight_source = (
        plan_flights
        if _has_usable_price_option(plan_flights, "price")
        else supplier_flights
        if _has_usable_price_option(supplier_flights, "price")
        else plan_flights or supplier_flights
    )
    plan_hotels = plan.get("hotels")
    supplier_hotels = source_payload.get("hotels") or source_payload.get("hotels_top")
    hotel_source = (
        plan_hotels
        if _has_usable_price_option(plan_hotels, "price_per_night", "price", "total_estimate")
        else supplier_hotels
        if _has_usable_price_option(supplier_hotels, "price", "price_per_night", "total_estimate")
        else plan_hotels or supplier_hotels
    )

    flights = normalize_flight_options(
        flight_source,
        origin,
        destination,
        state.get("origin_airport", ""),
        state.get("dest_airport", ""),
        travelers,
        cabin_class,
        target_per_person=budget_profile["target_flight_per_person"],
        max_per_person=budget_profile["target_flight_per_person"] if max_budget else None,
    )
    ground_transport_source = source_payload.get("ground_transport") or plan.get("transport_options") or {}
    if not ground_transport_source and isinstance(source_payload.get("transport_estimates"), dict):
        estimates = source_payload["transport_estimates"]
        ground_transport_source = {
            "train": {"options": estimates.get("train", [])},
            "bus": {"options": estimates.get("bus", [])},
        }
    trains = normalize_ground_transport_options(
        ground_transport_source,
        "train",
        origin,
        destination,
        travelers,
        target_per_person=budget_profile["target_train_per_person"],
        max_per_person=budget_profile["target_transport_per_person"] if max_budget and selected_transport_mode == "train" else None,
    )
    buses = normalize_ground_transport_options(
        ground_transport_source,
        "bus",
        origin,
        destination,
        travelers,
        target_per_person=budget_profile["target_bus_per_person"],
        max_per_person=budget_profile["target_transport_per_person"] if max_budget and selected_transport_mode == "bus" else None,
    )
    hotels = normalize_hotel_options(
        hotel_source,
        destination,
        total_days,
        travelers,
        cabin_class,
        target_nightly=budget_profile["target_hotel_per_night"],
        max_nightly=budget_profile["target_hotel_per_night"] if max_budget else None,
    )
    days = plan.get("days") if isinstance(plan.get("days"), list) else []
    hotel_name = hotels[0]["name"] if hotels else f"{destination} hotel"

    seed = destination_place_seed(destination)
    restaurants = _merge_named_items(
        source_payload.get("restaurants") if isinstance(source_payload.get("restaurants"), list) else [],
        seed.get("restaurants", []),
        12,
    )
    attractions = _merge_named_items(
        source_payload.get("attractions") if isinstance(source_payload.get("attractions"), list) else [],
        seed.get("attractions", []),
        18,
    )

    if len(days) != total_days:
        days = build_day_plans(
            destination,
            state.get("depart_date", ""),
            total_days,
            travelers,
            cabin_class,
            restaurants,
            attractions,
            hotel_name,
            selected_transport_mode=selected_transport_mode,
        )

    _fill_days_from_provider(days, destination, hotel_name, restaurants, attractions, costs)

    daily_total = sum(parse_price(day.get("daily_cost", {}).get("total")) or 0 for day in days)
    selected_options = {"flight": flights, "train": trains, "bus": buses}.get(selected_transport_mode, flights)
    selected_transport_total = _option_total_price(selected_options[0], travelers) if selected_options else None
    flight_total = _option_total_price(flights[0], travelers) if flights else costs["flight_low"]
    hotel_total = parse_price(hotels[0].get("total_estimate")) or costs["hotel_total"]
    grand_total = (selected_transport_total or flight_total) + daily_total

    plan.update(
        {
            "schema_version": "travelai_v11",
            "pipeline": {
                "providers_completed": True,
                "rag_completed": True,
                "compression_completed": True,
                "budget_optimized": True,
            },
            "destination_mode": plan.get("destination_mode") or destination_mode_for(destination),
            "pipeline_status": {
                "rag": True,
                "providers": True,
                "compression": True,
                "generation": True,
            },
            "source_confidence": "medium",
            "title": plan.get("title") or f"{destination} Trip Plan",
            "origin": plan.get("origin") or origin,
            "destination": plan.get("destination") or destination,
            "selected_transport": {
                "mode": selected_transport_mode,
                "total": format_inr(selected_transport_total) if selected_transport_total else 0,
            },
            "selected_hotel": {
                "name": hotels[0].get("name") if hotels else hotel_name,
                "area": hotels[0].get("area") if hotels else "",
                "rating": float(hotels[0].get("rating")) if hotels and str(hotels[0].get("rating") or "").replace(".", "", 1).isdigit() else 0,
                "price_night": parse_price(hotels[0].get("price_per_night")) or 0 if hotels else 0,
                "total": parse_price(hotels[0].get("total_estimate")) or 0 if hotels else 0,
            },
            "date_range": plan.get("date_range")
            or {
                "start": state.get("depart_date", ""),
                "end": state.get("return_date", ""),
                "total_days": total_days,
            },
            "travelers": plan.get("travelers") or travelers,
            "cabin_class": plan.get("cabin_class") or cabin_class,
            "selected_transport_mode": selected_transport_mode,
            "interests": plan.get("interests") or state.get("interests", "sightseeing"),
            "summary": plan.get("summary")
            if isinstance(plan.get("summary"), dict)
            else {
                "text": plan.get("summary") or f"{total_days} days, budget-paced.",
                "days": total_days,
                "budget": max_budget or 0,
            },
            "weather_note": plan.get("weather_note") or "Verify near departure.",
            "flights": flights[:2],
            "trains": trains[:2],
            "buses": buses[:2],
            "transport_options": {
                "flight": flights[:2],
                "train": trains[:2],
                "bus": buses[:2],
            },
            "hotels": hotels[:2],
            "days": days,
            "grouped_days": plan.get("grouped_days") if isinstance(plan.get("grouped_days"), list) else [],
            "cost_summary": plan.get("cost_summary")
            or {
                "transport_mode": selected_transport_mode,
                "selected_transport": format_inr(selected_transport_total) if selected_transport_total else "Transport estimate pending",
                "flights": format_inr(flight_total),
                "flight_per_person": flights[0].get("price_per_person", flights[0].get("price")) if flights else "Flight estimate pending",
                "hotels": hotels[0].get("total_estimate", format_inr(hotel_total)),
                "daily_spend": format_inr(daily_total),
                "grand_total": format_inr(grand_total),
                "notes": "Per-person fares; estimates marked.",
            },
            "sources": plan.get("sources")
            or [
                {
                    "name": "Live suppliers and RAG",
                    "confidence": "Medium",
                    "note": "Live/RAG used.",
                }
            ],
            "booking_tips": plan.get("booking_tips")
            or [
                "Recheck fares before paying.",
                "Keep transfer buffers.",
            ],
            "safety_tips": plan.get("safety_tips")
            or [
                "Use registered night transport.",
                "Verify hours same day.",
            ],
            "ai_insights": plan.get("ai_insights")
            if isinstance(plan.get("ai_insights"), list)
            else ["Budget first", "Mornings lighter"],
        }
    )

    # Normalize v11 day fields while keeping enough metadata for the UI.
    for day in plan.get("days", []) if isinstance(plan.get("days"), list) else []:
        if not isinstance(day, dict):
            continue
        meals = day.get("meals") if isinstance(day.get("meals"), list) else []
        def meal_obj(label: str):
            food = day.get("food") if isinstance(day.get("food"), dict) else {}
            direct = food.get(label) if isinstance(food.get(label), dict) else None
            if direct:
                return {
                    "meal": str(direct.get("meal") or label),
                    "place": str(direct.get("place") or direct.get("name") or ""),
                    "area": str(direct.get("area") or ""),
                    "specialty": str(direct.get("specialty") or direct.get("notes") or ""),
                    "cost": parse_price(direct.get("cost")) or 0,
                }
            m = next(
                (
                    x
                    for x in meals
                    if isinstance(x, dict)
                    and str(x.get("type") or x.get("meal") or "").lower() == label
                ),
                None,
            )
            if not m:
                return {"meal": label, "place":"", "area":"", "specialty":"", "cost":0}
            return {
                "meal": label,
                "place": str(m.get("name") or m.get("place") or ""),
                "area": str(m.get("area") or ""),
                "specialty": str(m.get("notes") or ""),
                "cost": parse_price(m.get("cost")) or 0,
            }
        day["food"] = {"breakfast": meal_obj("breakfast"), "lunch": meal_obj("lunch"), "dinner": meal_obj("dinner")}
        transport_value = day.get("transport")
        transport = transport_value if isinstance(transport_value, list) else []
        t0 = (
            transport_value
            if isinstance(transport_value, dict)
            else transport[0]
            if transport and isinstance(transport[0], dict)
            else {}
        )
        day["local_transport"] = {
            "mode": str(t0.get("mode") or ""),
            "route": str(t0.get("route") or ""),
            "duration": str(t0.get("duration") or ""),
            "cost": parse_price(t0.get("cost")) or 0,
        }
        day["transport"] = {
            "mode": day["local_transport"]["mode"],
            "route": day["local_transport"]["route"],
            "cost": day["local_transport"]["cost"],
        }
        stay = day.get("stay") if isinstance(day.get("stay"), dict) else {}
        stay_name = str(stay.get("name") or stay.get("hotel") or hotel_name or "")
        day["stay"] = {
            "name": stay_name,
            "hotel": stay_name,
            "cost": format_inr(parse_price(stay.get("cost"))) if parse_price(stay.get("cost")) else (stay.get("cost") or "INR 0"),
            "notes": str(stay.get("notes") or "Base stay"),
        }
        day["stay_cost"] = parse_price(day.get("stay", {}).get("cost")) or 0
        day["theme"] = _clean_text(day.get("theme") or day.get("title") or f"Day {day.get('day', '')}").strip()
        day["daily_total"] = parse_price(day.get("daily_total")) or parse_price(day.get("daily_cost", {}).get("total")) or 0
        if not isinstance(day.get("daily_cost"), dict):
            day["daily_cost"] = {}
        if day["daily_total"] and not day["daily_cost"].get("total"):
            day["daily_cost"]["total"] = format_inr(day["daily_total"])

    recalculate_cost_summary(
        plan,
        "Live prices when available; estimates marked.",
    )
    return apply_budget_preferences(plan, max_budget=max_budget, source="planner")


def build_fallback_trip_plan(state: dict[str, Any], source_payload: dict[str, Any], reason: str = "") -> dict[str, Any]:
    plan = {
        "title": f"{str(state.get('dest') or state.get('destination_city') or 'Destination').title()} Trip Plan",
        "summary": "Supplier-backed fallback.",
        "sources": [
            {
                "name": "Fallback planner",
                "confidence": "Medium" if source_payload else "Low",
                "note": reason or "Fallback estimate.",
            }
        ],
    }
    return complete_trip_plan(plan, state, source_payload)
