import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { ThemeToggle } from "../components/ThemeToggle";

export function Login() {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const reduce = useReducedMotion();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(username, password);
      else await signup(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Authentication failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-full flex-col overflow-hidden bg-surface dark:bg-surface-dark">
      {/* Subtle mesh/gradient backdrop. */}
      <div
        className="pointer-events-none absolute inset-0 opacity-70 dark:opacity-50"
        aria-hidden
        style={{
          background:
            "radial-gradient(60rem 40rem at 15% -10%, rgba(26,115,232,0.18), transparent 60%), radial-gradient(50rem 40rem at 110% 110%, rgba(26,127,55,0.14), transparent 55%)",
        }}
      />

      <div className="relative flex justify-end p-3">
        <ThemeToggle />
      </div>
      <div className="relative flex flex-1 items-center justify-center px-4 pb-16">
        <motion.div
          className="w-full max-w-sm"
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduce ? 0 : 0.35, ease: "easeOut" }}
        >
          <div className="mb-6 text-center">
            <h1 className="text-2xl font-semibold">
              <span className="text-brand">Portfolio</span>{" "}
              <span className="font-light text-content-muted dark:text-content-dark-muted">
                Finance
              </span>
            </h1>
            <p className="mt-1 text-sm text-content-muted dark:text-content-dark-muted">
              {mode === "login" ? "Log in to your account" : "Create an account"}
            </p>
          </div>

          <form
            onSubmit={submit}
            className="rounded-2xl border border-edge bg-surface-alt/80 p-5 shadow-card backdrop-blur-sm dark:border-edge-dark dark:bg-surface-dark-alt/80 dark:shadow-none"
          >
            <label className="mb-3 block">
              <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                Username
              </span>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/30 dark:border-edge-dark dark:bg-surface-dark"
              />
            </label>
            <label className="mb-4 block">
              <span className="mb-1 block text-xs text-content-muted dark:text-content-dark-muted">
                Password
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/30 dark:border-edge-dark dark:bg-surface-dark"
              />
            </label>

            {error && (
              <div className="mb-3 rounded-lg border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface-alt disabled:opacity-60 dark:focus-visible:ring-offset-surface-dark-alt"
            >
              {busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-content-muted dark:text-content-dark-muted">
            {mode === "login" ? "No account?" : "Already have an account?"}{" "}
            <button
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setError(null);
              }}
              className="font-medium text-brand hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              {mode === "login" ? "Sign up" : "Log in"}
            </button>
          </p>

          <p className="mt-6 text-center text-xs text-content-muted dark:text-content-dark-muted">
            Educational use only — not financial advice.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
