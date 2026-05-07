import { NavLink, useNavigate } from "react-router-dom";
import { Plane } from "lucide-react";
import "./Navbar.css";

export default function Navbar() {
  const navigate = useNavigate();
  const isLoggedIn = Boolean(localStorage.getItem("token"));

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="nav-left">
        <Plane size={28} className="logo-icon" />
        <span className="logo-text">TravelAI</span>
      </div>

      <div className="nav-center">
        <NavLink to="/" end>Home</NavLink>
        {isLoggedIn && <NavLink to="/dashboard">My Trips</NavLink>}
        {isLoggedIn && <NavLink to="/planTrip">Plan Trip</NavLink>}
        {isLoggedIn && <NavLink to="/profile">Profile</NavLink>}
      </div>

      <div className="nav-right">
        {!isLoggedIn ? (
          <>
            <NavLink to="/login" className="btn-outline">
              Login
            </NavLink>
            <NavLink to="/signup" className="btn-primary">
              Sign up
            </NavLink>
          </>
        ) : (
          <button className="btn-outline" onClick={handleLogout}>
            Logout
          </button>
        )}
      </div>
    </nav>
  );
}
