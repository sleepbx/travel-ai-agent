import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import "./TripDetails.css";

function parseItineraryByDay(itineraryText) {
  if (!itineraryText) return [];

  const dayRegex = /(Day\s+\d+:)/g;
  const parts = itineraryText.split(dayRegex).filter(Boolean);

  const days = [];

  for (let i = 0; i < parts.length; i += 2) {
    const title = parts[i];
    const content = parts[i + 1] || "";
    days.push({
      title: title.trim(),
      content: content.trim(),
    });
  }

  return days;
}

export default function TripDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [instruction, setInstruction] = useState("");
  const [refining, setRefining] = useState(false);
  const [openDay, setOpenDay] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      navigate("/login");
      return;
    }

    const fetchTrip = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/trips/my", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Failed to fetch trips");

        const trips = await res.json();
        const found = trips.find((t) => t.id === id);

        if (!found) {
          navigate("/dashboard");
          return;
        }

        setTrip(found);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrip();
  }, [id, navigate]);

  const handleRefine = async () => {
    if (!instruction.trim()) return;

    setRefining(true);

    try {
      const token = localStorage.getItem("token");

      const res = await fetch(
        `http://127.0.0.1:8000/trips/${id}/refine`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ instruction }),
        }
      );

      if (!res.ok) throw new Error("Refine failed");

      const data = await res.json();

      setTrip((prev) => ({
        ...prev,
        itinerary: data.updated_itinerary,
      }));

      setInstruction("");
      setOpenDay(0);
    } catch (err) {
      console.error(err);
      alert("Failed to refine trip");
    } finally {
      setRefining(false);
    }
  };

  if (loading) {
    return <div className="trip-details">Loading trip...</div>;
  }

  if (!trip) {
    return <div className="trip-details">Trip not found</div>;
  }

  const days = parseItineraryByDay(trip.itinerary);

  return (
    <div className="trip-details">
      {/* HEADER */}
      <div style={{ marginBottom: "24px" }}>
        <h1>{trip.title}</h1>
        <p className="subtitle">Destination: {trip.destination}</p>
      </div>

      {/* DAY-WISE ITINERARY */}
      <section>
        <h3 style={{ marginBottom: "12px" }}>📅 Day-wise Itinerary</h3>

        {days.map((day, index) => (
          <div
            key={index}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              marginBottom: "12px",
              overflow: "hidden",
            }}
          >
            <div
              onClick={() =>
                setOpenDay(openDay === index ? null : index)
              }
              style={{
                padding: "14px",
                background: "#f9fafb",
                cursor: "pointer",
                fontWeight: 600,
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>{day.title}</span>
              <span>{openDay === index ? "−" : "+"}</span>
            </div>

            {openDay === index && (
              <pre
                style={{
                  padding: "14px",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  fontSize: "14px",
                  background: "#fff",
                }}
              >
                {day.content}
              </pre>
            )}
          </div>
        ))}
      </section>

      {/* REFINE */}
      <section
        style={{
          marginTop: "32px",
          padding: "20px",
          border: "1px solid #eee",
          borderRadius: "8px",
          background: "#fafafa",
        }}
      >
        <h3>✏️ Refine your trip</h3>
        <p style={{ fontSize: "14px", color: "#666" }}>
          Example: <em>Add nightlife on day 2 and reduce overall cost</em>
        </p>

        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Enter refinement instruction..."
          rows={4}
          style={{
            width: "100%",
            padding: "10px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            resize: "vertical",
          }}
        />

        <div style={{ marginTop: "12px", textAlign: "right" }}>
          <button
            onClick={handleRefine}
            disabled={refining || !instruction.trim()}
            style={{
              padding: "10px 16px",
              borderRadius: "6px",
              border: "none",
              background: refining ? "#aaa" : "#2563eb",
              color: "#fff",
              cursor: refining ? "not-allowed" : "pointer",
            }}
          >
            {refining ? "Refining..." : "Refine Trip"}
          </button>
        </div>
      </section>
    </div>
  );
}
