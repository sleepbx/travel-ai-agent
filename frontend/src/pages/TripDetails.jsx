import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  BedDouble,
  BusFront,
  CalendarDays,
  CarFront,
  ChevronLeft,
  Clock3,
  Compass,
  ExternalLink,
  IndianRupee,
  Info,
  Landmark,
  MapPinned,
  PlaneTakeoff,
  RefreshCw,
  Route,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  SunMedium,
  TrainFront,
  Utensils,
  Wand2,
  WalletCards,
} from "lucide-react";
import { apiUrl } from "../lib/api";
import "./TripDetails.css";

const HOTEL_IMAGES = [
  "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?auto=format&fit=crop&w=900&q=80",
];

const TRANSPORT_COPY = {
  flight: { label: "Flight", plural: "Flights", Icon: PlaneTakeoff },
  train: { label: "Train", plural: "Trains", Icon: TrainFront },
  bus: { label: "Bus", plural: "Buses", Icon: BusFront },
};

function normalizeTransportMode(value) {
  const text = String(value || "flight").toLowerCase();
  if (text.includes("train") || text.includes("rail")) return "train";
  if (text.includes("bus") || text.includes("coach")) return "bus";
  return "flight";
}

function safeJsonParse(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function valueText(value, fallback = "Estimate") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") {
    return Object.values(value).filter(Boolean).join(" ") || fallback;
  }
  return String(value);
}

function priceText(value, fallback = "Estimate") {
  const text = valueText(value, fallback);
  const match = text.match(/(?:INR|Rs\.?)\s*[0-9][0-9,]*(?:\s*-\s*(?:INR|Rs\.?)?\s*[0-9][0-9,]*)?/i);
  return match ? match[0] : text;
}

function hasUsablePrice(value) {
  const text = valueText(value, "").toLowerCase();
  return /(?:inr|rs\.?)\s*[0-9][0-9,]*/i.test(text) && !/(pending|unavailable|tba)/.test(text);
}

function splitLines(text) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trim().replace(/^[-*]\s*/, ""))
    .filter(Boolean);
}

function parseItineraryByDay(itineraryText) {
  if (!itineraryText) return [];

  const matches = [...itineraryText.matchAll(/(?:^|\n)(Day\s+\d+[:\-.]?[^\n]*)/gi)];
  if (matches.length === 0) {
    return [{ title: "Full itinerary", content: itineraryText.trim() }];
  }

  return matches.map((match, index) => {
    const start = match.index + (match[0].startsWith("\n") ? 1 : 0);
    const next = matches[index + 1]?.index ?? itineraryText.length;
    const block = itineraryText.slice(start, next).trim();
    const [titleLine, ...rest] = block.split("\n");

    return {
      title: titleLine.trim(),
      content: rest.join("\n").trim() || block.replace(titleLine, "").trim(),
    };
  });
}

function parseSections(content) {
  const sectionRegex = /^(Places|Travel|Food|Stay|Daily Estimated Cost|Final Notes):?/gim;
  const matches = [...String(content || "").matchAll(sectionRegex)];

  if (matches.length === 0) {
    return [{ label: "Plan", text: content }];
  }

  return matches.map((match, index) => {
    const start = match.index + match[0].length;
    const end = matches[index + 1]?.index ?? content.length;

    return {
      label: match[1],
      text: content.slice(start, end).trim(),
    };
  });
}

function buildLegacyPlan(trip) {
  const legacyText = trip?.itinerary || "";
  const days = parseItineraryByDay(legacyText).map((day, index) => ({
    day: index + 1,
    title: day.title.replace(/^Day\s+\d+[:\-.]?\s*/i, "") || `Day ${index + 1}`,
    summary: "Saved text itinerary converted into a card view.",
    legacySections: parseSections(day.content),
    daily_cost: {
      total:
        parseSections(day.content).find((section) =>
          section.label.toLowerCase().includes("cost")
        )?.text || "See details",
    },
  }));

  return {
    schema_version: "legacy_text",
    title: trip?.title || `${trip?.destination || "Trip"} itinerary`,
    destination: trip?.destination || "Destination",
    origin: "Origin",
    summary: "This saved itinerary predates the new JSON planner, so it is displayed in a polished legacy layout.",
    selected_transport_mode: "flight",
    flights: [],
    trains: [],
    buses: [],
    transport_options: {},
    hotels: [],
    days,
    cost_summary: {},
    booking_tips: ["Regenerate or refine this trip to unlock the full structured JSON view."],
    safety_tips: [],
    sources: [{ name: "Saved itinerary", confidence: "Medium", note: "Parsed from legacy text." }],
    budget_guardrails: {},
  };
}

