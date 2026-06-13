import { createContext, createElement, useContext, useEffect, useMemo, useReducer, useState } from "react";
import { AnimatePresence, motion as Motion } from "framer-motion";
import {
  Bike,
  Bookmark,
  BusFront,
  CarFront,
  CheckCircle2,
  Clock3,
  CloudSun,
  Coffee,
  Compass,
  Copy,
  Download,
  Eye,
  Footprints,
  Gauge,
  Heart,
  IndianRupee,
  Instagram,
  Loader2,
  LocateFixed,
  MapPin,
  MapPinned,
  MessageCircle,
  Moon,
  Navigation,
  Route,
  Send,
  Share2,
  ShieldCheck,
  Shuffle,
  SlidersHorizontal,
  Sparkles,
  Sunrise,
  Timer,
  TrainFront,
  Umbrella,
  UsersRound,
  WalletCards,
  Wind,
  Zap,
} from "lucide-react";
import { apiUrl } from "../lib/api";
import "./NearbyPlanner.css";

const NearbyPlannerContext = createContext(null);

const DURATION_OPTIONS = ["2 Hours", "4 Hours", "Half Day", "Full Day", "Weekend", "2 Days", "Custom"];
const MOODS = [
  "Relax",
  "Adventure",
  "Food",
  "Romantic",
  "Nature",
  "Nightlife",
  "Shopping",
  "Photography",
  "Hidden Gems",
  "Luxury",
  "Spiritual",
  "Family",
  "Solo Recharge",
  "Rainy Day",
];
const TRANSPORT = [
  { label: "Car", Icon: CarFront },
  { label: "Bike", Icon: Bike },
  { label: "Metro", Icon: TrainFront },
  { label: "Walking", Icon: Footprints },
  { label: "Public Transport", Icon: BusFront },
];
const RADIUS_OPTIONS = ["Within 5 km", "Within 20 km", "1-hour drive", "3-hour drive"];
const GROUP_TYPES = ["Solo", "Couple", "Friends", "Family", "Office Team"];
const LOADING_STEPS = [
  "Finding hidden gems near you...",
  "Optimizing timing and traffic...",
  "Checking weather conditions...",
  "Scanning opening hours and crowd windows...",
  "Building your cinematic route...",
];
const initialState = {
  location: "",
  detectedCity: "Detecting nearby city",
  locationStatus: "Tap detect or type your city",
  coordinates: { lat: 12.9716, lng: 77.5946 },
  duration: "4 Hours",
  customDuration: "",
  moods: ["Food", "Hidden Gems"],
  budget: 1500,
  transport: "Car",
  radius: "Within 20 km",
  groupType: "Couple",
  surpriseMe: true,
};

function plannerReducer(state, action) {
  switch (action.type) {
    case "patch":
      return { ...state, ...action.payload };
    case "toggleMood": {
      const exists = state.moods.includes(action.payload);
      return {
        ...state,
        moods: exists
          ? state.moods.filter((mood) => mood !== action.payload)
          : [...state.moods, action.payload],
      };
    }
    default:
      return state;
  }
}

function usePlanner() {
  const context = useContext(NearbyPlannerContext);
  if (!context) throw new Error("usePlanner must be used inside NearbyPlannerContext");
  return context;
}

function budgetLabel(value) {
  if (value <= 700) return "INR 500 - street-smart";
  if (value <= 1800) return "INR 1,500 - easy local";
  if (value <= 3500) return "INR 3,000 - premium day";
  if (value <= 5000) return "INR 5,000 - elevated";
  return "INR 5,000+ - luxe";
}

function formatInr(value) {
  return `INR ${Number(value || 0).toLocaleString("en-IN")}`;
}

function tripName(form) {
  const mood = form.moods[form.moods.length - 1] || "Nearby";
  const group = form.groupType === "Solo" ? "Solo" : form.groupType;
  if (form.surpriseMe) return `${mood} Surprise Escape`;
  if (mood === group) return `${mood} Nearby Plan`;
  return `${group} ${mood} Nearby Plan`;
}

