# Investment Portfolio Simulation & Optimization Platform
## Tools, Frameworks & Approach — Decision Guide

> **Status:** Decision record fed to the build agents. It states the **finalized
> decisions** and the **non-obvious considerations** — deliberately *without*
> pre-selecting optimization or analytics techniques, so the research the agents
> do in those areas isn't biased.

---

## 1. Feasibility verdict

**Yes — fully feasible with free/open-source tools and free market data.** The
three core features sit on a gentle difficulty ramp:

| Feature | Difficulty | Why |
|---|---|---|
| "How would my money have grown" (historical sim) | Easy | Fetch prices + pandas arithmetic |
| Daily performance tracking | Moderate | Needs a data store + a scheduled refresh |
| Portfolio construction / optimization suggestions | Moderate | Solved by mature libraries — you won't write the math from scratch |

This is also a strong recruiter portfolio piece: it shows data skills,
quantitative finance, and (in later phases) full-stack software engineering.

---

## 2. Finalized decisions

- **UI:** Streamlit first, then split into FastAPI + React later.
- **Tracking:** Persisted + scheduled (DB + daily job).
- **First milestone:** Historical growth simulation.
- **Asset universe:** **US stocks/ETFs only** → yfinance is a clean fit; FX/global
  complexity avoided for now.
- **Users:** **Single-user now, multi-user later** → design the DB schema with a
  forward-compatible `user` concept so adding accounts later is cheap.
- **ML emphasis:** **Balanced** — a solid analytics core plus **one
  carefully-caveated** forecasting feature; specific techniques are chosen during
  the build (researched, not pre-listed).

---

## 3. Decision areas

### A. Language & packaging

**Decision: Python 3.11+**, managed with **`uv`** (environment + package manager).
Commit `uv.lock`; pin the Python version; one environment per project.

---

### B. Market data source

**Decision: `yfinance`** (free, no key; US stocks/ETFs, decades of daily history,
dividends/splits) behind a **thin wrapper** so the source can be swapped later
without touching business logic. Cache downloaded prices to **parquet** to reduce
calls and survive outages.

**Considerations (important):**
- Use **dividend-adjusted / total-return** prices, or growth will be understated.
- Handle **delisted tickers**, **non-overlapping histories**, market holidays.
- Respect each provider's **terms of use**, especially before any public deploy
  (Yahoo data redistribution is a grey area — fine for a personal demo, read the
  terms before commercializing).

---

### C. Portfolio optimization

**Not pre-decided here — on purpose.** The Phase 2 optimization **library and
technique** are intentionally left open so the choice isn't biased: the
`quant-ml-engineer` runs **parallel deep research**, ranks the candidates, and
presents a summary for the user to **select** before implementing (see
`docs/PROMPTS.md` Prompt 1, Phase 2). Compare any suggestion against a simple
baseline.

---

### D. Historical simulation / backtesting approach

**Decision: plain pandas/numpy.** The use case is buy-and-hold with periodic
rebalancing — simple, transparent arithmetic that's easy to test. Reach for a
dedicated engine (`vectorbt`/`bt`) only if you later want heavy multi-strategy
backtesting.

**Considerations:** support both **lump-sum** and **recurring contributions**
(dollar-cost averaging); compute against a **benchmark** (e.g. SPY).

---

### E. Numerics & analysis

- **pandas + numpy** — the backbone.
- **scipy / statsmodels** — stats when needed.
- **scikit-learn** — ML/analytics when needed.

---

### F. Visualization

**Decision: matplotlib by default; Plotly where interactivity clearly helps**
(e.g. interactive charts in the app). matplotlib/seaborn for notebook exploration.

---

### G. UI / delivery layer

**Decision: Streamlit now → FastAPI + React later.** Build the MVP in Streamlit to
validate the finance logic fast, then extract a FastAPI backend + React frontend
to demonstrate engineering breadth. The framework-free `core/` (see §4) keeps that
split cheap.

**Considerations:** never put business logic in Streamlit callbacks — keep it in
`core/` so both Streamlit and the future API call the same code.

