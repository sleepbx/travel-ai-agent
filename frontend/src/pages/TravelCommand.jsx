import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  BadgeCheck,
  BedDouble,
  BusFront,
  CalendarDays,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Clock3,
  Compass,
  IndianRupee,
  Luggage,
  PlaneTakeoff,
  RefreshCw,
  Route,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  TrainFront,
  WalletCards,
  Wand2,
} from "lucide-react";
import { apiUrl, backendUnavailableMessage } from "../lib/api";
import "./TravelCommand.css";

const TASKS = [
  { id: "rates", label: "Refresh transport and hotel rates", icon: RefreshCw },
  { id: "hotel", label: "Confirm cancellation and check-in rules", icon: BedDouble },
  { id: "transfer", label: "Save terminal or station transfer plan", icon: Route },
  { id: "docs", label: "Keep IDs, tickets, and bookings offline", icon: ShieldCheck },
  { id: "pack", label: "Pack weather-specific essentials", icon: Luggage },
];

const QUICK_COMMANDS = [
  "Refresh the latest available selected transport rates and hotel rates, use online estimates if live rates are unavailable, and keep everything close to my budget.",
  "Make this trip cheaper without making the days feel rushed.",
  "Find a better hotel value near a safe central area and update the total cost.",
];

const TRANSPORT_COPY = {
  flight: { label: "Flight", Icon: PlaneTakeoff },
  train: { label: "Train", Icon: TrainFront },
  bus: { label: "Bus", Icon: BusFront },
};

function safeJsonParse(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function valueText(value, fallback = "Estimate") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") return Object.values(value).filter(Boolean).join(" ") || fallback;
  return String(value);
}

function formatDate(value) {
  if (!value) return "Dates pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function priceNumber(value) {
  const text = valueText(value, "");
  const match = text.match(/([0-9][0-9,]{2,})/);
  return match ? Number(match[1].replaceAll(",", "")) : 0;
}

function hasUsablePrice(value) {
  const text = valueText(value, "").toLowerCase();
  return /(?:inr|rs\.?)\s*[0-9][0-9,]*/i.test(text) && !/(pending|unavailable|tba)/.test(text);
}

function normalizeTransportMode(value) {
  const text = String(value || "flight").toLowerCase();
  if (text.includes("train") || text.includes("rail")) return "train";
  if (text.includes("bus") || text.includes("coach")) return "bus";
  return "flight";
}

function transportList(plan) {
  const selected = normalizeTransportMode(plan.selected_transport_mode);
  if (selected === "train") return plan.trains || plan.transport_options?.train || [];
  if (selected === "bus") return plan.buses || plan.transport_options?.bus || [];
  return plan.flights || plan.transport_options?.flight || [];
}

function approximateTransport(plan) {
  const mode = normalizeTransportMode(plan.selected_transport_mode);
  const existing = transportList(plan).find((option) => hasUsablePrice(option.price_per_person || option.price));
  if (existing) return existing;

  const travelers = Number(plan.travelers || 2);
  const cabin = String(plan.cabin_class || "economy").toLowerCase();
  const factor = cabin.includes("business") || cabin.includes("luxury") ? 2.7 : cabin.includes("premium") ? 1.45 : 1;
  const low = mode === "flight" ? Math.round(4200 * factor) : mode === "train" ? 550 : 650;
  const high = mode === "flight" ? Math.round(7800 * factor) : mode === "train" ? 1900 : 2200;
  const label = TRANSPORT_COPY[mode].label;

  return {
    mode,
    airline: mode === "flight" ? "Approx fare watch" : "",
    operator: mode === "flight" ? "" : `Approx ${label.toLowerCase()} watch`,
    route: `${plan.origin || "Origin"} to ${plan.destination || "Destination"}`,
    price: `INR ${low.toLocaleString("en-IN")} - INR ${high.toLocaleString("en-IN")} per person`,
    price_per_person: `INR ${low.toLocaleString("en-IN")} - INR ${high.toLocaleString("en-IN")} per person`,
    total_price: `INR ${(low * travelers).toLocaleString("en-IN")} - INR ${(high * travelers).toLocaleString("en-IN")}`,
  };
}