function signalValue(value, fallback = "Estimate") {
  if (value && typeof value === "object" && "value" in value) return value.value || fallback;
  return value || fallback;
}

function signalFor(plan, key) {
  return plan?.summary?.signals?.[key] || null;
}

function SignalBadge({ signal }) {
  if (!signal) return null;
  return (
    <small className={`source-badge ${signal.live ? "live" : "estimate"}`}>
      {signal.live ? "Live" : "Estimate"} - {signal.source} - {signal.confidence}
    </small>
  );
}

function PlannerProvider({ children }) {
  const [state, dispatch] = useReducer(plannerReducer, initialState);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <NearbyPlannerContext.Provider value={value}>{children}</NearbyPlannerContext.Provider>;
}

function OptionButton({ active, children, onClick, className = "" }) {
  return (
    <button type="button" className={`${className} ${active ? "active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

function LocationControl() {
  const { state, dispatch } = usePlanner();
  const [detecting, setDetecting] = useState(false);

  const detectLocation = () => {
    if (!navigator.geolocation) {
      dispatch({ type: "patch", payload: { locationStatus: "Geolocation is not available. Type your city." } });
      return;
    }

    setDetecting(true);
    dispatch({ type: "patch", payload: { locationStatus: "Finding your location..." } });

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const coordinates = {
          lat: Number(position.coords.latitude.toFixed(5)),
          lng: Number(position.coords.longitude.toFixed(5)),
        };
        let city = "Current location";

        try {
          const res = await fetch(
            `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${coordinates.lat}&longitude=${coordinates.lng}&localityLanguage=en`
          );
          const data = await res.json();
          city = data.city || data.locality || data.principalSubdivision || city;
        } catch {
          city = "Current location";
        }

        dispatch({
          type: "patch",
          payload: {
            coordinates,
            detectedCity: city,
            location: city,
            locationStatus: "Location detected",
          },
        });
        setDetecting(false);
      },
      () => {
        dispatch({
          type: "patch",
          payload: { locationStatus: "Location blocked. Type your city to continue." },
        });
        setDetecting(false);
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 120000 }
    );
  };

  return (
    <div className="nearby-field nearby-location-field">
      <label>
        <MapPin size={16} />
        Current location
      </label>
      <div className="location-input-row">
        <input
          value={state.location}
          onChange={(event) => dispatch({ type: "patch", payload: { location: event.target.value } })}
          placeholder="Search or type your city"
        />
        <button type="button" onClick={detectLocation}>
          {detecting ? <Loader2 size={17} className="spin" /> : <LocateFixed size={17} />}
          Detect
        </button>
      </div>
      <div className="detected-city">
        <CheckCircle2 size={15} />
        <span>{state.detectedCity}</span>
        <small>{state.locationStatus}</small>
      </div>
    </div>
  );
}

function InputPanel({ onGenerate, loading }) {
  const { state, dispatch } = usePlanner();

  return (
    <Motion.section
      className="nearby-input-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
    >
      <div className="nearby-title">
        <span className="eyebrow dark">
          <Sparkles size={16} />
          AI Nearby Planner
        </span>
        <h1>Instant Escape</h1>
        <p>Plan a nearby experience that fits your time, mood, budget, and route energy right now.</p>
      </div>

      <div className="nearby-form-grid">
        <LocationControl />

        <div className="nearby-field">
          <label>
            <Clock3 size={16} />
            Duration
          </label>
          <div className="nearby-segment-grid compact">
            {DURATION_OPTIONS.map((duration) => (
              <OptionButton
                active={state.duration === duration}
                onClick={() => dispatch({ type: "patch", payload: { duration } })}
                key={duration}
              >
                {duration}
              </OptionButton>
            ))}
          </div>
          {state.duration === "Custom" && (
            <input
              className="custom-duration"
              value={state.customDuration}
              onChange={(event) => dispatch({ type: "patch", payload: { customDuration: event.target.value } })}
              placeholder="Example: 90 mins, 6 hours"
            />
          )}
        </div>

        <div className="nearby-field wide">
          <label>
            <Heart size={16} />
            Mood and intent
          </label>
          <div className="mood-chip-grid">
            {MOODS.map((mood) => (
              <OptionButton
                active={state.moods.includes(mood)}
                onClick={() => dispatch({ type: "toggleMood", payload: mood })}
                className="mood-chip"
                key={mood}
              >
                {mood}
              </OptionButton>
            ))}
          </div>
        </div>

        <div className="nearby-field">
          <label>
            <IndianRupee size={16} />
            Budget
          </label>
          <div className="budget-readout">
            <strong>{formatInr(state.budget)}</strong>
            <span>{budgetLabel(state.budget)}</span>
          </div>
          <input
            type="range"
            min="500"
            max="6500"
            step="500"
            value={state.budget}
            onChange={(event) => dispatch({ type: "patch", payload: { budget: Number(event.target.value) } })}
          />
          <div className="budget-scale">
            <span>INR 500</span>
            <span>INR 1,500</span>
            <span>INR 3,000</span>
            <span>INR 5,000+</span>
          </div>
        </div>

        <div className="nearby-field">
          <label>
            <Navigation size={16} />
            Transport mode
          </label>
          <div className="nearby-segment-grid">
            {TRANSPORT.map(({ label, Icon }) => (
              <OptionButton
                active={state.transport === label}
                onClick={() => dispatch({ type: "patch", payload: { transport: label } })}
                key={label}
              >
                {createElement(Icon, { size: 16 })}
                {label}
              </OptionButton>
            ))}
          </div>
        </div>

        <div className="nearby-field">
          <label>
            <Route size={16} />
            Travel radius
          </label>
          <div className="nearby-segment-grid compact">
            {RADIUS_OPTIONS.map((radius) => (
              <OptionButton
                active={state.radius === radius}
                onClick={() => dispatch({ type: "patch", payload: { radius } })}
                key={radius}
              >
                {radius}
              </OptionButton>
            ))}
          </div>
        </div>

        <div className="nearby-field">
          <label>
            <UsersRound size={16} />
            Group type
          </label>
          <div className="nearby-segment-grid compact">
            {GROUP_TYPES.map((groupType) => (
              <OptionButton
                active={state.groupType === groupType}
                onClick={() => dispatch({ type: "patch", payload: { groupType } })}
                key={groupType}
              >
                {groupType}
              </OptionButton>
            ))}
          </div>
        </div>

        <div className="nearby-surprise-card">
          <div>
            <span>
              <Shuffle size={16} />
              Surprise me
            </span>
            <p>Prioritize hidden gems, unique timing, and emotionally tuned picks.</p>
          </div>
          <button
            type="button"
            className={state.surpriseMe ? "toggle active" : "toggle"}
            onClick={() => dispatch({ type: "patch", payload: { surpriseMe: !state.surpriseMe } })}
            aria-label="Toggle surprise me"
          >
            <span></span>
          </button>
        </div>
      </div>

      <Motion.button
        type="button"
        className="escape-cta"
        onClick={onGenerate}
        disabled={loading}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        {loading ? <Loader2 size={21} className="spin" /> : <Sparkles size={21} />}
        {loading ? "Generating Escape..." : "Generate My Escape"}
      </Motion.button>
    </Motion.section>
  );
}

function LoadingExperience({ stepIndex }) {
  return (
    <Motion.section
      className="nearby-loading"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
    >
      <div className="route-loader">
        <div className="route-orbit">
          <Sparkles size={28} />
        </div>
        <div className="route-line animated"></div>
        <div className="route-pin pin-a"></div>
        <div className="route-pin pin-b"></div>
        <div className="route-pin pin-c"></div>
      </div>
      <div className="loading-copy">
        <span>AI route engine</span>
        <AnimatePresence mode="wait">
          <Motion.h2
            key={LOADING_STEPS[stepIndex]}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            {LOADING_STEPS[stepIndex]}
          </Motion.h2>
        </AnimatePresence>
        <div className="progress-cards">
          {[0, 1, 2].map((item) => (
            <Motion.div
              key={item}
              initial={{ opacity: 0.3 }}
              animate={{ opacity: [0.35, 1, 0.35] }}
              transition={{ duration: 1.6, repeat: Infinity, delay: item * 0.22 }}
            />
          ))}
        </div>
      </div>
    </Motion.section>
  );
}

function RouteMap({ plan, preview = false }) {
  const points = preview
    ? [
        { title: "You", coordinates: { lat: 12.9716, lng: 77.5946 } },
        { title: "Cafe", coordinates: { lat: 12.983, lng: 77.607 } },
        { title: "View", coordinates: { lat: 12.991, lng: 77.616 } },
      ]
    : plan.stops;
  const realPoints = points.filter((point) => point.coordinates);
  const lats = realPoints.map((point) => Number(point.coordinates.lat));
  const lngs = realPoints.map((point) => Number(point.coordinates.lng));
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const positionFor = (point, index) => {
    if (!point.coordinates || !Number.isFinite(minLat) || minLat === maxLat || minLng === maxLng) {
      return {
        left: `${18 + index * (64 / Math.max(points.length - 1, 1))}%`,
        top: `${preview ? 62 - index * 14 : 66 - (index % 3) * 17}%`,
      };
    }
    const lngRatio = (Number(point.coordinates.lng) - minLng) / (maxLng - minLng || 1);
    const latRatio = (Number(point.coordinates.lat) - minLat) / (maxLat - minLat || 1);
    return {
      left: `${14 + lngRatio * 72}%`,
      top: `${74 - latRatio * 50}%`,
    };
  };

  return (
    <div className="smart-map">
      <div className="map-grid"></div>
      <div className="map-route-line"></div>
      {points.map((point, index) => (
        <div
          className={`map-stop stop-${index + 1}`}
          style={positionFor(point, index)}
          key={`${point.title}-${index}`}
        >
          <span>{index + 1}</span>
          <small>{point.title}</small>
        </div>
      ))}
      <div className="map-chip top">
        <Gauge size={15} />
        {preview ? "Traffic-aware preview" : plan.route.traffic_awareness}
      </div>
      <div className="map-chip bottom">
        <MapPinned size={15} />
        {preview ? "Optimized route order" : `${plan.route.estimated_commute_time} - ${plan.route.optimized_order?.length || 0} real stops`}
      </div>
    </div>
  );
}

function PreviewPanel() {
  const { state } = usePlanner();
  return (
    <Motion.aside
      className="nearby-preview-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: 0.08 }}
    >
      <div className="preview-card">
        <span>
          <Compass size={16} />
          Current escape profile
        </span>
        <h2>{tripName(state)}</h2>
        <div className="preview-stats">
          <div>
            <Clock3 size={17} />
            <strong>{state.duration === "Custom" ? state.customDuration || "Custom" : state.duration}</strong>
            <small>Duration</small>
          </div>
          <div>
            <WalletCards size={17} />
            <strong>{formatInr(state.budget)}</strong>
            <small>Budget</small>
          </div>
          <div>
            <Route size={17} />
            <strong>{state.radius}</strong>
            <small>Radius</small>
          </div>
        </div>
      </div>
      <RouteMap preview />
      <div className="signal-stack">
        <div>
          <CloudSun size={18} />
          <span>Weather-aware route</span>
        </div>
        <div>
          <Eye size={18} />
          <span>Low-crowd windows</span>
        </div>
        <div>
          <Sunrise size={18} />
          <span>Golden-hour timing</span>
        </div>
      </div>
    </Motion.aside>
  );
}

function SummaryCard({ plan }) {
  const metrics = [
    ["Total duration", plan.summary.total_duration, Timer, null],
    ["Budget", plan.summary.estimated_budget, IndianRupee, signalFor(plan, "estimated_budget")],
    ["Distance", plan.summary.total_travel_distance, Route, signalFor(plan, "total_travel_distance")],
    ["Weather", plan.summary.weather_snapshot, CloudSun, signalFor(plan, "weather_snapshot")],
    ["Best leave", plan.summary.best_time_to_leave, Clock3, signalFor(plan, "best_time_to_leave")],
  ];

  return (
    <Motion.section className="nearby-summary" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
      <div>
        <span className="eyebrow dark">
          <Zap size={16} />
          Your escape is ready
        </span>
        <h2>{plan.summary.title}</h2>
        <p>{plan.summary.magic_touch}</p>
        <div className="summary-tags">
          {plan.summary.vibe_tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      </div>
      <div className="summary-metrics">
        {metrics.map(([label, value, Icon, signal]) => (
          <div key={label}>
            {createElement(Icon, { size: 18 })}
            <span>{label}</span>
            <strong>{signalValue(value)}</strong>
            <SignalBadge signal={signal} />
          </div>
        ))}
      </div>
    </Motion.section>
  );
}

function StopTimeline({ plan }) {
  return (
    <section className="timeline-output">
      <div className="output-heading">
        <div>
          <span>Interactive timeline</span>
          <h2>Stops, timing, and AI reasons</h2>
        </div>
        <Route size={24} />
      </div>

      <div className="timeline-list">
        {plan.stops.map((stop, index) => (
          <Motion.article
            className="stop-card"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            key={stop.id}
          >
            <div className="stop-index">{String(index + 1).padStart(2, "0")}</div>
            <div className="stop-body">
              <div className="stop-title-row">
                <div>
                  <span>{stop.eta}</span>
                  <h3>{stop.title}</h3>
                </div>
                <strong>{stop.estimated_cost}</strong>
              </div>
              <p>{stop.description}</p>
              <div className="stop-meta-grid">
                <span>
                  <Timer size={15} />
                  {stop.ideal_visit_duration}
                </span>
                <span>
                  <Navigation size={15} />
                  {stop.travel_time_to_next}
                </span>
                <span>
                  <UsersRound size={15} />
                  {stop.crowd_level}
                </span>
                <span>
                  <Umbrella size={15} />
                  {stop.weather_suitability}
                </span>
              </div>
              <div className="why-picked">
                <Sparkles size={17} />
                <span>{stop.why_ai_picked_this}</span>
              </div>
              <div className="source-row">
                <SignalBadge signal={stop.signals?.coordinates} />
                <SignalBadge signal={stop.signals?.opening_hours} />
                <SignalBadge signal={stop.signals?.estimated_cost} />
              </div>
              {stop.score_breakdown && (
                <div className="score-panel">
                  <strong>Score {stop.score_breakdown.total}/100</strong>
                  {[
                    ["Mood", stop.score_breakdown.mood_match],
                    ["Distance", stop.score_breakdown.distance_score],
                    ["Budget", stop.score_breakdown.budget_fit],
                    ["Rating", stop.score_breakdown.rating_score],
                    ["Weather", stop.score_breakdown.weather_fit],
                    ["Hours", stop.score_breakdown.opening_hours_fit],
                  ].map(([label, value]) => (
                    <span key={label}>{label}: {value}</span>
                  ))}
                </div>
              )}
            </div>
          </Motion.article>
        ))}
      </div>
    </section>
  );
}

function BudgetBreakdown({ plan }) {
  const items = [
    ["Food", plan.costs.food, Coffee],
    ["Transport", plan.costs.transport, Navigation],
    ["Tickets", plan.costs.tickets, ShieldCheck],
    ["Shopping", plan.costs.shopping, Bookmark],
    ["Buffer", plan.costs.buffer, WalletCards],
  ];

  return (
    <section className="budget-panel">
      <div className="output-heading compact">
        <div>
          <span>Budget breakdown</span>
          <h2>{plan.costs.total}</h2>
        </div>
        <IndianRupee size={23} />
      </div>
      <div className="budget-bars">
        {items.map(([label, value, Icon], index) => (
          <div className="budget-row" key={label}>
            <div>
              {createElement(Icon, { size: 17 })}
              <span>{label}</span>
            </div>
            <strong>{value}</strong>
            <i style={{ width: `${34 + index * 11}%` }}></i>
          </div>
        ))}
      </div>
    </section>
  );
}

function InsightsPanel({ plan }) {
  const signalCards = [
    ["Weather", plan.summary.weather_snapshot, CloudSun, plan.summary.signals?.weather_snapshot],
    ["Traffic", plan.timing.traffic_note, Gauge, plan.timing.signals?.traffic_note],
    ["Opening hours", "Shown per stop from Maps when returned", Clock3, null],
    ["AQI", "Estimate; no live AQI source configured", Wind, { live: false, source: "Deterministic estimate", confidence: "medium" }],
    ["Nightlife", plan.timing.nightlife_window, Moon, null],
    ["Rain fallback", plan.timing.rainy_day_cutover, Umbrella, plan.timing.signals?.rainy_day_cutover],
  ];

  return (
    <section className="insights-panel">
      <div className="output-heading compact">
        <div>
          <span>AI insights</span>
          <h2>Smart signals</h2>
        </div>
        <Sparkles size={23} />
      </div>

      <div className="signal-grid">
        {signalCards.map(([label, value, Icon, signal]) => (
          <div className="signal-card" key={label}>
            {createElement(Icon, { size: 18 })}
            <span>{label}</span>
            <strong>{value}</strong>
            <SignalBadge signal={signal} />
          </div>
        ))}
      </div>

      <div className="insight-list">
        {plan.insights.map((insight) => (
          <div key={insight}>
            <CheckCircle2 size={17} />
            <span>{insight}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function AlternatePlans({ plan, onSwitch }) {
  return (
    <section className="alternate-panel">
      <div className="output-heading">
        <div>
          <span>Alternate plans</span>
          <h2>Switch the vibe instantly</h2>
        </div>
        <SlidersHorizontal size={24} />
      </div>
      <div className="alternate-grid">
        {plan.alternates.map((alternate) => (
          <button className="alternate-card" key={alternate.id} type="button" onClick={() => onSwitch(alternate)}>
            <div>
              <h3>{alternate.title}</h3>
              <strong>{alternate.budget}</strong>
            </div>
            <p>{alternate.description}</p>
            <div>
              {alternate.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function SocialActions({ plan }) {
  const [message, setMessage] = useState("");

  const copyText = async (text, label) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage(`${label} copied`);
    } catch {
      setMessage(`${label} ready`);
    }
  };

  const sharePlan = async () => {
    const text = `${plan.summary.title}: ${plan.stops.map((stop) => stop.title).join(" -> ")}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: plan.summary.title, text });
        setMessage("Share sheet opened");
        return;
      } catch {
        setMessage("Share cancelled");
        return;
      }
    }
    copyText(text, "Share summary");
  };

  const savePlan = () => {
    const saved = JSON.parse(localStorage.getItem("travelai-nearby-plans") || "[]");
    localStorage.setItem("travelai-nearby-plans", JSON.stringify([{ ...plan, saved_at: new Date().toISOString() }, ...saved]));
    setMessage("Plan saved");
  };

  const duplicatePlan = () => {
    const duplicate = { ...plan, summary: { ...plan.summary, title: `${plan.summary.title} Copy` } };
    const saved = JSON.parse(localStorage.getItem("travelai-nearby-plans") || "[]");
    localStorage.setItem("travelai-nearby-plans", JSON.stringify([duplicate, ...saved]));
    setMessage("Plan duplicated");
  };

  return (
    <section className="social-panel">
      <div className="action-grid">
        <button type="button" onClick={sharePlan}>
          <Share2 size={18} />
          Share itinerary
        </button>
        <button type="button" onClick={() => window.print()}>
          <Download size={18} />
          Export PDF
        </button>
        <button type="button" onClick={() => copyText(JSON.stringify(plan, null, 2), "Story JSON")}>
          <Instagram size={18} />
          Story cards
        </button>
        <button type="button" onClick={savePlan}>
          <Bookmark size={18} />
          Save plan
        </button>
        <button type="button" onClick={duplicatePlan}>
          <Copy size={18} />
          Duplicate
        </button>
        <button type="button" onClick={() => copyText(plan.summary.magic_touch, "Friend note")}>
          <Send size={18} />
          Send to friends
        </button>
      </div>
      {message && (
        <Motion.div className="action-message" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <MessageCircle size={16} />
          {message}
        </Motion.div>
      )}
    </section>
  );
}

