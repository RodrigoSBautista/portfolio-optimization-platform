# Progress

> Living checkpoint so any session (or teammate) can resume cleanly after an
> interruption. Keep this current — see [WORKFLOW.md](WORKFLOW.md). Update the
> **Next step** line so a cold start knows exactly what to do next.

_Last updated: 2026-07-04_

## Next step (start here on resume)

- **Analytics push is complete** (Monte Carlo projection, retirement, frontier,
  diversification, dashboard advanced options — all live-validated). Remaining for
  the **Final Phase (production)**: SQLite→**Supabase Postgres** (Alembic — only
  `DATABASE_URL` changes), **GitHub Actions cron** for daily refresh, auth hardening
  (refresh tokens), and **cloud deploy**. See `docs/PLAN.md` Final Phase +
  [docs/WEB_UI.md](WEB_UI.md).
- **Analytics follow-ups (non-blocking, from reviews):** frontier request's unused
  `risk_free_rate` (add a max-Sharpe marker or drop it); metric strings can render
  "nan" on degenerate windows; Streamlit hasn't adopted the new core params
  (rebalance/rf/inflation/escalation/fee) — port if wanted; Retirement toggle lacks
  aria-pressed.
- **Web-UI known follow-ups (non-blocking):** sidebar does one `/api/simulate` per row
  (N+1 live fetches — fine for a few portfolios; batch later); JWT in `localStorage`;
  focus trap in drawer/modal; route-level code-splitting (~900 kB JS chunk).
- **Known Phase 1 follow-ups (non-blocking):** tracking metrics are value-based
  (honest caption added); a correct TWR-based tracking metric would need storing the
  `twr_index` in `daily_valuations` (schema migration). Auth signup has a benign
  TOCTOU on the username-unique check (DB constraint still protects integrity).
- **Workflow:** solo build + an independent `/code-review` on each feature branch
  before merge (chosen 2026-06-13). Full agent team reserved for Phase 2 research.
- **Run the app:** `uv run streamlit run app/streamlit_app.py` (after
  `uv run alembic upgrade head`). Refresh job: `uv run python -m jobs.refresh`.
- **Remote (SSH):** `git@github.com:RodrigoSBautista/portfolio-optimization-platform.git`

## Done (latest)

- **✅ Lot-based persistence + API (`feat/api-lots`)** — dated-purchase portfolios
  now persist and flow through the REST layer end to end (219 tests green; ruff clean).
  **Storage:** `LotRow` model + `Portfolio.lots` (delete-orphan cascade), Alembic
  migration `5cbf39db2a2f` (up/down round-trip verified on scratch SQLite);
  `repository.save_portfolio` replaces lots on update, `portfolio_io.orm_to_spec` and
  JSON export/import restore them (spec v2). **sim_runner:** lot branch in
  `run_simulation` (`simulate_lots_detailed` + mirror-lot benchmark with identical
  dollars/dates; rejects fee/rebalance/escalation overrides as `SimError`; weighted
  path unchanged). **API:** `LotDTO` + `PortfolioSpecDTO.lots`, `BuyMarker` +
  `SimulateResponse.buy_markers`; `/api/simulate` lot mode ignores `start`, fetches
  from `min(lot.date)`, 422s the inapplicable knobs, returns snapped buy markers;
  portfolios CRUD + compare carry lots. **jobs/refresh:** lot branch (mirror benchmark,
  idempotent upsert).