function normalizeTripPlan(trip) {
  const parsed = safeJsonParse(trip?.itinerary);
  if (!parsed || typeof parsed !== "object") return buildLegacyPlan(trip);

  const days = Array.isArray(parsed.days) ? parsed.days : [];
  const normalizedDays = days.map((day, index) => ({
    ...day,
    day: day.day || index + 1,
    title: day.title || `Day ${index + 1}`,
    summary: day.summary || day.theme || "A balanced day of travel, food, and exploration.",
    activities: Array.isArray(day.activities) ? day.activities : [],
    transport: Array.isArray(day.transport)
      ? day.transport
      : day.transport
        ? [day.transport]
        : day.local_transport
          ? [day.local_transport]
          : [],
    meals: Array.isArray(day.meals)
      ? day.meals
      : day.food
        ? [
            { type: "Breakfast", name: day.food?.breakfast?.place, cost: day.food?.breakfast?.cost, notes: day.food?.breakfast?.specialty },
            { type: "Lunch", name: day.food?.lunch?.place, cost: day.food?.lunch?.cost, notes: day.food?.lunch?.specialty },
            { type: "Dinner", name: day.food?.dinner?.place, cost: day.food?.dinner?.cost, notes: day.food?.dinner?.specialty },
          ].filter((m) => m?.name)
        : [],
    daily_cost: day.daily_cost || {},
  }));

  const summaryText = typeof parsed.summary === "object" && parsed.summary
    ? parsed.summary.text || `${parsed.summary.days || days.length || 1} days, budget-paced.`
    : parsed.summary;

  return {
    ...parsed,
    title: parsed.title || trip?.title || `${trip?.destination || "Trip"} itinerary`,
    destination: parsed.destination || trip?.destination || "Destination",
    origin: parsed.origin || "Origin",
    selected_transport_mode: normalizeTransportMode(parsed.selected_transport_mode),
    summary: summaryText || "A curated travel plan built from saved data and live travel context.",
    flights: Array.isArray(parsed.flights) ? parsed.flights : [],
    trains: Array.isArray(parsed.trains) ? parsed.trains : parsed.transport_options?.train || [],
    buses: Array.isArray(parsed.buses) ? parsed.buses : parsed.transport_options?.bus || [],
    transport_options: parsed.transport_options || {},
    hotels: Array.isArray(parsed.hotels) ? parsed.hotels : [],
    days: normalizedDays,
    booking_tips: Array.isArray(parsed.booking_tips) ? parsed.booking_tips : [],
    safety_tips: Array.isArray(parsed.safety_tips) ? parsed.safety_tips : [],
    sources: Array.isArray(parsed.sources) ? parsed.sources : [],
    cost_summary: parsed.cost_summary || {},
    budget_guardrails: parsed.budget_guardrails || {},
  };
}

function fallbackFlights(plan) {
  if (plan.flights?.length && plan.flights.some((flight) => hasUsablePrice(flight.price_per_person || flight.price))) {
    return plan.flights.slice(0, 2);
  }
  const travelers = Number(plan.travelers || 2);
  const cabin = String(plan.cabin_class || "economy").toLowerCase();
  const cabinFactor = cabin.includes("business") || cabin.includes("luxury")
    ? 2.7
    : cabin.includes("premium")
      ? 1.45
      : 1;
  const low = Math.round(4200 * cabinFactor);
  const high = Math.round(7800 * cabinFactor);
  const formatInr = (amount) => `INR ${amount.toLocaleString("en-IN")}`;
  const range = `${formatInr(low)} - ${formatInr(high)} per person`;
  const totalRange = `${formatInr(low * travelers)} - ${formatInr(high * travelers)}`;
  return [
    {
      airline: "Approx fare watch",
      route: `${plan.origin} to ${plan.destination}`,
      departure: "Check current schedule",
      arrival: "Flexible",
      duration: "Varies",
      price: range,
      price_per_person: range,
      total_price: totalRange,
      passengers: travelers,
      pricing_unit: "per_person",
      booking_note: "Approximate per-person fallback fare shown because saved live pricing is unavailable. Refresh rates before booking.",
      source: "Approx estimate",
    },
    {
      airline: "Flexible timing estimate",
      route: `${plan.origin} to ${plan.destination}`,
      departure: "Morning or evening",
      arrival: "Same day",
      duration: "Varies",
      price: `${formatInr(Math.round(low * 1.1))} - ${formatInr(Math.round(high * 1.2))} per person`,
      price_per_person: `${formatInr(Math.round(low * 1.1))} - ${formatInr(Math.round(high * 1.2))} per person`,
      total_price: `${formatInr(Math.round(low * 1.1) * travelers)} - ${formatInr(Math.round(high * 1.2) * travelers)}`,
      passengers: travelers,
      pricing_unit: "per_person",
      booking_note: "Compare this route again before payment because fares change quickly.",
      source: "Approx estimate",
    },
  ];
}