function JsonSchemaPanel({ plan }) {
  return (
    <section className="json-panel">
      <div className="output-heading compact">
        <div>
          <span>AI response format</span>
          <h2>Structured itinerary JSON</h2>
        </div>
        <Copy size={22} />
      </div>
      <pre>{JSON.stringify(plan, null, 2)}</pre>
    </section>
  );
}

function OutputSection({ plan, onAlternate }) {
  return (
    <div className="nearby-output">
      <SummaryCard plan={plan} />
      {plan.diagnostics && (
        <section className="diagnostics-panel">
          <strong>{plan.diagnostics.source}</strong>
          <span>Maps calls: {plan.diagnostics.maps_calls}</span>
          <span>Groq calls: {plan.diagnostics.groq_calls}</span>
          {plan.diagnostics.cache_hit && <span>Explanation cache hit</span>}
          {plan.diagnostics.warnings?.map((warning) => <small key={warning}>{warning}</small>)}
        </section>
      )}
      <div className="output-layout">
        <div>
          <StopTimeline plan={plan} />
          <AlternatePlans plan={plan} onSwitch={onAlternate} />
          <JsonSchemaPanel plan={plan} />
        </div>
        <aside>
          <RouteMap plan={plan} />
          <BudgetBreakdown plan={plan} />
          <InsightsPanel plan={plan} />
          <SocialActions plan={plan} />
        </aside>
      </div>
    </div>
  );
}

