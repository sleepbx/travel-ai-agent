import "./Auth.css";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { LockKeyhole, LogIn, Mail } from "lucide-react";
import { apiUrl } from "../lib/api";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async () => {
    setError("");

    try {
      const res = await fetch(apiUrl("/auth/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!res.ok) {
        throw new Error("Invalid email or password");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Login failed");
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-icon"><LogIn size={24} /></div>
        <h2>Welcome back</h2>
        <p className="auth-subtitle">Login to continue planning your trips.</p>

        <label className="auth-field">
          <span><Mail size={15} /> Email</span>
          <input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>

        <label className="auth-field">
          <span><LockKeyhole size={15} /> Password</span>
          <input type="password" placeholder="Your password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>

        {error && <p className="auth-error">{error}</p>}

        <button className="auth-btn" onClick={handleLogin}>
          Login
        </button>

        <p className="auth-footer">
          Do not have an account? <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
