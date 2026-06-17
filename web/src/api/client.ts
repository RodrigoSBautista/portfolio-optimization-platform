import axios from "axios";

export const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "pf_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({ baseURL: API_URL });

// Attach the JWT to every request when present.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, drop the token and bounce to login. A custom event lets AuthContext
// react without coupling the axios layer to React.
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken();
      window.dispatchEvent(new Event("pf-unauthorized"));
    }
    return Promise.reject(error);
  },
);

// Extract a human-readable message from a FastAPI error response.
export function apiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    if (error.message) return error.message;
  }
  return fallback;
}
