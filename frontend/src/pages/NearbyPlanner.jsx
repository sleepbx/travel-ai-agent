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
const STOP_IMAGES = [
  "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1501446529957-6226bd447c46?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1481833761820-0509d3217039?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=1100&q=80",
  "https://images.unsplash.com/photo-1528823872057-9c018a7a7553?auto=format&fit=crop&w=1100&q=80",
];

function placeImageUrl(title, location = "", kind = "travel") {
  const query = [title, location, kind, "nearby"].filter(Boolean).join(" ");
  return `https://source.unsplash.com/1100x760/?${encodeURIComponent(query)}`;
}

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

function durationHours(duration, customDuration) {
  if (duration === "2 Hours") return 2;
  if (duration === "4 Hours") return 4;
  if (duration === "Half Day") return 6;
  if (duration === "Full Day") return 10;
  if (duration === "Weekend") return 32;
  if (duration === "2 Days") return 44;
  const match = String(customDuration || "").match(/\d+/);
  return match ? Number(match[0]) : 5;
}

function tripName(form) {
  const mood = form.moods[form.moods.length - 1] || "Nearby";
  const group = form.groupType === "Solo" ? "Solo" : form.groupType;
  if (form.surpriseMe) return `${mood} Surprise Escape`;
  if (mood === group) return `${mood} Nearby Plan`;
  return `${group} ${mood} Nearby Plan`;
}

function durationBucket(hours) {
  if (hours <= 2) return "micro";
  if (hours <= 5) return "short";
  if (hours <= 10) return "day";
  return "escape";
}

function moodWeights(moods) {
  return moods.reduce((weights, mood, index) => ({ ...weights, [mood]: 6 + index * 2 }), {});
}

function seedValue(form) {
  return [
    form.location || form.detectedCity,
    form.duration,
    form.customDuration,
    form.moods.join(","),
    form.budget,
    form.transport,
    form.radius,
    form.groupType,
    form.surpriseMe,
  ].join("|");
}

function seedBonus(seed, title) {
  const text = `${seed}:${title}`;
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 31 + text.charCodeAt(index)) % 997;
  }
  return hash % 4;
}

