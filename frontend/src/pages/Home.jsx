import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    from: "",
    to: "",
    startDate: "",
    endDate: "",
    passengers: 2,
    cabin: "economy",
    budget: "",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handlePlanTrip = async () => {
    if (!form.from || !form.to || !form.startDate || !form.endDate) {
      alert("Please fill From, To and Dates");
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
          origin_city: form.from,
          destination_city: form.to,
          depart_date: form.startDate,
          return_date: form.endDate,
          passengers: Number(form.passengers),
          cabin_class: form.cabin,
          max_budget: form.budget ? Number(form.budget) : null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create trip");
      }

      const trip = await res.json();

      // 🚀 GO DIRECTLY TO CHAT / DETAILS VIEW
      navigate(`/trip/${trip.id}`);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="home">
      <section className="hero">
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          Your personal <span>AI travel expert</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          Plan trips easily, powered by AI ✨
        </motion.p>

        {/* SEARCH CARD */}
        <motion.div
          className="search-card"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <input
            name="from"
            placeholder="From city / state"
            value={form.from}
            onChange={handleChange}
          />

          <input
            name="to"
            placeholder="To city / state"
            value={form.to}
            onChange={handleChange}
          />

          <input
            type="date"
            name="startDate"
            value={form.startDate}
            onChange={handleChange}
          />

          <input
            type="date"
            name="endDate"
            value={form.endDate}
            onChange={handleChange}
          />

          <input
            type="number"
            name="passengers"
            min="1"
            value={form.passengers}
            onChange={handleChange}
          />

          <select name="cabin" value={form.cabin} onChange={handleChange}>
            <option value="economy">Economy</option>
            <option value="business">Business</option>
            <option value="luxury">Luxury</option>
          </select>

          <input
            type="number"
            name="budget"
            placeholder="Budget (INR)"
            value={form.budget}
            onChange={handleChange}
          />

          <button onClick={handlePlanTrip} disabled={loading}>
            {loading ? "Planning your trip..." : "Plan My Trip"}
          </button>
        </motion.div>
      </section>

      <section className="features">
        <div className="feature-card">
          🤖
          <h3>AI Itinerary</h3>
          <p>Day-wise plans with food, travel & cost</p>
        </div>

        <div className="feature-card">
          🍽️
          <h3>Real Restaurants</h3>
          <p>Actual restaurant names, not generic food</p>
        </div>

        <div className="feature-card">
          💰
          <h3>Budget Aware</h3>
          <p>Trips that respect your spending limit</p>
        </div>
      </section>
    </div>
  );
}
