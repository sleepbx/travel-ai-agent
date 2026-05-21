import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CalendarDays,
  BusFront,
  IndianRupee,
  MapPin,
  PlaneTakeoff,
  Sparkles,
  TrainFront,
  UsersRound,
} from "lucide-react";
import { apiUrl, backendUnavailableMessage } from "../lib/api";
import "./PlanTrip.css";

const TRANSPORT_MODES = [
  { value: "flight", label: "Flight" },
  { value: "train", label: "Train" },
  { value: "bus", label: "Bus" },
];

function transportIcon(value) {
  if (value === "train") return <TrainFront size={16} />;
  if (value === "bus") return <BusFront size={16} />;
  return <PlaneTakeoff size={16} />;
}

export default function PlanTrip() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    from_city: "",
    to_city: "",
    start_date: "",
    end_date: "",
    passengers: 2,
    cabin_class: "economy",
    transport_mode: "flight",
    budget: "",
    interests: "sightseeing",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    if (!form.from_city || !form.to_city || !form.start_date || !form.end_date) {
      alert("Please fill all required fields");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(apiUrl("/trips/create"), {
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
          transport_mode: form.transport_mode,
          interests: form.interests,
          max_budget: form.budget ? Number(form.budget) : null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Trip creation failed");
      }

      const trip = await res.json();
      navigate(`/trip/${trip.trip_id}`);
    } catch (err) {
      const message =
        err instanceof TypeError
          ? backendUnavailableMessage()
          : err.message;
      setError(message);
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="plan-trip page-wrap">
      <section className="plan-heading">
        <span className="eyebrow dark"><Sparkles size={16} /> Trip builder</span>
        <h1>Create a detailed itinerary</h1>
        <p>Give TravelAI the basics and it will build a practical plan you can refine later.</p>
      </section>

      <section className="plan-form">
        <label>
          <span><PlaneTakeoff size={15} /> From</span>
          <input name="from_city" placeholder="From city" value={form.from_city} onChange={handleChange} />
        </label>

        <label>
          <span><MapPin size={15} /> To</span>
          <input name="to_city" placeholder="Destination city" value={form.to_city} onChange={handleChange} />
        </label>

        <label>
          <span><CalendarDays size={15} /> Start date</span>
          <input type="date" name="start_date" value={form.start_date} onChange={handleChange} />
        </label>

        <label>
          <span><CalendarDays size={15} /> End date</span>
          <input type="date" name="end_date" value={form.end_date} onChange={handleChange} />
        </label>

        <label>
          <span><UsersRound size={15} /> Travelers</span>
          <input type="number" name="passengers" min="1" value={form.passengers} onChange={handleChange} />
        </label>

        <label>
          <span>Cabin class</span>
          <select name="cabin_class" value={form.cabin_class} onChange={handleChange}>
            <option value="economy">Economy</option>
            <option value="premium_economy">Premium Economy</option>
            <option value="business">Business</option>
          </select>
        </label>

        <div className="transport-choice wide" role="group" aria-label="Preferred transport">
          <span>Travel by</span>
          <div>
            {TRANSPORT_MODES.map(({ value, label }) => (
              <button
                type="button"
                className={form.transport_mode === value ? "active" : ""}
                onClick={() => setForm((current) => ({ ...current, transport_mode: value }))}
                key={value}
              >
                {transportIcon(value)}
                {label}
              </button>
            ))}
          </div>
        </div>

        <label className="wide">
          <span>Interests</span>
          <input name="interests" placeholder="food, history, nightlife" value={form.interests} onChange={handleChange} />
        </label>

        <label>
          <span><IndianRupee size={15} /> Budget</span>
          <input type="number" name="budget" placeholder="Budget in INR" value={form.budget} onChange={handleChange} />
        </label>

        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Planning..." : "Create trip"}
        </button>

        {error && <div className="form-error">{error}</div>}
      </section>
    </div>
  );
}
