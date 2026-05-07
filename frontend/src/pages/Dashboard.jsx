import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

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
        const res = await fetch("http://127.0.0.1:8000/trips/my", {
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
        setTrips(data);
      } catch (err) {
        console.error("Failed to load trips", err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrips();
  }, [navigate]);

  if (loading) {
    return (
      <div className="dashboard">
        <h1>Loading your trips...</h1>
        <div className="trip-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="trip-card skeleton"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h1>Welcome back 👋</h1>
      <p className="subtitle">Here are your planned trips</p>

      {trips.length === 0 ? (
        <div className="empty-state">
          <h2>No trips yet ✈️</h2>
          <p>Plan your first trip and it will appear here.</p>
        </div>
      ) : (
        <div className="trip-grid">
          {trips.map((trip) => (
            <div key={trip.id} className="trip-card">
              <h3>{trip.title}</h3>
              <p>{trip.destination}</p>

              <div className="actions">
                <button onClick={() => navigate(`/trip/${trip.id}`)}>
                  View
                </button>
                <button className="outline">Refine</button>
                <button className="danger">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