function planForTrip(trip) {
  const parsed = safeJsonParse(trip?.itinerary);
  if (parsed && typeof parsed === "object") return parsed;
  return {
    title: trip?.title || `${trip?.destination || "Trip"} itinerary`,
    destination: trip?.destination || "Destination",
    origin: "Origin",
    selected_transport_mode: "flight",
    flights: [],
    trains: [],
    buses: [],
    transport_options: {},
    hotels: [],
    days: [],
    cost_summary: {},
    sources: [],
    budget_guardrails: {},
  };
}

function isEstimate(option) {
  const text = [
    option?.source,
    option?.price,
    option?.price_per_night,
    option?.booking_note,
    option?.why,
  ]
    .map((part) => valueText(part, ""))
    .join(" ")
    .toLowerCase();

  return /estimate|fallback|offline|target range|pending/.test(text);
}

function buildTripHealth(plan) {
  const hasTransport = transportList(plan).length > 0;
  const hasHotel = Array.isArray(plan.hotels) && plan.hotels.length > 0;
  const hasDays = Array.isArray(plan.days) && plan.days.length > 0;
  const hasCost = Boolean(plan.cost_summary?.grand_total);
  const hasSources = Array.isArray(plan.sources) && plan.sources.length > 0;
  const rateEstimate =
    (hasTransport && isEstimate(transportList(plan)[0])) || (hasHotel && isEstimate(plan.hotels[0]));

  const score =
    (hasTransport ? 18 : 0) +
    (hasHotel ? 18 : 0) +
    (hasDays ? 24 : 0) +
    (hasCost ? 18 : 0) +
    (hasSources ? 12 : 0) +
    (!rateEstimate ? 10 : 4);

  return {
    score: Math.min(score, 100),
    label: score >= 82 ? "Booking ready" : score >= 62 ? "Needs rate check" : "Needs planning",
    rateEstimate,
  };
}

function TransportRate({ option, mode }) {
  const selected = normalizeTransportMode(mode || option?.mode);
  const copy = TRANSPORT_COPY[selected] || TRANSPORT_COPY.flight;
  const Icon = copy.Icon;
  return (
    <div className="rate-row">
      <Icon size={18} />
      <div>
        <strong>{valueText(option?.airline || option?.operator, `${copy.label} option`)}</strong>
        <span>{valueText(option?.route, "Route pending")}</span>
      </div>
      <b>{valueText(option?.price_per_person || option?.price, "Rate pending")}</b>
    </div>
  );
}

function HotelRate({ hotel }) {
  return (
    <div className="rate-row">
      <BedDouble size={18} />
      <div>
        <strong>{valueText(hotel?.name, "Hotel option")}</strong>
        <span>{valueText(hotel?.area || hotel?.address, "Area pending")}</span>
      </div>
      <b>{valueText(hotel?.price_per_night || hotel?.price, "Rate pending")}</b>
    </div>
  );
}

