# Investment Portfolio Simulation & Optimization Platform
## Tools, Frameworks & Approach — Decision Guide

> **Status:** Decision/research document. **No application code is written yet.**
> This file compares the options for each part of the stack (with pros/cons and
> considerations), recommends a default, proposes a project structure, and lays
> out the order in which to build. Use it to lock in choices before any coding.

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
- **Users:** **Single-user now, multi-user later** → no auth yet, but design the
  DB schema with a nullable/forward-compatible `user` concept so adding accounts
  later is cheap.
- **ML emphasis:** **Balanced** → solid analytics core (Monte Carlo, efficient
  frontier, PCA/clustering) plus **one carefully-caveated** forecasting feature.

The remaining sections list alternatives too, so choices can still be revisited.

---

## 3. Decision areas

Each subsection: the options, pros/cons, a recommendation, and considerations.

### A. Language & packaging

| Option | Pros | Cons |
|---|---|---|
| **Python** | Best ecosystem for finance/ML; plays to your strengths | Slower than compiled langs (irrelevant here) |
| R | Strong stats/finance packages | Weaker for web apps / production services |
| JS/TS only | One language across stack | Poor quant/ML libraries |

**Recommendation: Python 3.11+.**

Packaging/env manager:
- **`venv` + `requirements.txt`** — simplest, universally understood. *Best for learning.*
- **`uv`** — very fast, modern, increasingly standard. *Good "I know current tooling" signal.*
- **Poetry** — robust dependency resolution + lockfile. *Slightly heavier.*

**Recommendation:** `venv`+`requirements.txt` to start, or `uv` if you want to
show modern tooling. Pin versions for reproducibility either way.

**Considerations:** keep a lockfile; document Python version; one virtual env per
project.

---

### B. Market data source

| Option | Cost | Coverage | Notes |
|---|---|---|---|
| **`yfinance`** | Free, no key | Global stocks/ETFs, decades of daily data, dividends/splits | Unofficial Yahoo scraper — can break; rate-limit yourself |
| **Tiingo** | Free tier + paid | US equities/ETFs, good quality | Needs API key; clean adjusted data |
| **Financial Modeling Prep** | Free tier + paid | Prices + fundamentals | Key required |
| **Alpha Vantage** | Free tier (tight limits) | Global | 5 calls/min on free tier |
| **Polygon.io** | Free tier + paid | High quality, real-time options | Best reliability when you scale |
| **EOD Historical Data** | Paid (cheap) | Very broad global | Good if you need many exchanges |

**Recommendation:** **`yfinance`** for v1, **hidden behind a thin wrapper** so the
source can be swapped later without touching business logic. Cache downloaded
prices locally (parquet) to reduce calls and survive outages.

**Considerations (important):**
- Use **dividend-adjusted / total-return** prices, or growth will be understated.
- Handle **delisted tickers**, **non-overlapping histories**, market holidays.
- Respect each provider's **terms of use**, especially before any public deploy
  (Yahoo data redistribution is a grey area — fine for a personal demo, read the
  terms before commercializing).

---

### C. Portfolio optimization library

| Option | Pros | Cons |
|---|---|---|
| **PyPortfolioOpt** | Purpose-built, well-documented; covers mean-variance, max-Sharpe, min-vol, efficient frontier, **HRP**, Black-Litterman | Less exotic than riskfolio |
| **riskfolio-lib** | Many risk measures, advanced models | Steeper learning curve; more than you need now |
| **Hand-rolled (numpy/cvxpy)** | Max learning, full control | Reinventing solved problems; error-prone |

**Recommendation: PyPortfolioOpt.** It maps exactly onto your "well-known but not
complicated" brief.

**Techniques that fit "simple + long-term + low-churn":**

| Technique | What it does | Why it fits long-term investing |
|---|---|---|
| Equal-weight (1/N) | Same weight to each asset | Robust baseline; no estimation error; trivial to explain |
| Max-Sharpe (Markowitz) | Best risk-adjusted return | Classic, recruiter-recognizable |
| Min-volatility | Lowest-risk portfolio | Good for conservative long-horizon |
| Risk parity | Equal risk contribution per asset | Diversification-focused |
| **Hierarchical Risk Parity (HRP)** | Clusters correlated assets, allocates by risk | Modern, robust to estimation error, great recruiter signal |
| Black-Litterman | Blends market equilibrium with your views | Optional, more advanced |

**Considerations:** default to **annual or quarterly rebalancing**, not daily —
this directly honors the "avoid constant buying/selling" goal. Always show an
equal-weight baseline so users see whether optimization actually helped.

---

### D. Historical simulation / backtesting approach