function fallbackGroundOptions(plan, mode) {
  const key = mode === "train" ? "trains" : "buses";
  if (plan[key]?.length && plan[key].some((option) => hasUsablePrice(option.price_per_person || option.price))) {
    return plan[key].slice(0, 2);
  }

  const travelers = Number(plan.travelers || 2);
  const low = mode === "train" ? 550 : 650;
  const high = mode === "train" ? 1900 : 2200;
  const duration = mode === "train" ? "6-18h by route" : "5-16h by route";
  const formatInr = (amount) => `INR ${amount.toLocaleString("en-IN")}`;
  const label = TRANSPORT_COPY[mode].label;

  return [
    {
      mode,
      operator: `Cheapest ${label.toLowerCase()} watch`,
      service_name: `${label} fare estimate`,
      route: `${plan.origin} to ${plan.destination}`,
      departure: "Flexible",
      arrival: "Check live timetable",
      duration,
      price: `${formatInr(low)} - ${formatInr(high)} per person`,
      price_per_person: `${formatInr(low)} - ${formatInr(high)} per person`,
      total_price: `${formatInr(low * travelers)} - ${formatInr(high * travelers)}`,
      passengers: travelers,
      pricing_unit: "per_person",
      booking_note: `Offline ${label.toLowerCase()} estimate. Verify schedule and final fare before booking.`,
      source: "Approx estimate",
    },
  ];
}

function selectedTransportOptions(plan, flights, trains, buses) {
  const selected = normalizeTransportMode(plan.selected_transport_mode);
  if (selected === "train") return trains;
  if (selected === "bus") return buses;
  return flights;
}

function fallbackHotels(plan) {
  if (plan.hotels?.length) return plan.hotels.slice(0, 2);
  return [
    {
      name: `Central ${plan.destination} stay`,
      area: "Central area",
      rating: "Estimate",
      price_per_night: "INR estimate pending",
      total_estimate: "INR compare before booking",
      why: "Good default base for sightseeing, food, and short transfers.",
      source: "Estimate",
    },
    {
      name: `${plan.destination} comfort hotel`,
      area: "Well-connected neighborhood",
      rating: "Estimate",
      price_per_night: "INR estimate pending",
      total_estimate: "INR compare before booking",
      why: "A calmer option when you want easier evenings and predictable transport.",
      source: "Estimate",
    },
  ];
}

function SectionIcon({ label }) {
  const normalized = String(label || "").toLowerCase();
  if (normalized.includes("place")) return <Landmark size={18} />;
  if (normalized.includes("travel")) return <Route size={18} />;
  if (normalized.includes("food")) return <Utensils size={18} />;
  if (normalized.includes("stay")) return <BedDouble size={18} />;
  if (normalized.includes("cost")) return <WalletCards size={18} />;
  return <Sparkles size={18} />;
}

