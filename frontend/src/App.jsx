import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import "./App.css";

import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import TripDetails from "./pages/TripDetails";
import Profile from "./pages/Profile";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import PlanTrip from "./pages/PlanTrip";
import TravelCommand from "./pages/TravelCommand";
import IndiaPulse from "./pages/IndiaPulse";
import NearbyPlanner from "./pages/NearbyPlanner";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="app-shell">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/command" element={<TravelCommand />} />
          <Route path="/india-pulse" element={<IndiaPulse />} />
          <Route path="/nearby" element={<NearbyPlanner />} />
          <Route path="/planTrip" element={<PlanTrip />} />
          <Route path="/trip/:id" element={<TripDetails />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