| Option | Pros | Cons |
|---|---|---|
| **Plain pandas/numpy** | Full control, transparent, easy to test, no magic | You write the accounting (contributions, rebalancing) |
| **bt** | Tree-based backtests, clean API | Another dependency to learn |
| **vectorbt** | Very fast, vectorized, rich analytics | Steep API; overkill for buy-and-hold |
| **backtrader** | Mature, event-driven | Geared to active trading, heavier |

**Recommendation:** **plain pandas** for the historical-growth simulation. Your
use case is buy-and-hold with periodic rebalancing, which is simple arithmetic —
a dedicated backtesting engine adds complexity you don't need, and rolling your
own is more transparent and more testable. Reach for `vectorbt`/`bt` only if you
later want heavy multi-strategy backtesting.

**Considerations:** support both **lump-sum** and **recurring contributions**
(dollar-cost averaging); compute against a **benchmark** (e.g. SPY).

---

### E. Numerics & analysis

- **pandas + numpy** — the backbone. Non-negotiable.
- **scipy / statsmodels** — for stats (regressions, distributions) in analytics.
- **scikit-learn** — PCA, clustering, any ML.

**Recommendation:** pandas/numpy core; add scikit-learn when you reach analytics.

---

### F. Visualization

| Option | Pros | Cons |
|---|---|---|
| **Plotly** | Interactive, web-ready, integrates with Streamlit/React | Larger payloads |
| **matplotlib/seaborn** | Great for notebooks/static analysis | Not interactive for web |
| Altair | Declarative, clean | Smaller ecosystem |

**Recommendation:** **Plotly** for the app (interactive growth charts, efficient
frontier); **matplotlib/seaborn** for notebook exploration.

---

### G. UI / delivery layer (the biggest fork)

| Option | Pros | Cons | Recruiter signal |
|---|---|---|---|
| **Streamlit** | Fastest to build, pure Python, free hosting, ideal for data apps | Less control over UX; not "real" web eng | Data/analytics |
| Dash (Plotly) | More layout control, still Python | More boilerplate than Streamlit | Data + some web |
| Gradio | Trivial ML demos | Too limited for a multi-page product | ML demos |
| **FastAPI + React** | Production-grade, full separation, scalable | Much more work; two languages | Full-stack eng |

**Recommendation:** **Streamlit now, split to FastAPI + React later.** Build the
MVP in Streamlit to validate the finance logic fast, then extract a FastAPI
backend + React frontend to demonstrate engineering breadth. The architecture in
§4 keeps this split cheap by isolating all logic in a framework-free `core/`.

**Considerations:** never put business logic in Streamlit callbacks — keep it in
`core/` so both Streamlit and the future API call the same code.

---

### H. Storage / database

| Option | Pros | Cons |
|---|---|---|
| **SQLite** | Zero-config, file-based, perfect for dev/MVP | Single-writer; not for high concurrency |
| **PostgreSQL** | Production-grade, concurrent, time-series friendly | Needs a server/hosting |
| Parquet files | Great for cached price data | Not for transactional/user data |
| Time-series DB (TimescaleDB/InfluxDB) | Optimized for many ticks | Overkill for daily data |

**Recommendation:** **SQLite via SQLAlchemy** for phase 1, **migrate to
PostgreSQL** when you deploy / add the API. Cache raw prices as **parquet**
separately from the transactional DB. Using SQLAlchemy from day one makes the
SQLite→Postgres move nearly free.

**Considerations:** model `portfolios`, `holdings`, and `daily_valuations`
cleanly (with a forward-compatible `user` column so multi-user is cheap later);
daily data volume is tiny so don't over-engineer with a TSDB.

---

### I. Scheduling (daily performance tracking)

| Option | Pros | Cons |
|---|---|---|
| **APScheduler** | In-process Python scheduler, simple | Runs only while your app/process runs |
| **GitHub Actions cron** | Free, serverless, no infra | Coupled to GitHub; not for secrets-heavy jobs |
| OS cron / Task Scheduler | Built in | Machine must be on |
| Airflow / Prefect | Powerful orchestration | Massive overkill here |

**Recommendation:** **GitHub Actions cron** (or APScheduler if always-on) for the
daily price pull + valuation write. Avoid Airflow — way too heavy for one daily
job.

**Considerations:** make the job **idempotent** (safe to re-run); handle days the
market is closed; store a "last refreshed" timestamp.

---

### J. ML / advanced analytics (the recruiter differentiator)

Options, roughly easy→ambitious:

| Technique | Value | Honesty note |
|---|---|---|
| **Monte Carlo forward projection** | Projects future growth with confidence bands; pairs naturally with historical sim | Communicate it as a distribution, not a prediction |
| Efficient frontier visualization | Classic, visually impressive | Standard, low risk |
| PCA / correlation clustering | Quantifies diversification; explains HRP | Strong analytics signal |
| Regime detection (e.g. HMM) | "Sophisticated" angle | Don't oversell |
| Return/volatility forecasting (ML) | Eye-catching | **Price prediction is genuinely hard** — framing the limits honestly is itself a maturity signal recruiters respect |

