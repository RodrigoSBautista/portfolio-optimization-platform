import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { ThemeToggle } from "../components/ThemeToggle";

export function Login() {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
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
    <div className="flex min-h-full flex-col bg-surface dark:bg-surface-dark">
      <div className="flex justify-end p-3">
        <ThemeToggle />
      </div>
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-sm">
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
            className="rounded-lg border border-edge bg-surface-alt p-5 dark:border-edge-dark dark:bg-surface-dark-alt"
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
                className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark"
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
                className="w-full rounded-md border border-edge bg-surface px-3 py-2 text-sm outline-none focus:border-brand dark:border-edge-dark dark:bg-surface-dark"
              />
            </label>

            {error && (
              <div className="mb-3 rounded-md border border-down/40 bg-down/10 px-3 py-2 text-sm text-down">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-md bg-brand px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
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
              className="font-medium text-brand hover:underline"
            >
              {mode === "login" ? "Sign up" : "Log in"}
            </button>
          </p>

          <p className="mt-6 text-center text-xs text-content-muted dark:text-content-dark-muted">
            Educational use only — not financial advice.
          </p>
        </div>
      </div>
    </div>
  );
}
