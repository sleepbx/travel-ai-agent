import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Profile.css";

export default function Profile() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [tripsCount, setTripsCount] = useState(0);
  const [citiesCount, setCitiesCount] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const fetchProfileData = async () => {
      try {
        // 🔹 Fetch trips
        const res = await fetch("http://127.0.0.1:8000/trips/my", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch trips");

        const trips = await res.json();
        setTripsCount(trips.length);

        const uniqueCities = new Set(
          trips.map((t) => t.destination)
        );
        setCitiesCount(uniqueCities.size);

        // 🔹 Decode JWT safely
        const payload = JSON.parse(
          atob(token.split(".")[1])
        );

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

  if (loading) {
    return <div className="profile-page">Loading profile...</div>;
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        {/* LEFT CARD */}
        <div className="profile-left">
          <div className="avatar-wrapper">
            <div className="avatar">
              {name.slice(0, 2).toUpperCase()}
            </div>
            <button className="avatar-edit">+</button>
          </div>

          <h2 className="username">{name}</h2>
          <p className="role">TravelAI User</p>
          <p className="email">{email}</p>
        </div>

        {/* RIGHT CARD */}
        <div className="profile-right">
          <h3>Activity Overview</h3>

          <div className="activity-list">
            <div className="activity-item">
              ✈️ <span>Trips Planned</span>
              <strong>{tripsCount}</strong>
            </div>

            <div className="activity-item">
              🌍 <span>Cities Visited</span>
              <strong>{citiesCount}</strong>
            </div>

            <div className="activity-item">
              🏨 <span>Hotel Bookings</span>
              <strong>—</strong>
            </div>

            <div className="activity-item">
              🍽️ <span>Food Experiences</span>
              <strong>—</strong>
            </div>
          </div>

          <button className="edit-profile-btn" disabled>
            Edit Profile (Coming soon)
          </button>
        </div>
      </div>
    </div>
  );
}
