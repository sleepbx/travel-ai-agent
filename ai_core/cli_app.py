# cli_app.py — CLI interface for TravelAI (FINAL FIX)

from datetime import datetime
from agent_core import TravelAI


def main():
    print("=== TravelAI – Full Trip Planner (Conversational CLI) ===\n")

    # ---------------- USER INPUT ----------------
    origin_city = input("From city: ").strip()
    destination_city = input("To city: ").strip()

    depart = input("Depart date (YYYY-MM-DD): ").strip()
    return_date = input("Return date (YYYY-MM-DD): ").strip()

    passengers_raw = input("Passengers (default 2): ").strip()
    passengers = int(passengers_raw) if passengers_raw.isdigit() else 2

    cabin_class = input(
        "Cabin class (economy/premium_economy/business/first) [default economy]: "
    ).strip() or "economy"

    transport_mode = input(
        "Preferred transport (flight/train/bus) [default flight]: "
    ).strip() or "flight"

    interests = input(
        "Your interests (food/nightlife/history/adventure/etc) [default sightseeing]: "
    ).strip() or "sightseeing"

    budget_raw = input(
        "Approx TOTAL budget for the whole trip in INR (optional, press Enter to skip): "
    ).strip()
    max_budget = int(budget_raw) if budget_raw.isdigit() else None

    # ---------------- DATE HANDLING (DISPLAY ONLY) ----------------
    try:
        fmt = "%Y-%m-%d"
        d_depart = datetime.strptime(depart, fmt)
        d_return = datetime.strptime(return_date, fmt)
        days = (d_return - d_depart).days + 1
        if days < 1:
            days = 1
        print(f"\nComputed trip length: {days} day(s)\n")
    except Exception:
        print("\n⚠️ Could not compute trip length from dates.\n")

    print("Generating your full itinerary... Please wait...\n")

    # ---------------- AGENT INIT ----------------
    agent = TravelAI()

    try:
        # ---------------- INITIAL ITINERARY ----------------
        itinerary = agent.plan_full_trip(
            origin_city=origin_city,
            destination_city=destination_city,
            depart_date=depart,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            transport_mode=transport_mode,
            interests=interests,
            max_budget=max_budget,
        )

        print("\n=== INITIAL ITINERARY ===\n")
        print(itinerary)

        # ---------------- REFINEMENT LOOP ----------------
        while True:
            print("\nYou can now tweak your plan.")
            print("Examples:")
            print("  - make it more budget friendly")
            print("  - add more nightlife on day 2")
            print("  - reduce travel time, keep places nearby")
            print("  - add more shopping and remove museums")
            print("Type 'done' to finish.\n")

            user_change = input("What would you like to change? ").strip()

            if user_change.lower() in ("done", "exit", "quit", "no", "n"):
                print("\n✅ Final itinerary confirmed. Have a great trip! ✈️")
                break

            print("\nUpdating your itinerary based on your request...\n")

            itinerary = agent.refine_itinerary(
                existing_itinerary=itinerary,
                user_request=user_change,
            )

            print("\n=== UPDATED ITINERARY ===\n")
            print(itinerary)

    except Exception as e:
        print("\n[ERROR] Failed to generate or refine trip:")
        print(e)


if __name__ == "__main__":
    main()