function MetricPill({ icon, label, value }) {
  return (
    <div className="metric-pill">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TransportCard({ option, index, mode }) {
  const selectedMode = normalizeTransportMode(mode || option.mode);
  const copy = TRANSPORT_COPY[selectedMode] || TRANSPORT_COPY.flight;
  const Icon = copy.Icon;
  const title = selectedMode === "flight"
    ? valueText(option.airline, "Flight option")
    : valueText(option.operator || option.service_name, `${copy.label} option`);
  const subtitle = selectedMode === "flight"
    ? valueText(option.route)
    : valueText(option.service_name || option.route, option.route);
  const price = priceText(option.price_per_person || option.price, "Estimate");
  const total = priceText(option.total_price, "");

  return (
    <article className={`travel-option transport-option ${selectedMode}-option`}>
      <div className="option-kicker">
        <span>{copy.label} {String(index + 1).padStart(2, "0")}</span>
        <BadgeCheck size={17} />
      </div>
      <div className="option-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <strong>
          {price}
          <small>per person</small>
        </strong>
      </div>
      <div className="option-grid">
        <span><Clock3 size={15} /> {valueText(option.departure, "Departure TBA")}</span>
        <span><Icon size={15} /> {valueText(option.duration, "Duration TBA")}</span>
        <span><IndianRupee size={15} /> {total ? `${total} total` : valueText(option.source, "Pricing source")}</span>
      </div>
      <small>{valueText(option.booking_note || option.source, "Verify before booking")}</small>
    </article>
  );
}

function HotelCard({ hotel, index }) {
  const price = priceText(hotel.price_per_night || hotel.price, "Estimate");
  const hotelImage = hotel.image || `https://source.unsplash.com/900x600/?${encodeURIComponent(`${hotel.name || "hotel"} ${hotel.area || ""} travel hotel`)}`;

  return (
    <article className="travel-option hotel-option">
      <img
        src={hotelImage}
        alt=""
        onError={(event) => {
          event.currentTarget.src = HOTEL_IMAGES[index % HOTEL_IMAGES.length];
        }}
      />
      <div className="hotel-body">
        <div className="option-kicker">
          <span>Stay {String(index + 1).padStart(2, "0")}</span>
          <Star size={17} />
        </div>
        <div className="option-heading">
          <div>
            <h3>{valueText(hotel.name, "Hotel option")}</h3>
            <p>{valueText(hotel.area || hotel.address || hotel.why, "Convenient base")}</p>
          </div>
          <strong>{price}</strong>
        </div>
        <div className="hotel-meta">
          <span>{valueText(hotel.rating, "Rating TBA")}</span>
          <span>{valueText(hotel.total_estimate, "Total TBA")}</span>
        </div>
        <small>{valueText(hotel.why || hotel.source, "Verify live availability before booking.")}</small>
      </div>
    </article>
  );
}

function CostStrip({ cost }) {
  const items = [
    ["Activities", cost?.activities],
    ["Transport", cost?.transport],
    ["Food", cost?.food],
    ["Stay", cost?.stay],
    ["Total", cost?.total],
  ].filter(([, value]) => value);

  if (!items.length) return null;

  return (
    <div className="cost-strip">
      {items.map(([label, value]) => (
        <span key={label} className={label === "Total" ? "total" : ""}>
          {label}
          <strong>{valueText(value)}</strong>
        </span>
      ))}
    </div>
  );
}

function ActivityList({ title, icon, items, renderItem }) {
  if (!items?.length) return null;

  return (
    <div className="day-module">
      <div className="module-title">
        {icon}
        <h4>{title}</h4>
      </div>
      <div className="module-list">
        {items.map((item, index) => (
          <div className="module-row" key={`${title}-${index}`}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>
    </div>
  );
}

function LegacySection({ section }) {
  const lines = splitLines(section.text);

  return (
    <div className="day-module legacy-module">
      <div className="module-title">
        <SectionIcon label={section.label} />
        <h4>{section.label}</h4>
      </div>
      <div className="legacy-lines">
        {lines.map((line, index) => (
          <p key={`${section.label}-${index}`}>{line}</p>
        ))}
      </div>
    </div>
  );
}

function DayCard({ day, index, destination, selected, onSelect }) {
  return (
    <article className={`premium-day ${selected ? "selected" : "compact"}`} onClick={onSelect}>
      <div className="day-content">
        <div className="day-heading-row">
          <div>
            <span className="day-date">{formatDate(day.date) || destination}</span>
            <h3>{day.title}</h3>
            <p>{day.summary}</p>
          </div>
          <SunMedium size={26} />
        </div>

        <CostStrip cost={day.daily_cost} />

        {!selected ? null : day.legacySections ? (
          <div className="legacy-grid">
            {day.legacySections.map((section) => (
              <LegacySection section={section} key={`${day.day}-${section.label}`} />
            ))}
          </div>
        ) : (
          <div className="day-modules">
            <ActivityList
              title="Experiences"
              icon={<Landmark size={18} />}
              items={day.activities}
              renderItem={(activity) => (
                <>
                  <strong>{valueText(activity.time, "Any time")} - {valueText(activity.title, "Activity")}</strong>
                  <span>{valueText(activity.location || activity.area, destination)} - {valueText(activity.cost, "Cost TBA")}</span>
                  <p>{valueText(activity.notes, "Planned from trip context.")}</p>
                </>
              )}
            />

            <ActivityList
              title="Transport"
              icon={<CarFront size={18} />}
              items={day.transport}
              renderItem={(transport) => (
                <>
                  <strong>{valueText(transport.mode, "Transport")} - {valueText(transport.route, "Route TBA")}</strong>
                  <span>{valueText(transport.duration, "Timing TBA")} - {valueText(transport.cost, "Cost TBA")}</span>
                  <p>{valueText(transport.notes, "Verify timing before departure.")}</p>
                </>
              )}
            />

            <ActivityList
              title="Food"
              icon={<Utensils size={18} />}
              items={day.meals}
              renderItem={(meal) => (
                <>
                  <strong>{valueText(meal.type, "Meal")} - {valueText(meal.name, "Local option")}</strong>
                  <span>{valueText(meal.cost, "Cost TBA")}</span>
                  <p>{valueText(meal.notes, "Local dining suggestion.")}</p>
                </>
              )}
            />

            {day.stay && (
              <div className="day-module stay-module">
                <div className="module-title">
                  <BedDouble size={18} />
                  <h4>Stay</h4>
                </div>
                <div className="module-row">
                  <strong>{valueText(day.stay.name, "Hotel or area")}</strong>
                  <span>{valueText(day.stay.cost, "Cost TBA")}</span>
                  <p>{valueText(day.stay.notes, "Base for the night.")}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </article>
  );
}

export default function TripDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [instruction, setInstruction] = useState("");
  const [refining, setRefining] = useState(false);
  const [selectedDay, setSelectedDay] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const fetchTrip = async () => {
      try {
        const res = await fetch(apiUrl("/trips/my"), {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch trips");

        const trips = await res.json();
        const found = trips.find((t) => t.id === id);

        if (!found) {
          navigate("/dashboard");
          return;
        }

        setTrip(found);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrip();
  }, [id, navigate]);

  const plan = useMemo(() => normalizeTripPlan(trip), [trip]);
  const flights = useMemo(() => fallbackFlights(plan), [plan]);
  const trains = useMemo(() => fallbackGroundOptions(plan, "train"), [plan]);
  const buses = useMemo(() => fallbackGroundOptions(plan, "bus"), [plan]);
  const selectedMode = normalizeTransportMode(plan.selected_transport_mode);
  const transportOptions = useMemo(
    () => selectedTransportOptions(plan, flights, trains, buses),
    [plan, flights, trains, buses]
  );
  const hotels = useMemo(() => fallbackHotels(plan), [plan]);
  const activeDay = plan.days?.[selectedDay] || plan.days?.[0];
  const refinePresets = [
    {
      label: "Refresh rates",
      icon: <RefreshCw size={15} />,
      text: "Refresh the latest available flight rates and hotel rates, use online estimates if live rates are unavailable, and keep everything close to my budget.",
    },
    {
      label: "Cheaper route",
      icon: <PlaneTakeoff size={15} />,
      text: "Make my selected transport cheaper and keep fares per person as low as possible.",
    },
    {
      label: "Try train",
      icon: <TrainFront size={15} />,
      text: "Switch the selected transport to train, account for travel time, and keep the fare per person cheap.",
    },
    {
      label: "Try bus",
      icon: <BusFront size={15} />,
      text: "Switch the selected transport to bus, account for travel time, and keep the fare per person cheap.",
    },
    {
      label: "Lower hotel rate",
      icon: <BedDouble size={15} />,
      text: "Reduce the hotel rate and choose the closest good stay near my requested price.",
    },
    {
      label: "Reduce total",
      icon: <WalletCards size={15} />,
      text: "Lower the total trip cost while keeping the itinerary practical.",
    },
  ];

  useEffect(() => {
    if (selectedDay >= (plan.days?.length || 0)) setSelectedDay(0);
  }, [plan.days?.length, selectedDay]);

  const handleRefine = async () => {
    if (!instruction.trim()) return;

    setRefining(true);

    try {
      const token = localStorage.getItem("token");

      const res = await fetch(apiUrl(`/trips/${id}/refine`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ instruction }),
      });

      if (!res.ok) throw new Error("Refine failed");

      const data = await res.json();

      setTrip((prev) => ({
        ...prev,
        itinerary: data.updated_itinerary,
      }));

      setInstruction("");
      setSelectedDay(0);
    } catch (err) {
      console.error(err);
      alert("Failed to refine trip");
    } finally {
      setRefining(false);
    }
  };

  const addRefinePreset = (preset) => {
    setInstruction((current) => (current.trim() ? `${current.trim()} ${preset}` : preset));
  };

  if (loading) {
    return (
      <div className="trip-details page-wrap">
        <div className="trip-loading">Loading trip...</div>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="trip-details page-wrap">
        <div className="trip-loading">Trip not found</div>
      </div>
    );
  }

  return (
    <div className="trip-details page-wrap">
      <button className="back-link" onClick={() => navigate("/dashboard")}>
        <ChevronLeft size={18} />
        Back to trips
      </button>

      <section className="trip-hero deluxe-hero">
        <div className="hero-copy">
          <span className="eyebrow dark"><MapPinned size={16} /> AI itinerary dossier</span>
          <h1>{plan.title}</h1>
          <p>{plan.summary}</p>
          <div className="hero-metrics">
            <MetricPill icon={<Compass size={17} />} label="Route" value={`${plan.origin} -> ${plan.destination}`} />
            <MetricPill icon={<CalendarDays size={17} />} label="Days" value={plan.date_range?.total_days || plan.days.length || 1} />
            <MetricPill icon={<WalletCards size={17} />} label="Total" value={valueText(plan.cost_summary?.grand_total, "Estimated")} />
          </div>
        </div>
        <div className="hero-glass">
          <span>Source confidence</span>
          <strong>{valueText(plan.sources?.[0]?.confidence, "Mixed")}</strong>
          <p>{valueText(plan.weather_note || plan.cost_summary?.notes, "Live details are blended with planner estimates.")}</p>
        </div>
      </section>

      <section className="booking-showcase">
        <div className="section-title">
          <div>
            <span>Bookable options</span>
            <h2>{TRANSPORT_COPY[selectedMode].plural} and stays</h2>
          </div>
          {(() => {
            const Icon = TRANSPORT_COPY[selectedMode].Icon;
            return <Icon size={24} />;
          })()}
        </div>

        <div className="transport-mode-strip" aria-label="Available transport comparison">
          {["flight", "train", "bus"].map((mode) => {
            const copy = TRANSPORT_COPY[mode];
            const Icon = copy.Icon;
            const count = mode === "flight" ? flights.length : mode === "train" ? trains.length : buses.length;
            return (
              <span className={selectedMode === mode ? "active" : ""} key={mode}>
                <Icon size={15} />
                {copy.label}
                <strong>{selectedMode === mode ? "Selected" : `${count} option${count === 1 ? "" : "s"}`}</strong>
              </span>
            );
          })}
        </div>

        <div className="option-layout">
          <div className="option-column">
            {transportOptions.map((option, index) => (
              <TransportCard option={option} index={index} mode={selectedMode} key={`transport-${selectedMode}-${index}`} />
            ))}
          </div>
          <div className="option-column hotel-column">
            {hotels.map((hotel, index) => (
              <HotelCard hotel={hotel} index={index} key={`hotel-${index}`} />
            ))}
          </div>
        </div>
      </section>

      <div className="trip-layout deluxe-layout">
        <section className="itinerary-panel deluxe-panel">
          <div className="section-title">
            <div>
              <span>Day-wise route</span>
              <h2>Itinerary and daily costs</h2>
            </div>
            <div className="timeline-count">
              <Clock3 size={18} />
              <strong>{plan.days.length || 1}</strong>
            </div>
          </div>

          {activeDay && (
            <div className="active-day-spotlight">
              <div>
                <span>Now focused</span>
                <h3>Day {activeDay.day}: {activeDay.title}</h3>
                <p>{activeDay.summary}</p>
              </div>
              <div className="spotlight-cost">
                <IndianRupee size={21} />
                <strong>{valueText(activeDay.daily_cost?.total, "Estimate")}</strong>
              </div>
            </div>
          )}

          <div className="day-tabs" aria-label="Itinerary day shortcuts">
            {(plan.days.length ? plan.days : [{ day: 1, title: "Plan" }]).map((day, index) => (
              <button
                key={`tab-${day.day}-${index}`}
                className={selectedDay === index ? "active" : ""}
                onClick={() => setSelectedDay(index)}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                {day.title}
              </button>
            ))}
          </div>

          <div className="premium-timeline">
            {(plan.days.length ? plan.days : buildLegacyPlan(trip).days).map((day, index) => (
              <DayCard
                day={day}
                index={index}
                destination={plan.destination}
                selected={selectedDay === index}
                onSelect={() => setSelectedDay(index)}
                key={`day-${day.day}-${index}`}
              />
            ))}
          </div>
        </section>

        <aside className="refine-panel deluxe-refine">
          <div className="section-title compact">
            <div>
              <span>AI editor</span>
              <h2>Refine trip</h2>
            </div>
            <Wand2 size={22} />
          </div>

          <p>
            Ask for a cheaper plan, more luxury, fewer transfers, food-first days, family pacing, or nightlife.
          </p>

          <div className="refine-presets" aria-label="Quick refinement prompts">
            {refinePresets.map((preset) => (
              <button type="button" onClick={() => addRefinePreset(preset.text)} key={preset.label}>
                {preset.icon}
                {preset.label}
              </button>
            ))}
          </div>

          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Example: Keep the hotel under INR 4,000 per night and find the nearest flight fare below INR 8,000."
            rows={6}
          />

          <button className="refine-submit" onClick={handleRefine} disabled={refining || !instruction.trim()}>
            {refining ? (
              <>
                <Sparkles size={18} />
                Refining...
              </>
            ) : (
              <>
                <Send size={18} />
                Refine itinerary
              </>
            )}
          </button>

          <div className="cost-summary-box">
            <div>
              <IndianRupee size={19} />
              <span>Estimated trip cost</span>
            </div>
            <strong>{valueText(plan.cost_summary?.grand_total, "Needs live pricing")}</strong>
            <p>{valueText(plan.cost_summary?.notes, "Flights, hotel rates, and local costs should be verified before payment.")}</p>
          </div>

          {plan.budget_guardrails?.status && (
            <div className="guardrail-box">
              <div>
                <WalletCards size={18} />
                <span>Budget guardrails</span>
              </div>
              <strong>{valueText(plan.budget_guardrails.status)}</strong>
              <p>{valueText(plan.budget_guardrails.note)}</p>
              <div className="guardrail-targets">
                {[
                  ["Total", plan.budget_guardrails.target_total],
                  ["Flight", plan.budget_guardrails.target_flight],
                  ["Hotel", plan.budget_guardrails.target_hotel_per_night],
                  ["Daily", plan.budget_guardrails.target_daily],
                ]
                  .filter(([, value]) => value)
                  .map(([label, value]) => (
                    <span key={label}>
                      {label}
                      <strong>{value}</strong>
                    </span>
                  ))}
              </div>
            </div>
          )}

          <div className="tips-stack">
            {[...plan.booking_tips, ...plan.safety_tips].slice(0, 4).map((tip, index) => (
              <div className="tip-row" key={`tip-${index}`}>
                {index < plan.booking_tips.length ? <Info size={17} /> : <ShieldCheck size={17} />}
                <span>{tip}</span>
              </div>
            ))}
          </div>

          <div className="source-list">
            <h3>Sources</h3>
            {(plan.sources.length ? plan.sources : [{ name: "Planner", confidence: "Estimate", note: "No source metadata returned." }]).map((source, index) => (
              <div className="source-row" key={`source-${index}`}>
                <ExternalLink size={16} />
                <div>
                  <strong>{source.name}</strong>
                  <span>{valueText(source.confidence)} - {valueText(source.note, "Used for planning context")}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
