# Web UI — FastAPI + React (Google-Finance style)

A second, polished front end built **alongside** the Streamlit app (Phases 0–2),
inspired by Google Finance: a dark/light dashboard with green-for-up / red-for-down
charts. It pulls the planned production stack (FastAPI + React) forward, but still runs
against **local SQLite** (the Supabase/Postgres move is a later phase).

> **The two UIs are isolated by directory, not branch.** Streamlit lives in `app/`
> (untouched); the web UI is `api/` (FastAPI) + `web/` (React). They share the
> framework-free `core/`, `data/`, and `storage/` layers and run as separate processes.

![Web dashboard (dark)](screenshots/web-dashboard-dark.png)

## Architecture

```
api/      FastAPI — thin REST layer over core/ + data/ + storage/ (+ app/sim_runner,
          which is framework-free). JWT auth on the existing bcrypt+SQLite users;
          every portfolio route scoped by the token's user_id.
web/      React + Vite + TypeScript + Tailwind SPA. React Query + axios; Recharts for
          the green/red area charts and sparklines. Light & dark themes (toggle,
          persisted in localStorage). No finance math — it only calls the API.
```

No finance/ML logic lives in `api/` or `web/`; both reuse `core/` (simulation,
metrics, optimization), `data/` (prices, tickers), and `storage/` (repository, auth).

## API (default `http://localhost:8000`)

- `POST /api/auth/signup` · `POST /api/auth/login` → `{access_token}` (JWT) ·
  `GET /api/auth/me`
- `GET /api/tickers` · `GET/POST /api/portfolios` · `GET/DELETE /api/portfolios/{id}`
  (all `user_id`-scoped)
- `POST /api/simulate` → growth series + metrics · `POST /api/optimize` → suggested vs
  equal-weight + comparison

Interactive docs at `http://localhost:8000/docs`.

## Run it (three processes)

```bash
# 1) API (port 8000) — set a real AUTH_SECRET; required when APP_ENV=production
uv run uvicorn api.main:app --reload --port 8000

# 2) Web (port 5173)
cd web && npm install && npm run dev      # opens http://localhost:5173

# 3) (optional) the original Streamlit app, unaffected
uv run streamlit run app/streamlit_app.py # port 8501
```

`web/.env` sets `VITE_API_URL` (defaults to `http://localhost:8000`). Sign up in the
UI, or seed a demo user with the existing `storage.Repository` against the same
`DATABASE_URL` the API uses.

## Security notes

- **`AUTH_SECRET`** signs the JWTs. In production (`APP_ENV=production`) it is
  **required** — the app refuses to fall back to the dev secret. Set a strong value.
- JWTs are stored in `localStorage` (standard SPA tradeoff; an XSS could read them).
- The DB is local SQLite for now; the production phase moves it to Supabase/Postgres
  (only the `DATABASE_URL` changes — the schema/migrations are unchanged).

## Features (MVP)

Login/signup · sidebar of portfolios + benchmark indices with green/red sparklines ·
**dashboard** growth area chart (green/red) with time-range tabs + a KPI grid (all
percentages time-weighted for consistency) + a metrics-vs-benchmark table ·
**new portfolio** (ticker search, weights or $-amounts, contributions) · **optimize**
(allocate/select, suggested vs equal-weight). Compare + Tracking views are follow-ups.

> **Educational use only — not financial advice.**