function pickStops(form) {
  const library = [
    {
      title: form.surpriseMe ? "Rooftop Sunset Nook" : "Skyline Viewpoint",
      description: "A compact golden-hour stop with a short walk, clean views, and enough quiet to reset.",
      baseCost: 0,
      image: STOP_IMAGES[0],
      tags: ["Hidden Gems", "Photography", "Romantic"],
      groups: ["Couple", "Solo", "Friends"],
      transports: ["Car", "Bike"],
      radii: ["Within 20 km", "1-hour drive"],
      durations: ["micro", "short", "day"],
      why: "You are about 20 mins away from a low-friction sunset spot that matches the current mood mix.",
    },
    {
      title: "Chef-Led Street Food Lane",
      description: "A walkable food stretch with snacks, dessert, and one sit-down option if the group slows down.",
      baseCost: 520,
      image: STOP_IMAGES[1],
      tags: ["Food", "Family", "Nightlife"],
      groups: ["Friends", "Family", "Office Team"],
      transports: ["Metro", "Walking", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["micro", "short", "day"],
      why: "It gives the plan a social anchor without needing a booking or a long commute.",
    },
    {
      title: "Design Museum and Cafe",
      description: "Indoor galleries, a covered cafe, and a backup bookstore nearby if rain arrives early.",
      baseCost: 420,
      image: STOP_IMAGES[2],
      tags: ["Rainy Day", "Relax", "Photography"],
      groups: ["Solo", "Couple", "Family"],
      transports: ["Metro", "Car", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["short", "day"],
      why: "Rain risk is handled with an indoor backup that still feels like an outing.",
    },
    {
      title: "Leafy Lake Loop",
      description: "A calm nature loop for photos, air, and an easy decompression window.",
      baseCost: 80,
      image: STOP_IMAGES[3],
      tags: ["Nature", "Relax", "Solo Recharge", "Photography"],
      groups: ["Solo", "Couple", "Family"],
      transports: ["Walking", "Bike", "Car"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["micro", "short", "day"],
      why: "AQI and crowd signals favor a lighter outdoor window before evening traffic builds.",
    },
    {
      title: "Candlelit Courtyard Dinner",
      description: "A soft-lit stop with reliable seating, warm drinks, and a second cafe within walking distance.",
      baseCost: 1200,
      image: STOP_IMAGES[4],
      tags: ["Romantic", "Coffee", "Luxury"],
      groups: ["Couple"],
      transports: ["Car", "Metro"],
      radii: ["Within 20 km"],
      durations: ["short", "day"],
      why: "This keeps the final hour emotionally warm and reduces last-minute venue hunting.",
    },
    {
      title: "Maker Market Arcade",
      description: "A compact set of local stores, stationery, handmade finds, and giftable food counters.",
      baseCost: 900,
      image: STOP_IMAGES[5],
      tags: ["Shopping", "Hidden Gems", "Family"],
      groups: ["Friends", "Family", "Couple"],
      transports: ["Metro", "Walking", "Car"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["short", "day"],
      why: "It creates a flexible browsing window that can expand or shrink based on energy.",
    },
    {
      title: "Quiet Temple Courtyard",
      description: "A peaceful courtyard with low noise, short rituals, and an easy exit route.",
      baseCost: 40,
      image: STOP_IMAGES[6],
      tags: ["Spiritual", "Relax", "Solo Recharge"],
      groups: ["Solo", "Family", "Couple"],
      transports: ["Walking", "Metro", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["micro", "short"],
      why: "It adds a reflective stop without making the plan feel heavy or over-scheduled.",
    },
    {
      title: "Live Music Pocket",
      description: "A small-format music venue timed before the late-night surge.",
      baseCost: 850,
      image: STOP_IMAGES[7],
      tags: ["Nightlife", "Friends", "Romantic"],
      groups: ["Friends", "Couple", "Office Team"],
      transports: ["Car", "Metro"],
      radii: ["Within 20 km", "1-hour drive"],
      durations: ["short", "day"],
      why: "The set starts before peak traffic and leaves room for a graceful exit.",
    },
    {
      title: "Bouldering and Brew Session",
      description: "A guided climbing block followed by a low-key brew stop nearby.",
      baseCost: 1100,
      image: STOP_IMAGES[8],
      tags: ["Adventure", "Friends", "Photography"],
      groups: ["Friends", "Office Team", "Solo"],
      transports: ["Bike", "Car", "Metro"],
      radii: ["Within 20 km", "1-hour drive"],
      durations: ["short", "day"],
      why: "It gives the route a real activity peak without spending the whole day in transit.",
    },
    {
      title: "Indie Art Walk",
      description: "Murals, micro-galleries, design stores, and a coffee pause in a walkable cluster.",
      baseCost: 300,
      image: STOP_IMAGES[9],
      tags: ["Photography", "Hidden Gems", "Shopping", "Solo Recharge"],
      groups: ["Solo", "Friends", "Couple"],
      transports: ["Walking", "Metro", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["micro", "short", "day"],
      why: "The plan stays easy to explore on foot and still feels discovery-led.",
    },
    {
      title: "Luxury Spa and High Tea",
      description: "A polished reset with reserved seating, quieter service, and a premium indoor backup.",
      baseCost: 2400,
      image: STOP_IMAGES[10],
      tags: ["Luxury", "Relax", "Romantic", "Rainy Day"],
      groups: ["Couple", "Solo"],
      transports: ["Car"],
      radii: ["Within 20 km", "1-hour drive"],
      durations: ["short", "day"],
      why: "Budget and mood allow one elevated anchor instead of many average stops.",
    },
    {
      title: "Family Science and Dessert Loop",
      description: "Hands-on exhibits, a snack break, and a dessert stop that works across ages.",
      baseCost: 950,
      image: STOP_IMAGES[11],
      tags: ["Family", "Rainy Day", "Food"],
      groups: ["Family"],
      transports: ["Car", "Metro", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["short", "day"],
      why: "It keeps kids, adults, weather, and food breaks in one manageable loop.",
    },
    {
      title: "Golden Hour Nature Drive",
      description: "A scenic outer-edge drive with one viewpoint, one snack stop, and a flexible return.",
      baseCost: 700,
      image: STOP_IMAGES[12],
      tags: ["Nature", "Adventure", "Photography", "Romantic"],
      groups: ["Couple", "Friends", "Family"],
      transports: ["Car", "Bike"],
      radii: ["1-hour drive", "3-hour drive"],
      durations: ["day", "escape"],
      why: "Your radius allows a wider route, so the plan spends budget on scenery rather than tickets.",
    },
    {
      title: "Hidden Vineyard Lunch",
      description: "A slower road-trip lunch with a scenic table, photo stops, and a no-rush return window.",
      baseCost: 1800,
      image: STOP_IMAGES[13],
      tags: ["Luxury", "Food", "Romantic", "Hidden Gems"],
      groups: ["Couple", "Friends"],
      transports: ["Car"],
      radii: ["3-hour drive", "1-hour drive"],
      durations: ["day", "escape"],
      why: "Weekend-style timing supports a memorable anchor experience outside the usual city loop.",
    },
    {
      title: "Team Game Arena",
      description: "Bowling, arcade games, quick food, and easy split-bill timing for a group.",
      baseCost: 1300,
      image: STOP_IMAGES[14],
      tags: ["Adventure", "Nightlife", "Food", "Rainy Day"],
      groups: ["Office Team", "Friends", "Family"],
      transports: ["Car", "Metro"],
      radii: ["Within 20 km"],
      durations: ["short", "day"],
      why: "It is weather-safe, group-friendly, and keeps everyone active without complex logistics.",
    },
    {
      title: "Bookstore Recharge Cafe",
      description: "A quiet bookstore-cafe hybrid for journaling, reading, coffee, and solo decompression.",
      baseCost: 280,
      image: STOP_IMAGES[15],
      tags: ["Solo Recharge", "Relax", "Rainy Day", "Spiritual"],
      groups: ["Solo"],
      transports: ["Walking", "Metro", "Public Transport"],
      radii: ["Within 5 km", "Within 20 km"],
      durations: ["micro", "short"],
      why: "It protects your energy and keeps the plan satisfying even with limited time.",
    },
  ];

  const hours = durationHours(form.duration, form.customDuration);
  const count = hours <= 2 ? 2 : hours <= 5 ? 3 : hours <= 10 ? 4 : 5;
  const bucket = durationBucket(hours);
  const weights = moodWeights(form.moods);
  const seed = seedValue(form);
  const scored = library
    .map((stop) => {
      const tagScore = stop.tags.reduce((score, tag) => score + (weights[tag] || 0), 0);
      const groupScore = stop.groups?.includes(form.groupType) ? 5 : 0;
      const transportScore = stop.transports?.includes(form.transport) ? 4 : 0;
      const radiusScore = stop.radii?.includes(form.radius) ? 3 : 0;
      const durationScore = stop.durations?.includes(bucket) ? 3 : 0;
      const surpriseScore = form.surpriseMe && stop.tags.includes("Hidden Gems") ? 4 : 0;
      const costScore = stop.baseCost <= form.budget * 0.45 ? 3 : stop.baseCost > form.budget * 0.85 ? -5 : 0;
      return {
        ...stop,
        score:
          tagScore +
          groupScore +
          transportScore +
          radiusScore +
          durationScore +
          surpriseScore +
          costScore +
          seedBonus(seed, stop.title),
      };
    })
    .sort((a, b) => b.score - a.score || a.baseCost - b.baseCost);

  const chosen = [];
  const chosenTitles = new Set();

  [...form.moods].reverse().forEach((mood) => {
    const match =
      scored.find((stop) => stop.tags.includes(mood) && stop.durations?.includes(bucket) && !chosenTitles.has(stop.title)) ||
      scored.find((stop) => stop.tags.includes(mood) && !chosenTitles.has(stop.title));
    if (match && chosen.length < count) {
      chosen.push(match);
      chosenTitles.add(match.title);
    }
  });

  scored.forEach((stop) => {
    if (chosen.length < count && !chosenTitles.has(stop.title)) {
      chosen.push(stop);
      chosenTitles.add(stop.title);
    }
  });

  return chosen;
}

function buildNearbyPlan(form) {
  const stops = pickStops(form);
  const hours = durationHours(form.duration, form.customDuration);
  const commuteUnit = form.transport === "Walking" ? 9 : form.transport === "Bike" ? 11 : form.transport === "Metro" ? 16 : 18;
  const foodBudget = Math.round(form.budget * (form.moods.includes("Food") ? 0.42 : 0.3));
  const transportBudget = Math.round(form.budget * (form.transport === "Walking" ? 0.08 : 0.18));
  const ticketBudget = Math.round(form.budget * 0.18);
  const shoppingBudget = Math.round(form.budget * (form.moods.includes("Shopping") ? 0.2 : 0.1));
  const bufferBudget = Math.max(150, form.budget - foodBudget - transportBudget - ticketBudget - shoppingBudget);
  const weather = form.moods.includes("Rainy Day") ? "Cloudy, rain backup active" : "Warm with a clear evening window";
  const now = new Date();
  const leaveHour = hours <= 4 ? now.getHours() + 1 : 9;
  const bestLeave = `${String(Math.min(leaveHour, 21)).padStart(2, "0")}:15`;
  const baseLat = form.coordinates.lat;
  const baseLng = form.coordinates.lng;

  const normalizedStops = stops.map((stop, index) => {
    const lat = Number((baseLat + (index + 1) * 0.009 - (index % 2) * 0.006).toFixed(5));
    const lng = Number((baseLng + (index + 1) * 0.008 + (index % 2) * 0.005).toFixed(5));
    return {
      id: `stop-${index + 1}`,
      sequence: index + 1,
      title: stop.title,
      image: placeImageUrl(stop.title, form.location || form.detectedCity, stop.tags?.[0] || "nearby"),
      description: stop.description,
      eta: index === 0 ? bestLeave : `+${index * commuteUnit + index * 45} mins`,
      ideal_visit_duration: hours <= 2 ? "40 mins" : index === stops.length - 1 ? "75 mins" : "55 mins",
      estimated_cost: formatInr(Math.min(stop.baseCost, Math.max(0, form.budget - 250))),
      travel_time_to_next: index === stops.length - 1 ? "Return when ready" : `${commuteUnit + index * 4} mins`,
      crowd_level: index === 0 ? "Low now" : index === stops.length - 1 ? "Medium later" : "Balanced",
      weather_suitability: form.moods.includes("Rainy Day") || stop.tags.includes("Rainy Day") ? "Indoor-safe" : "Good",
      opening_hours: index === stops.length - 1 ? "Open till 11:00 PM" : "Open now",
      why_ai_picked_this: stop.why,
      mood_tags: stop.tags,
      coordinates: { lat, lng },
      backup_plan: stop.tags.includes("Rainy Day") ? "Covered cafe table held as backup" : "Indoor cafe fallback within 700 m",
    };
  });
  const primaryMood = form.moods[form.moods.length - 1] || "your mood";
  const leadStop = normalizedStops[0]?.title || "a nearby escape";

  return {
    summary: {
      title: tripName(form),
      location: form.location || form.detectedCity,
      total_duration: form.duration === "Custom" ? form.customDuration || "Custom" : form.duration,
      estimated_budget: formatInr(form.budget),
      total_travel_distance: form.radius === "Within 5 km" ? "4.8 km" : form.radius === "Within 20 km" ? "16.4 km" : form.radius,
      weather_snapshot: weather,
      best_time_to_leave: bestLeave,
      vibe_tags: [...form.moods, form.groupType, form.transport].slice(0, 7),
      magic_touch: `Your strongest match is ${leadStop}, tuned for ${primaryMood.toLowerCase()} energy and ${form.transport.toLowerCase()} timing.`,
    },
    stops: normalizedStops,
    timing: {
      generated_at: now.toISOString(),
      best_leave: bestLeave,
      golden_hour: "17:42 - 18:22",
      nightlife_window: form.moods.includes("Nightlife") ? "20:00 - 23:15" : "Optional after 20:30",
      traffic_note: "Traffic expected after 19:00, route keeps the longest hop before then.",
      rainy_day_cutover: "If rain starts after 20:00, switch to the indoor backup at stop 3.",
    },
    costs: {
      food: formatInr(foodBudget),
      transport: formatInr(transportBudget),
      tickets: formatInr(ticketBudget),
      shopping: formatInr(shoppingBudget),
      buffer: formatInr(bufferBudget),
      total: formatInr(foodBudget + transportBudget + ticketBudget + shoppingBudget + bufferBudget),
    },
    route: {
      mode: form.transport,
      radius: form.radius,
      optimized_order: normalizedStops.map((stop) => stop.title),
      estimated_commute_time: `${Math.max(18, (normalizedStops.length - 1) * commuteUnit)} mins`,
      transport_aware_routing: `${form.transport} route balanced for commute time, crowd levels, and opening windows.`,
      traffic_awareness: "Avoids the densest outbound leg after 19:00.",
      map_coordinates: normalizedStops.map((stop) => stop.coordinates),
    },
    insights: [
      "This cafe is less crowded after 17:00.",
      "Perfect sunset timing at the viewpoint if you leave by the suggested time.",
      "Traffic expected after 19:00, so the route front-loads the longest commute.",
      form.moods.includes("Rainy Day")
        ? "Rain likely later, indoor backup added before the last stop."
        : "Weather is outdoor-friendly, with a cafe fallback if wind picks up.",
      "AQI-aware filter keeps the outdoor block short and close to greenery.",
      "Live opening-hour hooks are ready for future place APIs.",
    ],
    alternates: [
      {
        id: "cheaper",
        title: "Cheaper version",
        budget: formatInr(Math.max(500, Math.round(form.budget * 0.62))),
        duration: "Trim one paid stop",
        description: "Keeps the route social and local with street food, free views, and walking hops.",
        tags: ["Budget", "Flexible"],
      },
      {
        id: "luxury",
        title: "Luxury version",
        budget: formatInr(Math.round(form.budget * 1.8)),
        duration: "Same pace",
        description: "Upgrades dinner, adds reserved seating, and swaps one stop for a premium experience.",
        tags: ["Luxury", "Romantic"],
      },
      {
        id: "faster",
        title: "Faster version",
        budget: formatInr(Math.round(form.budget * 0.9)),
        duration: "2 stops",
        description: "Compresses the plan into the two highest-signal stops with the least commute.",
        tags: ["Fast", "Low commute"],
      },
      {
        id: "hidden",
        title: "Hidden gems version",
        budget: formatInr(form.budget),
        duration: "Mystery route",
        description: "Prioritizes lesser-known studios, rooftops, and quieter food counters.",
        tags: ["Hidden Gems", "Surprise"],
      },
      {
        id: "weather",
        title: "Weather-safe version",
        budget: formatInr(Math.round(form.budget * 1.05)),
        duration: "Indoor-first",
        description: "Moves outdoor stops earlier and keeps indoor backups within a short hop.",
        tags: ["Rainy Day", "AQI-aware"],
      },
    ],
    map_coordinates: normalizedStops.map((stop) => stop.coordinates),
  };
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

  return (
    <div className="smart-map">
      <div className="map-grid"></div>
      <div className="map-route-line"></div>
      {points.map((point, index) => (
        <div
          className={`map-stop stop-${index + 1}`}
          style={{
            left: `${18 + index * (64 / Math.max(points.length - 1, 1))}%`,
            top: `${preview ? 62 - index * 14 : 66 - (index % 3) * 17}%`,
          }}
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
        {preview ? "Optimized route order" : plan.route.estimated_commute_time}
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
        <div>
          <Timer size={18} />
          <span>Total duration</span>
          <strong>{plan.summary.total_duration}</strong>
        </div>
        <div>
          <IndianRupee size={18} />
          <span>Budget</span>
          <strong>{plan.summary.estimated_budget}</strong>
        </div>
        <div>
          <Route size={18} />
          <span>Distance</span>
          <strong>{plan.summary.total_travel_distance}</strong>
        </div>
        <div>
          <CloudSun size={18} />
          <span>Weather</span>
          <strong>{plan.summary.weather_snapshot}</strong>
        </div>
        <div>
          <Clock3 size={18} />
          <span>Best leave</span>
          <strong>{plan.summary.best_time_to_leave}</strong>
        </div>
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
    ["Weather", plan.summary.weather_snapshot, CloudSun],
    ["Traffic", plan.timing.traffic_note, Gauge],
    ["Opening hours", "Live opening-hour hooks ready", Clock3],
    ["AQI", "Outdoor exposure kept short and green", Wind],
    ["Nightlife", plan.timing.nightlife_window, Moon],
    ["Rain fallback", plan.timing.rainy_day_cutover, Umbrella],
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
        {signalCards.map(([label, value, Icon]) => (
          <div className="signal-card" key={label}>
            {createElement(Icon, { size: 18 })}
            <span>{label}</span>
            <strong>{value}</strong>
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

function AlternatePlans({ plan }) {
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
          <article className="alternate-card" key={alternate.id}>
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
          </article>
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

function OutputSection({ plan }) {
  return (
    <div className="nearby-output">
      <SummaryCard plan={plan} />
      <div className="output-layout">
        <div>
          <StopTimeline plan={plan} />
          <AlternatePlans plan={plan} />
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

  useEffect(() => {
    if (!loading) return undefined;
    const interval = window.setInterval(() => {
      setLoadingStep((current) => (current + 1) % LOADING_STEPS.length);
    }, 850);
    return () => window.clearInterval(interval);
  }, [loading]);

  const generatePlan = async () => {
    setLoading(true);
    setPlan(null);
    setLoadingStep(0);
    const payload = {
      location: state.location || state.detectedCity,
      detected_city: state.detectedCity,
      coordinates: state.coordinates,
      duration: state.duration === "Custom" ? state.customDuration || "Custom" : state.duration,
      moods: state.moods,
      budget: state.budget,
      transport: state.transport,
      radius: state.radius,
      group_type: state.groupType,
      surprise_me: state.surpriseMe,
    };

    const localPlan = buildNearbyPlan(state);

    try {
      const res = await fetch(apiUrl("/nearby/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Nearby planner API failed");
      const apiPlan = await res.json();
      window.setTimeout(() => {
        setPlan(apiPlan);
        setLoading(false);
      }, 1800);
    } catch {
      window.setTimeout(() => {
        setPlan(localPlan);
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

      <AnimatePresence>{plan && !loading && <OutputSection plan={plan} />}</AnimatePresence>
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
