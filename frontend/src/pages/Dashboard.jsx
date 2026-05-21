import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarClock, ChevronRight, MapPinned, Plus, Route, Sparkles } from "lucide-react";
import { apiUrl } from "../lib/api";
import "./Dashboard.css";

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

function tripAccent(index) {
  const accents = ["teal", "sky", "amber", "rose"];
  return accents[index % accents.length];
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [trips, setTrips] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      navigate("/login");
      return;
    }

    const fetchTrips = async () => {
      try {
        const res = await fetch(apiUrl("/trips/my"), {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }

        const data = await res.json();
        setTrips(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to load trips", err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrips();
  }, [navigate]);

  const citiesCount = useMemo(
    () => new Set(trips.map((trip) => trip.destination).filter(Boolean)).size,
    [trips]
  );

  if (loading) {
    return (
      <div className="dashboard page-wrap">
        <div className="page-heading">
          <span className="eyebrow dark"><Sparkles size={16} /> Loading workspace</span>
          <h1>Your trips</h1>
        </div>
        <div className="trip-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="trip-card skeleton"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard page-wrap">
      <section className="dashboard-header">
        <div className="page-heading">
          <span className="eyebrow dark"><Route size={16} /> Travel workspace</span>
          <h1>Your trips</h1>
          <p>Review saved itineraries, continue planning, and refine trips as your plans change.</p>
        </div>

        <button className="primary-action" onClick={() => navigate("/")}>
          <Plus size={18} />
          New trip
        </button>
      </section>

      <section className="summary-row">
        <div className="summary-card">
          <span>Trips planned</span>
          <strong>{trips.length}</strong>
        </div>
        <div className="summary-card">
          <span>Destinations</span>
          <strong>{citiesCount}</strong>
        </div>
        <div className="summary-card">
          <span>AI versions</span>
          <strong>Ready</strong>
        </div>
      </section>

      {trips.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><MapPinned size={34} /></div>
          <h2>No trips yet</h2>
          <p>Create your first itinerary and it will appear here as a trip card.</p>
          <button className="primary-action" onClick={() => navigate("/")}>
            <Plus size={18} />
            Plan a trip
          </button>
        </div>
      ) : (
        <div className="trip-grid">
          {trips.map((trip, index) => (
            <article key={trip.id} className={`trip-card ${tripAccent(index)}`}>
              <div className="trip-card-top">
                <div className="destination-mark">
                  <MapPinned size={22} />
                </div>
                <span>{formatDate(trip.updated_at || trip.created_at)}</span>
              </div>

              <h3>{trip.title || `${trip.destination} Trip`}</h3>
              <p>{trip.destination || "Destination pending"}</p>

              <div className="trip-meta">
                <span><CalendarClock size={15} /> Saved itinerary</span>
                <span><Sparkles size={15} /> AI ready</span>
              </div>

              <button className="card-action" onClick={() => navigate(`/trip/${trip.id}`)}>
                Open trip
                <ChevronRight size={17} />
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
