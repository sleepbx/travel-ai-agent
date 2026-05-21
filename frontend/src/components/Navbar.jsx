import { NavLink, useNavigate } from "react-router-dom";
import { Activity, Compass, LayoutDashboard, LogIn, LogOut, Map, Newspaper, Sparkles, UserRound } from "lucide-react";
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
      <NavLink to="/" className="nav-left" aria-label="TravelAI home">
        <Compass size={28} className="logo-icon" />
        <span className="logo-text">TravelAI</span>
      </NavLink>

      <div className="nav-center">
        <NavLink to="/" end><Map size={16} /> Plan</NavLink>
        <NavLink to="/nearby"><Sparkles size={16} /> Nearby</NavLink>
        <NavLink to="/india-pulse"><Newspaper size={16} /> Pulse</NavLink>
        {isLoggedIn && <NavLink to="/dashboard"><LayoutDashboard size={16} /> Trips</NavLink>}
        {isLoggedIn && <NavLink to="/command"><Activity size={16} /> HQ</NavLink>}
        {isLoggedIn && <NavLink to="/profile"><UserRound size={16} /> Profile</NavLink>}
      </div>

      <div className="nav-right">
        {!isLoggedIn ? (
          <>
            <NavLink to="/login" className="btn-outline">
              <LogIn size={16} />
              Login
            </NavLink>
            <NavLink to="/signup" className="btn-primary">
              Sign up
            </NavLink>
          </>
        ) : (
          <button className="btn-outline" onClick={handleLogout}>
            <LogOut size={16} />
            Logout
          </button>
        )}
      </div>
    </nav>
  );
}