function NearbyPlannerInner() {
  const { state } = usePlanner();
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading) return undefined;
    const interval = window.setInterval(() => {
      setLoadingStep((current) => (current + 1) % LOADING_STEPS.length);
    }, 850);
    return () => window.clearInterval(interval);
  }, [loading]);

  const generatePlan = async (patch = {}) => {
    const nextState = {
      ...state,
      ...patch,
      moods: patch.moods || state.moods,
      budget: patch.budget || state.budget,
      duration: patch.duration || state.duration,
      radius: patch.radius || state.radius,
    };
    setLoading(true);
    setPlan(null);
    setError("");
    setLoadingStep(0);
    const payload = {
      location: nextState.location || nextState.detectedCity,
      detected_city: nextState.detectedCity,
      coordinates: nextState.coordinates,
      duration: nextState.duration === "Custom" ? nextState.customDuration || "Custom" : nextState.duration,
      moods: nextState.moods,
      budget: nextState.budget,
      transport: nextState.transport,
      radius: nextState.radius,
      group_type: nextState.groupType,
      surprise_me: nextState.surpriseMe,
    };

    try {
      const res = await fetch(apiUrl("/nearby/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "Nearby planner API failed");
      }
      const apiPlan = await res.json();
      window.setTimeout(() => {
        setPlan(apiPlan);
        setLoading(false);
      }, 1800);
    } catch (err) {
      window.setTimeout(() => {
        setError(err.message || "Nearby planner API failed. No local fake plan was shown.");
        setLoading(false);
      }, 1800);
    }
  };

  return (
    <div className="nearby-page page-wrap">
      <div className="nearby-hero-grid">
        <InputPanel onGenerate={generatePlan} loading={loading} />
        <PreviewPanel />
      </div>

      <AnimatePresence>{loading && <LoadingExperience stepIndex={loadingStep} />}</AnimatePresence>

      {error && !loading && (
        <section className="nearby-error">
          <strong>Could not generate a verified nearby plan.</strong>
          <span>{error}</span>
          <small>Configure `GOOGLE_MAPS_API_KEY` or `SERPAPI_KEY` for real nearby place search. Groq is only used for short explanations.</small>
        </section>
      )}

      <AnimatePresence>{plan && !loading && <OutputSection plan={plan} onAlternate={(alternate) => generatePlan(alternate.request_patch || {})} />}</AnimatePresence>
    </div>
  );
}

export default function NearbyPlanner() {
  return (
    <PlannerProvider>
      <NearbyPlannerInner />
    </PlannerProvider>
  );
}