---

### H. Storage / database

**Decision: SQLite via SQLAlchemy** now → **migrate to PostgreSQL** when you
deploy / add the API. Cache raw prices as **parquet**, separate from the
transactional DB. Using SQLAlchemy from day one makes the SQLite→Postgres move
nearly free.

**Considerations:** model `portfolios`, `holdings`, and `daily_valuations` cleanly
(with a forward-compatible `user` column so multi-user is cheap later); daily data
volume is tiny — don't over-engineer with a time-series DB.

---

### I. Scheduling (daily performance tracking)

**Decision: GitHub Actions cron** (or APScheduler if always-on) for the daily
price pull + valuation write.

**Considerations:** make the job **idempotent** (safe to re-run); handle days the
market is closed; store a "last refreshed" timestamp.

---

### J. ML / advanced analytics

**Not pre-listed here — on purpose.** Specific analytics techniques are
researched/chosen during the build rather than prescribed up front, so the choice
isn't biased. **Guardrail:** never overclaim price prediction — present any
forecast as a distribution / uncertainty band, not a point prediction.

---

### K. Deployment / hosting

**Decision: Streamlit Community Cloud (or Hugging Face Spaces) for the MVP;
Render/Railway** when it becomes a FastAPI + React app with Postgres. (See §6.5 for
the Streamlit persistence gotcha.)

---

### L. Dev tooling

- **Version control:** Git + GitHub from day one. A clean commit history and
  README are themselves recruiter signals.
- **Testing:** `pytest` — especially for `core/` finance logic.
- **Formatting/lint:** `ruff` (fast, all-in-one).
- **CI:** GitHub Actions to run tests/lint on push.
- **Types:** optional `mypy` on `core/` for an extra quality signal.

---

## 4. Recommended project structure

Layered so the Streamlit→FastAPI split later is painless. **All business logic
lives in a framework-free `core/`** that both the UI and the future API import.

```
ml_project/
  data/            # price fetching + caching (yfinance wrapper, parquet cache)
  core/            # PURE domain logic — no UI, no framework imports
    simulation.py  # historical growth: lump-sum & recurring contributions
    optimization.py# portfolio optimization (library + technique chosen in Phase 2)
    analytics.py   # forward projections / diversification (techniques TBD, later)
    metrics.py     # CAGR, volatility, Sharpe, max drawdown vs benchmark
  storage/         # SQLAlchemy models + repository (SQLite -> Postgres)
  app/             # Streamlit pages (thin: call core/, render charts)
  jobs/            # scheduled daily refresh (GitHub Actions / APScheduler)
  notebooks/       # exploration (portfolio_theories.ipynb lives here)
  docs/            # this guide and future design notes
  tests/           # pytest, focused on core/
  pyproject.toml
  README.md
```

**Why this shape:** when you add FastAPI later, endpoints just call `core/` — the
same code Streamlit already uses. No rewrite of finance logic.

---

## 5. Recommended build order

Each phase is independently demoable.

1. **Phase 0 — Foundations.** `git init` + GitHub remote, `uv` env +
   `pyproject.toml`, `.gitignore`, README, `pytest` set up. (No real features yet.)
2. **Phase 1 — Historical growth simulation (first milestone).**
   `data/` fetcher + parquet cache → `core/simulation.py` (lump-sum + recurring)
   → `core/metrics.py` (CAGR, vol, Sharpe, drawdown, benchmark vs SPY) →
   Streamlit page with a growth chart + metrics table.
3. **Phase 2 — Optimization & suggestions.** `core/optimization.py` (technique
   selected via Phase 2 research) + a comparison view; a Streamlit page that feeds
   suggested weights straight into the Phase 1 sim.
4. **Phase 3 — Persisted portfolios + daily tracking.** `storage/` schema
   (portfolios, holdings, daily_valuations) + `jobs/` scheduled daily refresh;
   dashboard reads stored history.
5. **Phase 4 — Advanced analytics.** Forward projections, diversification
   analysis, and one caveated forecasting feature (techniques chosen during the
   build).