- **✅ Analytics push — simulations upgraded end to end** (4 increments, every branch
  independently reviewed before merge; 189+ tests green; ruff + web gates clean).
  **Core** (quant-ml agent, math-reviewed with numerical probes): rf-aware Sharpe
  (default 4%) + Sortino/Calmar/best-worst-year/beta/alpha + `deflate`; contribution
  **escalation** (calendar anniversaries) + **advisory-fee drag** (portfolio only —
  benchmark stays fee-free so the fee's cost is visible); `core/projection.py` —
  block-bootstrap **Monte Carlo** (percentile bands, goal probability, seeded,
  ~0.3 s per 1000 paths × 30 y) + **withdrawal simulator** (success rate,
  years-lasted). **API** (backend agent): /simulate extensions (end/rebalance/rf/
  inflation/escalation/fee/analytics), /project, /retirement, /frontier,
  /diversification — review caught a **silent 100× unit seam** (retirement rate
  fraction vs percent), fixed with discriminating value tests; response units pinned
  as fractions. **React** (frontend agent): Projection fan chart + goal stat +
  caveat banner, Retirement view, frontier scatter, diversification heatmap/
  clusters/risk bars, dashboard crisis presets + advanced panel + today's-dollars
  mode + drawdown/rolling. **Live validation** exposed + fixed a latent v1 bug:
  optimize comparison specs carried no cash (flat $0 series, all-zero metrics) —
  now a $10k lump + value-locked tests. Screenshots:
  `docs/screenshots/web-{projection,retirement,diversification,optimize-frontier,dashboard-analytics}.png`.
  Also new: `finance-conventions` Skill + quant charter v2 (statistical rigor).

## In progress (superseded by the entry above — kept for the record)

- **Web analytics expansion** (`feat/web-analytics`, frontend-viz) — built against
  the pinned API contract (endpoints may 404 until the backend lands; views are
  loading/error-resilient). Awaiting the parallel backend endpoints + review/merge.
  Touches only `web/`. `npm run build` (tsc) + `npm run lint` clean.
  - **Dashboard**: Advanced options panel (rebalance / risk-free / escalation /
    fee / inflation → today's-dollars view), crisis preset chips (Dot-com, GFC,
    COVID, 2022) using the new `end` field, analytics section (drawdown +
    rolling), all flowing into a spec-inclusive simulate query key.
  - **New views**: Projection (`/projection`, fan chart + goal probability),
    Retirement (`/retirement`, success rate + balance fan), Diversification
    (`/diversification`, heatmap + clusters + risk-contribution bars).
  - **Optimize**: efficient-frontier section (cloud + line + Equal-weight/
    Suggested markers via `extra_points`).
  - New charts: FanChart, DrawdownChart, RollingChart, FrontierChart,
    CorrelationHeatmap, RiskContributionBar. Contract typed verbatim in
    `web/src/api/types.ts` (+ endpoint wrappers + React Query hooks).

## Done

- **✅ Web UI v2 — modern + dynamic, with Compare & Tracking** (agents built in
  parallel worktrees; both branches independently code-reviewed, fixed, merged).
  **Backend** (`feat/api-compare-tracking`, backend-data): `/api/compare` (globally
  aligned shared window; per-portfolio saved schedules; `dropped` surfaced),
  `GET /api/portfolios/{id}/valuations`, `POST .../refresh`; review fix landed at the
  source in `jobs/refresh.py` (price-less holding no longer 500s — also fixes
  Streamlit tracking). **Frontend** (`feat/web-modern-ui`, frontend-viz): Inter +
  design tokens, skeleton shimmer loaders, Framer Motion (staggered entrances,
  count-ups, cross-fades, route transitions; reduced-motion gated), sonner toasts,
  chart legend chips (toggle benchmark/invested), mobile drawer (390px verified),
  real routes `/compare` `/tracking` + the two new views; review fixes: honest
  compare caption (each portfolio keeps its own contribution plan), stale-results
  gating, deep-link login return. **Live validation caught + fixed a real bug:** a
  portfolio holding its own benchmark (SPY vs SPY) crashed refresh/simulate via a
  duplicated price column — deduped in `jobs/refresh.py` + `app/sim_runner.py` with
  regression tests. **125 tests green**, ruff clean, `npm run build`+lint clean;
  Playwright-verified (dashboard light/dark, skeletons, Compare, Tracking, mobile —
  `docs/screenshots/web-*.png`). Streamlit `app/` untouched (verified).

- **✅ Web UI (FastAPI + React) MVP — Google-Finance style** (built by the agent team,
  reviewed, merged). Isolated by directory (Streamlit `app/` untouched — verified):
  **`api/`** = FastAPI over the unchanged `core/`/`data/`/`storage/` with JWT auth +
  per-user isolation (backend-data-engineer; 16 API tests; an independent review fixed
  a prod-secret footgun + NaN-JSON + optimize 4xx mapping). **`web/`** = React + Vite +
  TS + Tailwind SPA (frontend-viz-engineer): **light/dark themes** (toggle, persisted),
  green/red **area growth chart**, sidebar sparklines, KPI grid (all %s time-weighted
  for consistency after review), metrics-vs-benchmark table, new-portfolio + optimize
  views. 110 Python tests green; `npm run build`+lint clean; verified live via
  Playwright (`docs/screenshots/web-*.png`). See [docs/WEB_UI.md](WEB_UI.md).
- **✅ Phase 2 COMPLETE — portfolio optimization (research-first, unbiased)**.
  Stage 2A: ranked survey `docs/OPTIMIZATION_RESEARCH.md` (built-in web research, as
  the paid parallel-cli was unavailable). Gate: user selected 4 allocators + 2
  selectors. Stage 2B: `core/optimization.py` (framework-free) — equal-weight baseline
  + **risk parity (ERC)**, **inverse-volatility**, **min-variance + Ledoit-Wolf
  shrinkage**, **HRP**, plus **low-volatility** and **correlation-clustering**
  selection; long-only/sum-to-1/optional cap; hardened against NaN/flat/non-overlapping
  inputs after an independent review (adds scipy + scikit-learn). Stage 2C:
  `app/views/optimize.py` — Optimize page (Allocate / Select modes) showing suggested
  vs **equal-weight baseline** vs benchmark (reuses `app/sim_runner`); "Use these
  weights" / "Save as portfolio". 93 tests green; verified live
  (`docs/screenshots/optimize.png`).
- **✅ Phase 1.5 COMPLETE — MVP refinements** (4 branches, each tested + merged):
  (A) curated **ticker universe** `data/tickers.csv` (S&P 500 + ETFs) + loader;
  (B) builder **ticker suggestions** (searchable multiselect) + **weight/$-amount
  toggle** + benchmark picker (`weights_from_amounts`); (C) **more recurring
  cadences** (added every 2 / 6 months, ordered shortest→longest via a DateOffset
  generator that supports N-month steps); (D) **Compare 2–3 saved portfolios** —
  shared `app/sim_runner.py` (also refactored the Simulation page onto it), a compare
  view with side-by-side KPIs + one chart + metrics table, aligned to a single global
  window for fairness. 80 tests green; verified live (builder + compare screenshots
  in `docs/screenshots/`). Decisions: curated-list search now / live autocomplete in
  React; persistence still stores weights (amount mode converts).
- **🎉 Phase 1 COMPLETE — local Streamlit + SQLite app is functional & demoable**
  (merged, code-reviewed). Multi-user **auth** (`storage/security.py` bcrypt,
  `storage/auth_service.py`, `app/auth.py` + session gating); **Streamlit UI**
  (`app/streamlit_app.py` + `app/views/{builder,simulation,tracking}.py`,
  `app/charts.py` Plotly): build/save/export/import portfolios, dividend-adjusted
  **growth simulation** vs benchmark (TWR metrics), and a **tracking dashboard**;
  idempotent **refresh job** (`jobs/refresh.py`, also the tracking "Refresh now").
  Verified live via Playwright screenshots (signup → builder → simulation: a 2018
  $1k in AAPL/MSFT/GOOGL → ~$6.2k vs SPY). Independent `/code-review` caught and
  fixed a benchmark-window misalignment + contribution-inflated tracking metric.
  **61 tests green**, ruff clean.
- **Phase 1 · step 4 — storage layer** (merged, code-reviewed): `storage/models.py`
  (users, portfolios, holdings, contributions, daily_valuations; portable types;
  UNIQUE(portfolio_id, as_of_date)), `storage/db.py` (DB-agnostic engine; SQLite FK
  pragma), `storage/repository.py` (**all reads/writes scoped by user_id**; eager
  loading; idempotent benchmark-preserving upsert), `storage/portfolio_io.py` (JSON
  export/import + ORM↔spec), `core/portfolio.py` (PortfolioSpec value objects).
  Alembic initial migration verified (downgrade/upgrade round-trip). An independent
  `/code-review` caught a benchmark-overwrite bug + a detached-instance trap; both
  fixed. 47 tests green.
- **Phase 1 · step 3 — core layer** (merged): `core/simulation.py`
  (`simulate_portfolio`: buy-and-hold + periodic rebalancing, lump-sum + recurring
  DCA, look-ahead-safe; returns value/invested/twr_index using time-weighted return
  so contributions aren't mistaken for gains) and `core/metrics.py` (CAGR, vol,
  Sharpe, max drawdown, total return, summarize). 34 tests green.
- **Phase 1 · step 2 — data layer** (merged): `data/provider.py` (yfinance
  adjusted/total-return wrapper + delisted/non-overlap handling), `data/cache.py`
  (parquet), `data/prices.py` (PriceService). Verified live + 10 offline tests.
- **Dependency note:** dropped **passlib** (1.7.4 is broken with bcrypt 5.0 and is
  unmaintained); auth will hash with the **`bcrypt`** library directly.
- **Phase 1 · step 1 — env scaffold** (branch `feat/env-scaffold`): uv project
  (`pyproject.toml` requires-python >=3.11, `uv.lock` committed), runtime + dev deps,
  layered framework-free skeleton (`data/ core/ storage/ app/ jobs/ tests/`),
  `core/constants.py` (disclaimer + default benchmark), ruff + pytest config (green,
  6 smoke tests), `.env.example` (un-ignored), README run instructions. uv installed
  to `C:\Users\edu_s\.local\bin`.
- **Prompt 2 — four reusable subagents created** in `.claude/agents/`:
  `quant-ml-engineer`, `backend-data-engineer`, `frontend-viz-engineer`,
  `devops-qa-engineer` (all `model: opus`, plan-before-execute, standing
  conventions). Role refinements from `docs/PLAN.md`: quant-ml treats Monte
  Carlo/PCA/forecasting as research-selected candidates (no pre-bias) and gets the
  `Skill` tool for `parallel-deep-research`; auth, client-side save, and
  refresh-vs-cron boundaries made explicit across agents.
- **Prompt 1 — executable plan written** to `docs/PLAN.md` (phased breakdown,
  schema, per-phase DoD/verification). Confirmed this session: Phase 1 = plain
  Streamlit + local SQLite (Supabase deferred to Production); persistence via
  client-side file export/import + optional account save; optimization stays
  unbiased/research-first (no pre-named techniques).
- **Phase 0:** git repo initialized, SSH auth working, first commit pushed to
  `origin/main` (merged with the remote's LICENSE/README).
- Project decision docs written: `docs/ARCHITECTURE.md`, `docs/PROMPTS.md`,
  `docs/AGENT_MODELS.md`.
- Standing conventions added: `CLAUDE.md`, `docs/WORKFLOW.md`, this file,
  `.gitignore`.
- Agent-teams enabled; team model config decided (lead + quant-ml on Opus, others
  on Sonnet; plan-before-execute).
- Tooling policy set (`docs/TOOLING.md`): progressive disclosure; paid/enterprise
  finance plugins (S&P Global/Kensho, anthropics/financial-services, accounting
  `finance`) ruled out of scope for this free-data project.

## Blocked / open questions

- _(none)_

---

### How to use this file
- **Done** — completed, committed units of work.
- **In progress** — exactly what's mid-flight right now (ideally one thing).
- **Next step** — the single concrete next action to take.
- Update it as you go, and commit it alongside the work it describes.