**Recommendation (balanced):** build a solid analytics core — **Monte Carlo
projection** + **efficient frontier** + **PCA/clustering diversification** — plus
**one** carefully-caveated forecasting feature. Overclaiming predictive power is a
red flag to knowledgeable reviewers.

---

### K. Deployment / hosting

| Option | Cost | Best for |
|---|---|---|
| **Streamlit Community Cloud** | Free | The Streamlit MVP |
| **Hugging Face Spaces** | Free | Streamlit/Gradio demos, ML-flavored audience |
| Render / Railway / Fly.io | Free–cheap | FastAPI + React + Postgres later |
| AWS/GCP/Azure | Pay-as-you-go | Production scale (overkill early) |

**Recommendation:** **Streamlit Community Cloud** or **HF Spaces** for the MVP;
**Render/Railway** when it becomes a FastAPI+React app with Postgres.

---

### L. Dev tooling

- **Version control:** Git + GitHub from day one (this project isn't a git repo
  yet — initializing it is the natural first step). A clean commit history and
  README are themselves recruiter signals.
- **Testing:** `pytest` — especially for `core/` finance logic.
- **Formatting/lint:** `ruff` (fast, all-in-one) + optionally `black`.
- **CI:** GitHub Actions to run tests/lint on push (shows engineering maturity).
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
    optimization.py# PyPortfolioOpt wrappers (equal-wt, max-Sharpe, min-vol, HRP)
    montecarlo.py  # forward projection with confidence bands (later)
    metrics.py     # CAGR, volatility, Sharpe, max drawdown vs benchmark
  storage/         # SQLAlchemy models + repository (SQLite -> Postgres)
  app/             # Streamlit pages (thin: call core/, render Plotly)
  jobs/            # scheduled daily refresh (GitHub Actions / APScheduler)
  notebooks/       # exploration (portfolio_theories.ipynb lives here)
  docs/            # this guide and future design notes
  tests/           # pytest, focused on core/
  requirements.txt
  README.md
```

**Why this shape:** when you add FastAPI later, endpoints just call `core/` — the
same code Streamlit already uses. No rewrite of finance logic.

---

## 5. Recommended build order

Each phase is independently demoable.

1. **Phase 0 — Foundations.** `git init`, repo skeleton, virtual env,
   `requirements.txt`, README, `pytest` set up. (No real features yet.)
2. **Phase 1 — Historical growth simulation (first milestone).**
   `data/` fetcher + parquet cache → `core/simulation.py` (lump-sum + recurring)
   → `core/metrics.py` (CAGR, vol, Sharpe, drawdown, benchmark vs SPY) →
   Streamlit page with a Plotly growth chart + metrics table.
3. **Phase 2 — Optimization & suggestions.** `core/optimization.py`
   (equal-weight, max-Sharpe, min-vol, HRP) + efficient-frontier plot; a
   Streamlit page that feeds suggested weights straight into the Phase 1 sim.
4. **Phase 3 — Persisted portfolios + daily tracking.** `storage/` schema
   (portfolios, holdings, daily_valuations) + `jobs/` scheduled daily refresh;
   dashboard reads stored history.
5. **Phase 4 — Advanced analytics.** Monte Carlo projection with confidence
   bands; PCA/correlation-clustering diversification view; one caveated
   forecasting feature.
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
- **Reproducibility.** Pin dependencies; seed Monte Carlo runs; cache data.
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

| Layer | Default pick | Main alternative |
|---|---|---|
| Language | Python 3.11+ | — |
| Env/packaging | venv + requirements.txt | uv |
| Market data | yfinance (wrapped) | Tiingo / Polygon |
| Optimization | PyPortfolioOpt | riskfolio-lib |
| Simulation | plain pandas | vectorbt / bt |
| ML/analytics | scikit-learn + Monte Carlo | statsmodels |
| Charts | Plotly | matplotlib/seaborn |
| UI (now) | Streamlit | Dash |
| UI (later) | FastAPI + React | — |
| Storage | SQLite → PostgreSQL | parquet for prices |
| Scheduling | GitHub Actions cron | APScheduler |
| Hosting | Streamlit Cloud / HF Spaces | Render / Railway |
| Dev tooling | Git, pytest, ruff, GH Actions CI | mypy |

---

## 8. Remaining minor question

- Packaging: `venv` (simple) vs `uv` (modern signal)? — can be decided at Phase 0.

> The scope questions are settled (see §2). The next step, when ready, is Phase 0
> (repo + skeleton) — a separate go-ahead. No application code has been written.