6. **Phase 5 — Split the stack.** Extract `core/` behind a FastAPI REST API;
   build a React frontend; migrate to Postgres; add multi-user auth; deploy to
   Render/Railway.

---

## 6. Cross-cutting considerations

- **Not financial advice.** Add a clear educational-use disclaimer everywhere
  suggestions appear.
- **Dividends matter.** Use adjusted/total-return prices so growth isn't
  understated; document the choice.
- **Data robustness.** Delisted tickers, non-overlapping histories, currency
  differences, and holidays belong in the `data/` layer, not `core/`.
- **Reproducibility.** Pin dependencies; seed stochastic runs; cache data.
- **Data licensing.** Re-read provider terms before any public/commercial deploy.
- **Honesty about ML.** Don't claim to predict prices; present projections as
  probability distributions.
- **Secrets management.** Commit a `.env.example` documenting required variables
  (no real values); keep real secrets in `.env` (gitignored) locally and in
  Streamlit secrets when hosted. Never commit credentials or the password salt.
- **Schema migrations.** Use **Alembic** so schema changes — and the eventual
  SQLite→PostgreSQL move — are versioned and repeatable, not hand-applied.
- **Backtest integrity.** Guard the historical simulation against **look-ahead
  bias** (only use data available as of each date) and **survivorship bias**
  (delisted tickers). Credible "how would my money have grown" numbers are a
  recruiter signal; silently wrong ones are a liability.

---

## 6.5 Phase 1 hosting & persistence gotchas (important)

These shape whether Phase 1's "multi-user, hosted on Streamlit" goal is fully
achievable as stated. Decide the trade-off consciously.

- **⚠️ Streamlit Community Cloud has an ephemeral filesystem.** Files written at
  runtime — including the **SQLite `.db` holding user accounts and saved
  portfolios** — are *not durable*; a restart/redeploy can wipe them. This works
  perfectly **locally**, but a *hosted* multi-user app needs a **hosted database
  (e.g., Supabase Postgres) earlier than Phase 5**. Practical options: (a) keep
  Phase 1 truly local for real multi-user data, treating any Streamlit Cloud
  deploy as a single-user/demo; or (b) bring in a hosted Postgres (Supabase) as
  soon as you want hosted persistence.
- **No background scheduler on Streamlit.** A Streamlit app only runs while
  serving a browser session, so it can't run the daily tracking refresh itself.
  Drive it **externally via GitHub Actions cron**, which writes valuations to the
  database — and that job must reach the *same* DB (reinforcing the hosted-DB
  point above).
- **Streamlit's multi-user/auth model is unusual.** One process serves all users;
  per-user state lives in `st.session_state` per browser session, and SQLite has
  limited concurrent-write support. Roll auth carefully: hash passwords with
  **bcrypt or argon2**, keep portfolios scoped by `user_id`, and expect this to be
  a real reason to move to FastAPI + React for robust multi-user later.

---

## 7. Recommended default stack (one-glance summary)

| Layer | Pick | Note |
|---|---|---|
| Language | Python 3.11+ | — |
| Env/packaging | uv | commit `uv.lock` |
| Market data | yfinance (wrapped) | parquet cache; swap-able |
| Simulation | plain pandas | — |
| Charts | matplotlib (Plotly when interactive) | — |
| UI (now) | Streamlit | — |
| UI (later) | FastAPI + React | — |
| Storage | SQLite → PostgreSQL | parquet for prices |
| Scheduling | GitHub Actions cron | APScheduler if always-on |
| Hosting | Streamlit Cloud now → Render/Railway later | — |
| Dev tooling | Git, pytest, ruff, GH Actions CI | mypy optional |

> Optimization library/technique and the advanced-analytics methods are
> intentionally **omitted** here — they're researched and chosen during the build
> (see §3C and §3J).

---

> Scope questions are settled (see §2). Phase 0 (repo + `uv` skeleton) is done; the
> next step is generating the executable plan (`docs/PLAN.md`) via Prompt 1.
