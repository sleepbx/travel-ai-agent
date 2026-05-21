import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BedDouble,
  BusFront,
  CalendarDays,
  BrainCircuit,
  Clock3,
  IndianRupee,
  MapPin,
  PlaneTakeoff,
  Route,
  ShieldCheck,
  Sparkles,
  Star,
  TrainFront,
  UsersRound,
  Wand2,
  WalletCards,
} from "lucide-react";
import { apiUrl, backendUnavailableMessage } from "../lib/api";
import "./Home.css";

const MotionDiv = motion.div;

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

export default function Home() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    from: "",
    to: "",
    startDate: "",
    endDate: "",
    passengers: 2,
    cabin: "economy",
    transportMode: "flight",
    budget: "",
    interests: "food, culture, sightseeing",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handlePlanTrip = async () => {
    if (!form.from || !form.to || !form.startDate || !form.endDate) {
      alert("Please fill origin, destination, and dates.");
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
          origin_city: form.from,
          destination_city: form.to,
          depart_date: form.startDate,
          return_date: form.endDate,
          passengers: Number(form.passengers),
          cabin_class: form.cabin,
          transport_mode: form.transportMode,
          interests: form.interests,
          max_budget: form.budget ? Number(form.budget) : null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create trip");
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
    <div className="home">
      <section className="hero">
        <div className="hero-inner">
          <MotionDiv
            className="hero-copy"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            <span className="eyebrow"><Sparkles size={16} /> AI trip studio</span>
            <h1>Plan a trip that feels ready before you pack.</h1>
            <p>
              Build a day-wise itinerary with flights, food, attractions, budget
              awareness, and easy refinements.
            </p>

            <div className="hero-stats" aria-label="TravelAI highlights">
              <div>
                <strong>Day-wise</strong>
                <span>smart schedules</span>
              </div>
              <div>
                <strong>Budget</strong>
                <span>aware plans</span>
              </div>
              <div>
                <strong>Versioned</strong>
                <span>refinements</span>
              </div>
            </div>
          </MotionDiv>

          <MotionDiv
            className="planner-panel"
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.45 }}
          >
            <div className="panel-header">
              <div>
                <span>Start here</span>
                <h2>Create itinerary</h2>
              </div>
              <Wand2 size={24} />
            </div>

            <div className="planner-grid">
              <label>
                <span><PlaneTakeoff size={15} /> From</span>
                <input name="from" placeholder="Bengaluru" value={form.from} onChange={handleChange} />
              </label>

              <label>
                <span><MapPin size={15} /> To</span>
                <input name="to" placeholder="Goa" value={form.to} onChange={handleChange} />
              </label>

              <label>
                <span><CalendarDays size={15} /> Depart</span>
                <input type="date" name="startDate" value={form.startDate} onChange={handleChange} />
              </label>

              <label>
                <span><CalendarDays size={15} /> Return</span>
                <input type="date" name="endDate" value={form.endDate} onChange={handleChange} />
              </label>

              <label>
                <span><UsersRound size={15} /> Travelers</span>
                <input type="number" name="passengers" min="1" value={form.passengers} onChange={handleChange} />
              </label>

              <label>
                <span>Cabin</span>
                <select name="cabin" value={form.cabin} onChange={handleChange}>
                  <option value="economy">Economy</option>
                  <option value="premium_economy">Premium Economy</option>
                  <option value="business">Business</option>
                  <option value="luxury">Luxury</option>
                </select>
              </label>

              <div className="wide transport-picker" role="group" aria-label="Preferred transport">
                <span>Travel by</span>
                <div>
                  {TRANSPORT_MODES.map(({ value, label }) => (
                    <button
                      type="button"
                      className={form.transportMode === value ? "active" : ""}
                      onClick={() => setForm((current) => ({ ...current, transportMode: value }))}
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
                <input name="interests" placeholder="food, history, beaches" value={form.interests} onChange={handleChange} />
              </label>

              <label>
                <span><IndianRupee size={15} /> Budget</span>
                <input type="number" name="budget" placeholder="50000" value={form.budget} onChange={handleChange} />
              </label>
            </div>

            <button className="planner-submit" onClick={handlePlanTrip} disabled={loading}>
              {loading ? "Planning..." : "Plan my trip"}
            </button>

            {error && <div className="form-error">{error}</div>}
          </MotionDiv>
        </div>
      </section>

      <section className="feature-band">
        <div className="feature-card">
          <Sparkles size={24} />
          <h3>AI itinerary</h3>
          <p>Day plans with attractions, meals, travel time, and cost context.</p>
        </div>

        <div className="feature-card">
          <MapPin size={24} />
          <h3>Place aware</h3>
          <p>Recommendations adapt to destination, interests, dates, and pace.</p>
        </div>

        <div className="feature-card">
          <Wand2 size={24} />
          <h3>Refine anytime</h3>
          <p>Ask for cheaper, slower, foodie, family-friendly, or premium versions.</p>
        </div>
      </section>

      <section className="experience-showcase">
        <div className="showcase-copy">
          <span className="eyebrow dark"><BrainCircuit size={16} /> Live planning intelligence</span>
          <h2>Every trip opens like a polished travel dossier.</h2>
          <p>
            Flights, stays, daily routes, food, weather, source confidence, and budget pressure are shown together
            so the plan feels ready to judge, refine, and book.
          </p>

          <div className="showcase-metrics">
            <div>
              <WalletCards size={20} />
              <strong>INR 48,200</strong>
              <span>target trip ceiling</span>
            </div>
            <div>
              <ShieldCheck size={20} />
              <strong>Medium</strong>
              <span>source confidence</span>
            </div>
            <div>
              <Clock3 size={20} />
              <strong>4 days</strong>
              <span>balanced pacing</span>
            </div>
          </div>
        </div>

        <div className="dossier-preview" aria-label="Premium itinerary preview">
          <div className="dossier-map">
            <div className="map-route">
              <span>BLR</span>
              <Route size={22} />
              <span>GOI</span>
            </div>
            <div className="map-note">
              <strong>Bengaluru to Goa</strong>
              <span>Beach days, seafood, culture, and lower transfer stress</span>
            </div>
          </div>

          <div className="dossier-stack">
            <article className="dossier-tile flight">
              <div>
                <PlaneTakeoff size={19} />
                <span>Flight match</span>
              </div>
              <strong>INR 7,800 target</strong>
              <p>Nearest live fare is kept around the user ceiling.</p>
            </article>

            <article className="dossier-tile stay">
              <div>
                <BedDouble size={19} />
                <span>Stay match</span>
              </div>
              <strong>INR 4,200 / night</strong>
              <p>Central comfort base with total stay estimate.</p>
            </article>

            <article className="dossier-tile rag">
              <div>
                <Star size={19} />
                <span>RAG memory</span>
              </div>
              <strong>5 ranked sources</strong>
              <p>Local knowledge, live web context, suppliers, and weather.</p>
            </article>
          </div>
        </div>
      </section>

      <section className="journey-strip">
        <div className="journey-step active">
          <span>01</span>
          <strong>Resolve</strong>
          <p>City, airport, dates, travelers.</p>
        </div>
        <div className="journey-step">
          <span>02</span>
          <strong>Retrieve</strong>
          <p>FAISS RAG, live web, supplier APIs.</p>
        </div>
        <div className="journey-step">
          <span>03</span>
          <strong>Constrain</strong>
          <p>Flights, hotels, daily costs near budget.</p>
        </div>
        <div className="journey-step">
          <span>04</span>
          <strong>Refine</strong>
          <p>Cheaper, premium, slower, food-first.</p>
        </div>
      </section>
    </div>
  );
}
