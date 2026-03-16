"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "@/lib/supabase";

type Mode = "sign-in" | "sign-up";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function switchMode(newMode: Mode) {
    setMode(newMode);
    setError(null);
    setSuccess(null);
    setConfirmPassword("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const supabase = getSupabaseBrowserClient();

      if (mode === "sign-up") {
        // ── Sign Up ──
        if (password !== confirmPassword) {
          setError("Passwords do not match.");
          setLoading(false);
          return;
        }
        if (password.length < 6) {
          setError("Password must be at least 6 characters.");
          setLoading(false);
          return;
        }

        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { role: "customer" }, // default role
          },
        });

        if (signUpError) {
          setError(signUpError.message);
          return;
        }

        setSuccess(
          "Account created! Check your email for a confirmation link, then sign in."
        );
        setPassword("");
        setConfirmPassword("");
      } else {
        // ── Sign In ──
        const { data, error: authError } =
          await supabase.auth.signInWithPassword({ email, password });

        if (authError) {
          setError(authError.message);
          return;
        }

        const role = data?.user?.user_metadata?.role ?? "customer";
        router.push(role === "admin" ? "/admin" : "/");
        router.refresh();
      }
    } catch {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  // ── Shared input style ──
  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.7rem 0.875rem",
    borderRadius: 8,
    border: "1px solid rgba(148, 163, 184, 0.15)",
    background: "rgba(15, 15, 30, 0.6)",
    color: "#e2e8f0",
    fontSize: "0.875rem",
    outline: "none",
    boxSizing: "border-box",
    transition: "border-color 0.2s",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "0.8125rem",
    fontWeight: 500,
    color: "#94a3b8",
    marginBottom: "0.5rem",
  };

  const focusBorder = "rgba(138, 92, 246, 0.5)";
  const blurBorder = "rgba(148, 163, 184, 0.15)";

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "linear-gradient(135deg, #0a0a0f 0%, #141424 50%, #0d1117 100%)",
        fontFamily:
          "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          padding: "2.5rem",
          borderRadius: 16,
          background: "rgba(20, 20, 36, 0.85)",
          border: "1px solid rgba(138, 92, 246, 0.15)",
          backdropFilter: "blur(20px)",
          boxShadow:
            "0 8px 32px rgba(0,0,0,0.4), 0 0 60px rgba(138, 92, 246, 0.08)",
        }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1rem",
              fontSize: 22,
            }}
          >
            🛡️
          </div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "#e2e8f0",
              margin: "0 0 0.5rem",
            }}
          >
            Support Agent
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              color: "#94a3b8",
              margin: 0,
            }}
          >
            {mode === "sign-in"
              ? "Sign in to your account"
              : "Create a new account"}
          </p>
        </div>

        {/* Mode Toggle Tabs */}
        <div
          style={{
            display: "flex",
            borderRadius: 8,
            background: "rgba(15, 15, 30, 0.5)",
            border: "1px solid rgba(148, 163, 184, 0.1)",
            padding: 3,
            marginBottom: "1.5rem",
          }}
        >
          {(["sign-in", "sign-up"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              style={{
                flex: 1,
                padding: "0.5rem",
                borderRadius: 6,
                border: "none",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s",
                background:
                  mode === m
                    ? "linear-gradient(135deg, #8b5cf6, #6366f1)"
                    : "transparent",
                color: mode === m ? "#fff" : "#94a3b8",
              }}
            >
              {m === "sign-in" ? "Sign In" : "Sign Up"}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              padding: "0.75rem 1rem",
              borderRadius: 8,
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#ef4444",
              fontSize: "0.8125rem",
              marginBottom: "1.25rem",
            }}
          >
            {error}
          </div>
        )}

        {/* Success */}
        {success && (
          <div
            style={{
              padding: "0.75rem 1rem",
              borderRadius: 8,
              background: "rgba(34, 197, 94, 0.1)",
              border: "1px solid rgba(34, 197, 94, 0.3)",
              color: "#22c55e",
              fontSize: "0.8125rem",
              marginBottom: "1.25rem",
            }}
          >
            {success}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {/* Email */}
          <div style={{ marginBottom: "1.25rem" }}>
            <label htmlFor="email" style={labelStyle}>
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
              style={inputStyle}
              onFocus={(e) => (e.target.style.borderColor = focusBorder)}
              onBlur={(e) => (e.target.style.borderColor = blurBorder)}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: mode === "sign-up" ? "1.25rem" : "1.75rem" }}>
            <label htmlFor="password" style={labelStyle}>
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={
                mode === "sign-in" ? "current-password" : "new-password"
              }
              placeholder="••••••••"
              style={inputStyle}
              onFocus={(e) => (e.target.style.borderColor = focusBorder)}
              onBlur={(e) => (e.target.style.borderColor = blurBorder)}
            />
          </div>

          {/* Confirm Password — only for Sign Up */}
          {mode === "sign-up" && (
            <div style={{ marginBottom: "1.75rem" }}>
              <label htmlFor="confirmPassword" style={labelStyle}>
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="••••••••"
                style={inputStyle}
                onFocus={(e) => (e.target.style.borderColor = focusBorder)}
                onBlur={(e) => (e.target.style.borderColor = blurBorder)}
              />
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: 8,
              border: "none",
              background: loading
                ? "rgba(138, 92, 246, 0.4)"
                : "linear-gradient(135deg, #8b5cf6, #6366f1)",
              color: "#fff",
              fontSize: "0.875rem",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "opacity 0.2s, transform 0.1s",
            }}
          >
            {loading
              ? mode === "sign-in"
                ? "Signing in..."
                : "Creating account..."
              : mode === "sign-in"
              ? "Sign In"
              : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
