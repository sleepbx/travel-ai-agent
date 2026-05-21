import "./Auth.css";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { LockKeyhole, Mail, UserPlus, UserRound } from "lucide-react";
import { apiUrl } from "../lib/api";

export default function Signup() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSignup = async () => {
    setError("");

    try {
      const res = await fetch(apiUrl("/auth/signup"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          email,
          password,
        }),
      });

      if (!res.ok) {
        throw new Error("Signup failed. Email may already exist.");
      }

      navigate("/login");
    } catch (err) {
      setError(err.message || "Signup failed");
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-icon"><UserPlus size={24} /></div>
        <h2>Create your account</h2>
        <p className="auth-subtitle">Start planning smarter trips with AI.</p>

        <label className="auth-field">
          <span><UserRound size={15} /> Full name</span>
          <input type="text" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} />
        </label>

        <label className="auth-field">
          <span><Mail size={15} /> Email</span>
          <input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>

        <label className="auth-field">
          <span><LockKeyhole size={15} /> Password</span>
          <input type="password" placeholder="Choose a password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>

        {error && <p className="auth-error">{error}</p>}

        <button className="auth-btn" onClick={handleSignup}>
          Sign up
        </button>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
