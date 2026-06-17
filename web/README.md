# Portfolio Finance — Web (React)

A Google-Finance-styled React single-page app for the investment-portfolio platform.
It talks to the existing FastAPI backend; it contains **no finance math** — all
simulation/optimization is computed server-side in `core/`.

## Stack

- Vite + React + TypeScript
- Tailwind CSS v3 (`darkMode: "class"`)
- `@tanstack/react-query` (data fetching/caching), `axios` (client), `react-router-dom`
- `recharts` (charts)

## Prerequisites

- Node 22 + npm 10
- The FastAPI backend running (default `http://localhost:8000`):
  `uv run uvicorn api.main:app --port 8000` from the repo root.

## Setup & run

```bash
cd web
npm install
cp .env.example .env   # sets VITE_API_URL=http://localhost:8000
npm run dev            # serves on http://localhost:5173
```

Other scripts:

```bash
npm run build   # tsc -b && vite build  (type-checks + production build)
npm run lint    # eslint
npm run preview # preview the production build
```

## Environment

| Var            | Default                  | Purpose                          |
| -------------- | ------------------------ | -------------------------------- |
| `VITE_API_URL` | `http://localhost:8000`  | Base URL of the FastAPI backend. |

Read via `import.meta.env.VITE_API_URL` with the same default as a fallback.

## Theme

- `ThemeProvider` (`src/theme/`) defaults to the OS preference
  (`prefers-color-scheme`), persists the choice in `localStorage`, and toggles the
  `dark` class on `<html>`. The sun/moon toggle lives in the top bar.
- Tailwind defines a light (white/light-grey) and dark (near-black) palette.
- **Green-up (`#1a7f37`) / red-down (`#d1242f`)** chart semantics are
  theme-independent constants (`src/theme/colors.ts`); axis/grid/tooltip colors
  adapt to the active theme via `useChartTheme()`.

## Structure

```
src/
  api/        # typed client (axios + interceptors), endpoint fns, React Query hooks
  auth/       # AuthContext (JWT in localStorage) + provider + useAuth
  theme/      # ThemeContext/provider, chart color tokens, useTheme/useChartTheme
  charts/     # recharts: GrowthChart, ComparisonChart, WeightsBar, Sparkline
  components/  # Sidebar, TopBar, ThemeToggle, TickerSearch, MetricsTable, Modal, …
  views/      # Login, AppShell, Dashboard, NewPortfolio, Optimize
  lib/        # date ranges, formatting, benchmark index specs
```

## Disclaimer

Educational use only — not financial advice. Shown persistently in the app footer.