export default function TravelCommand() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState("");
  const [completedTasks, setCompletedTasks] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("travelai-command-tasks") || "{}");
    } catch {
      return {};
    }
  });
  const [command, setCommand] = useState("");
  const [refining, setRefining] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const fetchTrips = async () => {
      try {
        const res = await fetch(apiUrl("/trips/my"), {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }

        const data = await res.json();
        setTrips(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to load Travel HQ", err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrips();
  }, [navigate]);

  useEffect(() => {
    if (!selectedTripId && trips.length) setSelectedTripId(trips[0].id);
  }, [selectedTripId, trips]);

  const selectedTrip = useMemo(
    () => trips.find((trip) => trip.id === selectedTripId) || trips[0],
    [selectedTripId, trips]
  );
  const selectedPlan = useMemo(() => planForTrip(selectedTrip), [selectedTrip]);
  const health = useMemo(() => buildTripHealth(selectedPlan), [selectedPlan]);
  const selectedTransportMode = normalizeTransportMode(selectedPlan.selected_transport_mode);
  const selectedTransport = approximateTransport(selectedPlan);
  const selectedHotel = selectedPlan.hotels?.[0];
  const totalBudget = valueText(selectedPlan.cost_summary?.grand_total, "Budget pending");
  const transportCost = priceNumber(selectedTransport?.total_price || selectedTransport?.price);
  const dailyCost = priceNumber(selectedPlan.cost_summary?.daily_spend);
  const budgetPressure = Math.min(Math.round(((transportCost + dailyCost) / Math.max(priceNumber(totalBudget), 1)) * 100), 100);

  useEffect(() => {
    localStorage.setItem("travelai-command-tasks", JSON.stringify(completedTasks));
  }, [completedTasks]);

  const toggleTask = (taskId) => {
    if (!selectedTrip?.id) return;
    const key = `${selectedTrip.id}:${taskId}`;
    setCompletedTasks((current) => ({ ...current, [key]: !current[key] }));
  };

  const runCommand = async (instruction) => {
    if (!selectedTrip?.id || !instruction.trim()) return;

    setRefining(true);
    setMessage("");

    try {
      const token = localStorage.getItem("token");
      const res = await fetch(apiUrl(`/trips/${selectedTrip.id}/refine`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ instruction }),
      });

      if (!res.ok) throw new Error("Travel HQ command failed");

      const data = await res.json();
      setTrips((current) =>
        current.map((trip) =>
          trip.id === selectedTrip.id
            ? { ...trip, itinerary: data.updated_itinerary, updated_at: new Date().toISOString() }
            : trip
        )
      );
      setCommand("");
      setMessage("Trip updated with the latest budget-aware refinement.");
    } catch (err) {
      const text = err instanceof TypeError ? backendUnavailableMessage() : err.message;
      setMessage(text);
    } finally {
      setRefining(false);
    }
  };

  if (loading) {
    return (
      <div className="command-page page-wrap">
        <div className="trip-loading">Loading Travel HQ...</div>
      </div>
    );
  }

  if (!trips.length) {
    return (
      <div className="command-page page-wrap">
        <section className="command-empty">
          <Sparkles size={34} />
          <h1>Travel HQ is ready when your first trip is.</h1>
          <p>Create an itinerary, then come back here for rate refreshes, readiness tasks, and quick AI refinements.</p>
          <button onClick={() => navigate("/")}>Plan a trip</button>
        </section>
      </div>
    );
  }

  return (
    <div className="command-page page-wrap">
      <section className="command-hero">
        <div>
          <span className="eyebrow dark"><Compass size={16} /> Travel HQ</span>
          <h1>Run every trip like it is almost ready to book.</h1>
          <p>
            Watch prices, keep budget pressure visible, finish the practical checklist, and ask TravelAI to refine
            transport, hotels, pacing, food, safety, or total cost from one place.
          </p>
        </div>

        <div className="hero-readiness" style={{ "--score": `${health.score}%` }}>
          <div className="command-ring">
            <strong>{health.score}</strong>
            <span>ready</span>
          </div>
          <div>
            <span>Current trip</span>
            <h2>{selectedTrip?.title || selectedPlan.title}</h2>
            <p>{health.label}</p>
          </div>
        </div>
      </section>

      <section className="command-layout">
        <aside className="trip-switcher">
          <div className="tool-heading">
            <div>
              <span>Trips</span>
              <h2>Active board</h2>
            </div>
            <BadgeCheck size={22} />
          </div>

          <div className="switcher-list">
            {trips.map((trip) => {
              const plan = planForTrip(trip);
              const tripHealth = buildTripHealth(plan);
              return (
                <button
                  className={trip.id === selectedTrip?.id ? "switcher-trip active" : "switcher-trip"}
                  onClick={() => setSelectedTripId(trip.id)}
                  key={trip.id}
                >
                  <strong>{trip.title || `${trip.destination} Trip`}</strong>
                  <span>{plan.origin || "Origin"} to {plan.destination || trip.destination}</span>
                  <small>{tripHealth.score}% ready - {formatDate(trip.updated_at || trip.created_at)}</small>
                </button>
              );
            })}
          </div>
        </aside>

        <div className="command-main">
          <section className="command-panel price-watch">
            <div className="tool-heading">
              <div>
                <span>Price watch</span>
                <h2>Budget and live-rate pressure</h2>
              </div>
              {health.rateEstimate ? <AlertTriangle size={22} /> : <CheckCircle2 size={22} />}
            </div>

            <div className="watch-grid">
              <div className="budget-pulse">
                <div className="pulse-top">
                  <WalletCards size={22} />
                  <span>Total estimate</span>
                </div>
                <strong>{totalBudget}</strong>
                <div className="pressure-meter" aria-label="Budget pressure">
                  <div style={{ width: `${budgetPressure || 48}%` }}></div>
                </div>
                <p>{valueText(selectedPlan.cost_summary?.notes, "Rates are estimates until checkout confirms them.")}</p>
              </div>

              <div className="rate-stack">
                <TransportRate option={selectedTransport} mode={selectedTransportMode} />
                <HotelRate hotel={selectedHotel} />
              </div>
            </div>

            <button className="panel-action" onClick={() => runCommand(QUICK_COMMANDS[0])} disabled={refining}>
              <RefreshCw size={18} />
              Refresh rates near budget
            </button>
          </section>

          <section className="command-panel readiness-board">
            <div className="tool-heading">
              <div>
                <span>Readiness</span>
                <h2>Before-booking checklist</h2>
              </div>
              <ClipboardCheck size={22} />
            </div>

            <div className="task-grid">
              {TASKS.map((task) => {
                const Icon = task.icon;
                const key = `${selectedTrip?.id}:${task.id}`;
                const done = Boolean(completedTasks[key]);
                return (
                  <button
                    className={done ? "task-chip done" : "task-chip"}
                    onClick={() => toggleTask(task.id)}
                    key={task.id}
                  >
                    {done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                    <Icon size={18} />
                    <span>{task.label}</span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="command-panel ai-command">
            <div className="tool-heading">
              <div>
                <span>AI command</span>
                <h2>Ask for any refinement</h2>
              </div>
              <Wand2 size={22} />
            </div>

            <div className="quick-commands">
              {QUICK_COMMANDS.slice(1).map((item) => (
                <button type="button" onClick={() => runCommand(item)} disabled={refining} key={item}>
                  <Target size={16} />
                  {item.includes("hotel") ? "Better stay value" : "Lower total cost"}
                </button>
              ))}
            </div>

            <textarea
              value={command}
              onChange={(event) => setCommand(event.target.value)}
              placeholder="Ask anything: cheaper transport rates, hotel under INR 4,000, slower days, better food, safer areas, fewer transfers..."
              rows={5}
            />

            <button className="panel-action" onClick={() => runCommand(command)} disabled={refining || !command.trim()}>
              {refining ? <RefreshCw size={18} /> : <Send size={18} />}
              {refining ? "Updating trip..." : "Send refinement"}
            </button>

            {message && <div className="command-message">{message}</div>}
          </section>

          <section className="command-panel trip-snapshot">
            <div className="snapshot-row">
              <CalendarDays size={20} />
              <span>{formatDate(selectedPlan.date_range?.start)} to {formatDate(selectedPlan.date_range?.end)}</span>
            </div>
            <div className="snapshot-row">
              <Route size={20} />
              <span>{selectedPlan.origin || "Origin"} to {selectedPlan.destination || "Destination"}</span>
            </div>
            <div className="snapshot-row">
              <Clock3 size={20} />
              <span>{selectedPlan.date_range?.total_days || selectedPlan.days?.length || 1} planned days</span>
            </div>
            <div className="snapshot-row">
              <IndianRupee size={20} />
              <span>{valueText(selectedPlan.budget_guardrails?.status, "Budget guardrails ready")}</span>
            </div>
          </section>
        </div>
      </section>
    </div>
  );
}
