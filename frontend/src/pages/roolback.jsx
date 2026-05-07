// import { useParams, useNavigate } from "react-router-dom";
// import { useEffect, useState } from "react";
// import "./TripDetails.css";

// /* ------------------ Helpers ------------------ */
// function parseItineraryByDay(itineraryText) {
//   if (!itineraryText) return [];

//   const dayRegex = /(Day\s+\d+:)/g;
//   const parts = itineraryText.split(dayRegex).filter(Boolean);

//   const days = [];
//   for (let i = 0; i < parts.length; i += 2) {
//     days.push({
//       title: parts[i].trim(),
//       content: (parts[i + 1] || "").trim(),
//     });
//   }
//   return days;
// }

// /* ------------------ Component ------------------ */
// export default function TripDetails() {
//   const { id } = useParams();
//   const navigate = useNavigate();

//   const [trip, setTrip] = useState(null);
//   const [versions, setVersions] = useState([]);
//   const [loading, setLoading] = useState(true);

//   const [instruction, setInstruction] = useState("");
//   const [refining, setRefining] = useState(false);
//   const [openDay, setOpenDay] = useState(0);
//   const [rollingBack, setRollingBack] = useState(null);

//   const token = localStorage.getItem("token");

//   /* ------------------ Fetch Trip + Versions ------------------ */
//   useEffect(() => {
//     if (!token) {
//       navigate("/login");
//       return;
//     }

//     const fetchData = async () => {
//       try {
//         const tripsRes = await fetch("http://127.0.0.1:8000/trips/my", {
//           headers: { Authorization: `Bearer ${token}` },
//         });

//         const trips = await tripsRes.json();
//         const found = trips.find((t) => t.id === id);
//         if (!found) {
//           navigate("/dashboard");
//           return;
//         }
//         setTrip(found);

//         const versionsRes = await fetch(
//           `http://127.0.0.1:8000/trips/${id}/versions`,
//           {
//             headers: { Authorization: `Bearer ${token}` },
//           }
//         );
//         setVersions(await versionsRes.json());
//       } catch (err) {
//         console.error(err);
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchData();
//   }, [id, navigate, token]);

//   /* ------------------ Refine ------------------ */
//   const handleRefine = async () => {
//     if (!instruction.trim()) return;

//     setRefining(true);
//     try {
//       const res = await fetch(
//         `http://127.0.0.1:8000/trips/${id}/refine`,
//         {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//             Authorization: `Bearer ${token}`,
//           },
//           body: JSON.stringify({ instruction }),
//         }
//       );

//       const data = await res.json();
//       setTrip((prev) => ({ ...prev, itinerary: data.updated_itinerary }));
//       setInstruction("");

//       // refresh versions
//       const vr = await fetch(
//         `http://127.0.0.1:8000/trips/${id}/versions`,
//         { headers: { Authorization: `Bearer ${token}` } }
//       );
//       setVersions(await vr.json());
//     } catch {
//       alert("Refine failed");
//     } finally {
//       setRefining(false);
//     }
//   };

//   /* ------------------ Rollback ------------------ */
//   const handleRollback = async (version) => {
//     setRollingBack(version);
//     try {
//       const res = await fetch(
//         `http://127.0.0.1:8000/trips/${id}/rollback`,
//         {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json",
//             Authorization: `Bearer ${token}`,
//           },
//           body: JSON.stringify({ version_number: version }),
//         }
//       );

//       const data = await res.json();
//       setTrip((prev) => ({ ...prev, itinerary: data.current_itinerary }));

//       const vr = await fetch(
//         `http://127.0.0.1:8000/trips/${id}/versions`,
//         { headers: { Authorization: `Bearer ${token}` } }
//       );
//       setVersions(await vr.json());
//     } catch {
//       alert("Rollback failed");
//     } finally {
//       setRollingBack(null);
//     }
//   };

//   if (loading) return <div className="trip-details">Loading...</div>;
//   if (!trip) return <div className="trip-details">Trip not found</div>;

//   const days = parseItineraryByDay(trip.itinerary);

//   return (
//     <div className="trip-details">
//       <h1>{trip.title}</h1>
//       <p className="subtitle">Destination: {trip.destination}</p>

//       {/* -------- Itinerary -------- */}
//       <h3>📅 Day-wise Itinerary</h3>
//       {days.map((day, i) => (
//         <div key={i} style={{ border: "1px solid #ddd", marginBottom: 10 }}>
//           <div
//             style={{
//               padding: 12,
//               background: "#f5f5f5",
//               cursor: "pointer",
//               fontWeight: 600,
//             }}
//             onClick={() => setOpenDay(openDay === i ? null : i)}
//           >
//             {day.title}
//           </div>

//           {openDay === i && (
//             <pre style={{ padding: 12, whiteSpace: "pre-wrap" }}>
//               {day.content}
//             </pre>
//           )}
//         </div>
//       ))}

//       {/* -------- Refine -------- */}
//       <section style={{ marginTop: 30 }}>
//         <h3>✏️ Refine Trip</h3>
//         <textarea
//           value={instruction}
//           onChange={(e) => setInstruction(e.target.value)}
//           rows={4}
//           style={{ width: "100%", padding: 10 }}
//         />
//         <button
//           onClick={handleRefine}
//           disabled={refining || !instruction.trim()}
//         >
//           {refining ? "Refining..." : "Refine"}
//         </button>
//       </section>

//       {/* -------- Versions -------- */}
//       <section style={{ marginTop: 40 }}>
//         <h3>🧠 Version History</h3>

//         {versions.map((v) => (
//           <div
//             key={v.version}
//             style={{
//               display: "flex",
//               justifyContent: "space-between",
//               padding: "8px 0",
//               borderBottom: "1px solid #eee",
//             }}
//           >
//             <div>
//               <strong>Version {v.version}</strong>
//               <div style={{ fontSize: 12, color: "#666" }}>
//                 {v.instruction}
//               </div>
//             </div>

//             <button
//               onClick={() => handleRollback(v.version)}
//               disabled={rollingBack === v.version}
//             >
//               {rollingBack === v.version ? "Rolling back..." : "Rollback"}
//             </button>
//           </div>
//         ))}
//       </section>
//     </div>
//   );
// }
