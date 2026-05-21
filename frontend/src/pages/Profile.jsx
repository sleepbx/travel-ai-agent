import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BadgeCheck,
  CalendarDays,
  Compass,
  Crown,
  MapPinned,
  Plane,
  Route,
  ShieldCheck,
  Sparkles,
  Star,
  UserRound,
  WalletCards,
} from "lucide-react";
import { apiUrl } from "../lib/api";
import "./Profile.css";

const DESTINATION_IMAGES = [
  "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1000&q=80",
  "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1000&q=80",
  "https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=1000&q=80",
];

function safeJsonParse(value) {
  if (!value || typeof value !== "string") return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function decodeToken(token) {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

function formatDate(value) {
  if (!value) return "Recently updated";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently updated";
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getTripPlan(trip) {
  const parsed = safeJsonParse(trip.itinerary);
  if (parsed && typeof parsed === "object") return parsed;
  return {};
}

function getTripDays(trip) {
  const plan = getTripPlan(trip);
  return Number(plan.date_range?.total_days || plan.days?.length || 1);
}

function buildStats(trips) {
  const destinations = new Set(trips.map((trip) => trip.destination).filter(Boolean));
  const totalDays = trips.reduce((sum, trip) => sum + getTripDays(trip), 0);
  const jsonTrips = trips.filter((trip) => String(getTripPlan(trip).schema_version || "").startsWith("travelai_")).length;
  const recentTrip = [...trips].sort(
    (a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0)
  )[0];

  return {
    destinations: destinations.size,
    totalDays,
    jsonTrips,
    recentTrip,
    planningLevel: trips.length >= 5 ? "Expert" : trips.length >= 2 ? "Explorer" : "Getting started",
    aiReadiness: trips.length ? Math.round((jsonTrips / trips.length) * 100) : 0,
  };
}

function StatCard({ icon, label, value, note }) {
  return (
    <article className="profile-card">
      <div className="profile-card-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

export default function Profile() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [trips, setTrips] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const fetchProfileData = async () => {
      try {
        const res = await fetch(apiUrl("/trips/my"), {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch trips");

        const loadedTrips = await res.json();
        setTrips(Array.isArray(loadedTrips) ? loadedTrips : []);

        const payload = decodeToken(token);
        setName(payload.name || "TravelAI User");
        setEmail(payload.email || "");
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchProfileData();
  }, [navigate]);

  const stats = useMemo(() => buildStats(trips), [trips]);
  const recentTrips = useMemo(
    () =>
      [...trips]
        .sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
        .slice(0, 3),
    [trips]
  );

  if (loading) {
    return (
      <div className="profile-page page-wrap">
        <div className="trip-loading">Loading profile...</div>
      </div>
    );
  }

  return (
    <div className="profile-page page-wrap">
      <section className="profile-hero">
        <div className="profile-avatar">
          {name ? name.slice(0, 2).toUpperCase() : <UserRound size={32} />}
        </div>

        <div className="profile-hero-copy">
          <span className="eyebrow dark"><Compass size={16} /> Traveler profile</span>
          <h1>{name}</h1>
          <p>{email || "No email available"}</p>

          <div className="profile-chips">
            <span><Crown size={15} /> {stats.planningLevel}</span>
            <span><Route size={15} /> {stats.totalDays} planned days</span>
            <span><BadgeCheck size={15} /> {stats.aiReadiness}% structured</span>
          </div>
        </div>
      </section>

      <section className="profile-grid">
        <StatCard
          icon={<Plane size={24} />}
          label="Trips planned"
          value={trips.length}
          note="Saved itineraries ready to refine."
        />
        <StatCard
          icon={<MapPinned size={24} />}
          label="Destinations"
          value={stats.destinations}
          note="Unique places in your travel board."
        />
        <StatCard
          icon={<CalendarDays size={24} />}
          label="Travel days"
          value={stats.totalDays}
          note="Day-wise plans across every trip."
        />
        <StatCard
          icon={<Sparkles size={24} />}
          label="AI planning"
          value="Active"
          note={`${stats.jsonTrips} trip${stats.jsonTrips === 1 ? "" : "s"} using the premium JSON planner.`}
        />
      </section>

      <section className="profile-showcase">
        <div className="profile-panel signature-panel">
          <div className="panel-title">
            <span>Travel signature</span>
            <h2>Built for polished plans</h2>
          </div>

          <div className="signature-meter">
            <div style={{ width: `${stats.aiReadiness}%` }}></div>
          </div>

          <div className="signature-list">
            <div>
              <ShieldCheck size={19} />
              <span>Safety tips and source confidence are tracked inside each structured itinerary.</span>
            </div>
            <div>
              <WalletCards size={19} />
              <span>Daily cost sections keep flights, hotels, food, transport, and activities readable.</span>
            </div>
            <div>
              <Star size={19} />
              <span>Refine any trip to refresh it into the premium card experience.</span>
            </div>
          </div>
        </div>

        <div className="profile-panel recent-panel">
          <div className="panel-title">
            <span>Recent journeys</span>
            <h2>{stats.recentTrip ? "Continue planning" : "Start your first route"}</h2>
          </div>

          {recentTrips.length ? (
            <div className="recent-trip-list">
              {recentTrips.map((trip, index) => (
                <button
                  className="recent-trip"
                  style={{ backgroundImage: `url("${DESTINATION_IMAGES[index % DESTINATION_IMAGES.length]}")` }}
                  onClick={() => navigate(`/trip/${trip.id}`)}
                  key={trip.id}
                >
                  <span>{formatDate(trip.updated_at || trip.created_at)}</span>
                  <strong>{trip.title || `${trip.destination} Trip`}</strong>
                  <small>{getTripDays(trip)} day plan - {trip.destination}</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="profile-empty">
              <Sparkles size={28} />
              <p>Your best-looking trips will appear here after you create the first itinerary.</p>
              <button onClick={() => navigate("/")}>Plan a trip</button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
