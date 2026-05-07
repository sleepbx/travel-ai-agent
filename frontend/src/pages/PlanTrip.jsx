import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./PlanTrip.css";

export default function PlanTrip() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    from_city: "",
    to_city: "",
    start_date: "",
    end_date: "",
    passengers: 2,
    cabin_class: "economy",
    budget: "",
    interests: "sightseeing",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    if (
      !form.from_city ||
      !form.to_city ||
      !form.start_date ||
      !form.end_date
    ) {
      alert("Please fill all required fields");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/trips/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          origin_city: form.from_city,
          destination_city: form.to_city,
          depart_date: form.start_date,
          return_date: form.end_date,
          passengers: Number(form.passengers),
          cabin_class: form.cabin_class,
          interests: form.interests,
          max_budget: form.budget ? Number(form.budget) : null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Trip creation failed");
      }

      const trip = await res.json();

      // Redirect to Trip Details
      navigate(`/trip/${trip.id}`);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="plan-trip">
      <h1>Plan your trip ✈️</h1>
      <p className="subtitle">Let AI create a personalized itinerary</p>

      <div className="plan-form">
        <input
          name="from_city"
          placeholder="From city"
          value={form.from_city}
          onChange={handleChange}
        />

        <input
          name="to_city"
          placeholder="To city"
          value={form.to_city}
          onChange={handleChange}
        />

        <input
          type="date"
          name="start_date"
          value={form.start_date}
          onChange={handleChange}
        />

        <input
          type="date"
          name="end_date"
          value={form.end_date}
          onChange={handleChange}
        />

        <input
          type="number"
          name="passengers"
          min="1"
          value={form.passengers}
          onChange={handleChange}
        />

        <select
          name="cabin_class"
          value={form.cabin_class}
          onChange={handleChange}
        >
          <option value="economy">Economy</option>
          <option value="premium_economy">Premium Economy</option>
          <option value="business">Business</option>
        </select>

        <input
          name="interests"
          placeholder="Interests (food, history, nightlife)"
          value={form.interests}
          onChange={handleChange}
        />

        <input
          type="number"
          name="budget"
          placeholder="Budget (INR)"
          value={form.budget}
          onChange={handleChange}
        />

        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Planning your trip..." : "Create Trip"}
        </button>
      </div>
    </div>
  );
}
