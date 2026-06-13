# Implementation Plan — Investment Portfolio Simulation & Optimization Platform

> The executable, phased plan referenced by `CLAUDE.md` and produced by **Prompt 1**
> (`docs/PROMPTS.md`). It turns the settled decisions in `docs/ARCHITECTURE.md`,
> `docs/AGENT_MODELS.md`, `docs/WORKFLOW.md`, and `docs/TOOLING.md` into ordered,
> resumable, demoable phases. **Prompt 2** (agent creation) reads this file.

## Context

We are building a Python investment-portfolio platform that (a) simulates how money
would have grown if invested in chosen US stocks/ETFs from a past date, (b) lets
users save and track their own portfolios vs a benchmark (each user sees only their
own), and (c) eventually suggests optimized long-term portfolios. The architecture,
tooling, and team-model decisions are already settled. Phase 0 (repo + GitHub remote
+ `.gitignore` + UV-managed env decisions) is complete; **no Python code exists yet.**

### Decisions confirmed in this planning session

These shape the phases below and **override** the more granular build order in
`docs/ARCHITECTURE.md §5` where they differ (notably: multi-user auth, saved
portfolios, and daily tracking are bundled **into Phase 1** per the project goal,
rather than deferred to a later phase as §5 sequenced them):

1. **Phase 1 stays on plain Streamlit + local SQLite. No Supabase in Phase 1.**
   Supabase Postgres — and the GitHub Actions daily cron that writes to it — arrive
   only **after the MVP**, in the Production phase. Consequence: the Phase 1
   daily-tracking refresh runs **locally** (a "Refresh now" action plus an optional
   local scheduler), because a CI cron cannot reach a SQLite DB that lives only on
   the local machine / inside the ephemeral Streamlit container.

2. **Persistence is two complementary mechanisms** (primary path chosen because
   Streamlit Community Cloud's filesystem is ephemeral — a server-side `.db` is not
   durable when hosted):
   - **Primary — client-side "save on your computer":** export a portfolio as a
     downloadable file (JSON); re-import later to restore it. Durable on the user's
     own machine, needs no account, survives any Streamlit redeploy.
   - **Secondary — optional "save to account":** when logged in, also persist to our
     server-side SQLite DB. Durable locally; best-effort/ephemeral on Streamlit
     Cloud until the Supabase phase.

3. **Optimization is fully unbiased and research-first.** The `quant-ml-engineer`
   runs `parallel-deep-research`, ranks candidate techniques, and the user **selects**
   before any implementation. This plan deliberately names **no** technique and
   pre-bakes nothing (no pre-decided Monte Carlo / forecasting). An **equal-weight
   baseline** is always implemented for comparison.

### Constraints flagged as suboptimal (with the pragmatic path taken)

- **"Host multi-user on Streamlit" vs ephemeral filesystem.** Hosting Phase 1 on
  Streamlit Community Cloud means server-side accounts/portfolios are **not durable**.
  Pragmatic resolution (per decision 1+2): Phase 1's durable persistence is the
  **client-side export/import** file; a Streamlit Cloud deploy is treated as a
  live demo, and durable hosted accounts wait for Supabase Postgres in the
  Production phase. We do **not** fight the platform with SQLite-durability hacks.
- **Daily cron on Streamlit.** Streamlit can't run a background scheduler, and a CI
  cron can't reach a local SQLite file. So Phase 1 tracking refresh is **local/manual**;
  the **GitHub Actions cron → Supabase** pattern is implemented in the Production
  phase when the DB is reachable from CI.
- **"matplotlib by default."** Kept — but the growth and tracking charts are exactly
  the case where "interactivity is clearly better," so those specific charts use
  **Plotly** (hover, zoom, toggle series); matplotlib/seaborn remain the default for
  static report figures and notebook exploration.

---

## 1. Project structure (layered, framework-free `core/`)

```
ml_project/
  data/            # yfinance wrapper + parquet price cache (source-swappable)
    provider.py    #   thin fetch wrapper; adjusted/total-return prices
    cache.py       #   parquet read/write, "last refreshed" metadata
  core/            # PURE domain logic — NO Streamlit/React/DB imports
    simulation.py  #   historical growth: lump-sum + recurring (DCA)
    metrics.py     #   CAGR, volatility, Sharpe, max drawdown, benchmark compare
    optimization.py#   Phase 2: technique SELECTED via research; + equal-weight baseline
    portfolio.py   #   portfolio value objects, weight/contribution models
  storage/         # SQLAlchemy models + repository (SQLite -> PostgreSQL)
    models.py      #   users, portfolios, holdings, contributions, daily_valuations
    repository.py  #   ALL queries scoped by user_id (per-user isolation)
    db.py          #   engine/session factory (DB-agnostic via SQLAlchemy URL)
    portfolio_io.py#   export/import portfolio <-> JSON (client-side save)
  app/             # Streamlit (thin: auth UI, call core/, render charts)
    auth.py        #   signup/login, bcrypt/argon2, session_state user_id
    pages/         #   builder, growth simulation, tracking dashboard
  jobs/            # scheduled refresh (local in P1; GitHub Actions cron later)
    refresh.py     #   idempotent daily valuation writer (upsert by date)
  migrations/      # Alembic versions (versioned schema; SQLite->Postgres move)
  notebooks/       # exploration (portfolio_theories.ipynb)
  docs/            # ARCHITECTURE, PLAN, PROGRESS, PROMPTS, WORKFLOW, TOOLING
  tests/           # pytest — focused on core/ correctness + isolation
  pyproject.toml   # UV-managed; uv.lock committed
  .env.example     # documents required vars; real .env gitignored
  README.md
```

**Why:** every business rule lives in `core/`, imported by both Streamlit now and
the future FastAPI backend — the UI swap costs no finance-logic rewrite.

---

## 2. Cross-cutting conventions (apply to every phase)

- **Version control.** Git + GitHub remote from day one (done in Phase 0). Feature
  branches per layer (`feat/data-layer`, `feat/core-simulation`, …); merge to `main`
  via PR once green; keep `main` working. Commit small and often with conventional
  messages (`feat: / fix: / chore: / test: / docs: / refactor:`). **Never commit**
  `.env`/secrets, `*.db`/`*.sqlite3`, or parquet caches — verify with `git status`
  before every commit. Auto-checkpoint `Stop` hook is a safety net, not a substitute
  for meaningful commits.
- **Resumable workflow.** Keep `docs/PROGRESS.md` current (Done / In progress / Next
  step — single concrete next action). Break work into small atomic tasks each with a
  clear "definition of done." In agent teams, keep shared-task-list statuses accurate
  so an interruption loses at most one task. On resume: read `PROGRESS.md` + `git log`
  first.
- **Backtest integrity.** Guard against **look-ahead bias** (only use data available
  as of each simulated date) and **survivorship bias** (handle delisted tickers; don't
  silently drop them). These guards live in `data/` + `core/` and are unit-tested.
- **Dividend-adjusted / total-return prices** everywhere growth is computed, so
  returns aren't understated; document the choice in code + README.
- **Data robustness in `data/` only:** delisted tickers, non-overlapping histories,
  market holidays, missing days — handled in the data layer, never in `core/`.
- **Reproducibility.** Pin deps via `uv.lock` + pinned Python; seed any stochastic
  run; cache prices to parquet so runs are repeatable offline.
- **"Not financial advice."** A clear educational-use disclaimer wherever simulations
  or suggestions appear (and in the README).
- **Secrets.** Commit `.env.example` (no values); real secrets in `.env` (gitignored)
  locally / Streamlit secrets when hosted. Rotate anything that leaks.
- **Schema migrations** via **Alembic** from the first model, so the SQLite→Postgres
  move is versioned, not hand-applied.
- **Skills/tooling.** When a formula set (CAGR/Sharpe/drawdown), a rebalancing rule,
  or a recurring data gotcha starts repeating, capture it as a Skill
  (`.claude/skills/<name>/SKILL.md`) instead of bloating prompts/CLAUDE.md. Only
  enable MCP/plugins actually used; paid/enterprise finance plugins remain out of
  scope (`docs/TOOLING.md`).

---

## 3. Data model (designed to migrate SQLite → PostgreSQL cleanly)

SQLAlchemy ORM from day one. Portability rules: integer surrogate PKs; store all
timestamps as **UTC, timezone-aware**; use portable column types (`Integer`,
`String`, `Numeric`/`Float`, `Boolean`, `Date`, `DateTime`, `JSON`) — no
SQLite-only types; all schema changes via Alembic. Every read/write goes through
`storage/repository.py`, which **always filters by `user_id`** (per-user isolation
is enforced in one place, not scattered through the UI).

| Table | Key columns | Notes |
|---|---|---|
| `users` | `id` PK, `username` UNIQUE, `password_hash`, `created_at` | password hashed with **bcrypt or argon2** (passlib); never store plaintext |
| `portfolios` | `id` PK, `user_id` FK→users, `name`, `benchmark_symbol` (default `SPY`), `base_currency` (`USD`), `created_at`, `updated_at` | owner scoping via `user_id` |
| `holdings` | `id` PK, `portfolio_id` FK, `symbol`, `target_weight` | weights validated to sum to 1.0 in `core/` |
| `contributions` | `id` PK, `portfolio_id` FK, `kind` (`lump_sum`/`recurring`), `amount`, `frequency` (e.g. monthly), `start_date`, `end_date` | drives lump-sum + DCA simulation |
| `daily_valuations` | `id` PK, `portfolio_id` FK, `as_of_date`, `market_value`, `benchmark_value` | **UNIQUE(`portfolio_id`,`as_of_date`)** so refresh is idempotent (upsert) |

The same models back SQLite (Phase 1) and Postgres (Production) — only the SQLAlchemy
URL changes. Prices are **not** in this DB; they live in the parquet cache.

---

## 4. Phase-by-phase breakdown

### Phase 0 — Foundations  *(DONE — recap only)*

Git repo + GitHub remote, `.gitignore` (excludes secrets/`.env`, `*.db`, parquet
caches), standing-convention docs, agent-team model config. **Remaining setup deferred
to Phase 1 start:** `uv init`, `pyproject.toml`, pinned Python, `pytest`/`ruff` config,
`.env.example`. **DoD:** repo pushes to `origin/main`; `.gitignore` proven; docs in
place. ✅

---

### Phase 1 — Local Streamlit + SQLite (the MVP)

**Goal:** a logged-in user builds a US-stock/ETF portfolio, runs a historical growth
simulation (lump-sum + recurring), saves it (download file + optional account), and
tracks saved portfolios daily vs a benchmark with metrics — all locally.

**Ordered steps** (each step = a small atomic task + a commit; suggested owner in
brackets):

1. **Env scaffold** [devops-qa]: `uv init`, add deps (pandas, numpy, yfinance,
   SQLAlchemy, alembic, passlib[bcrypt]/argon2, streamlit, plotly, matplotlib, pytest,
   ruff), commit `uv.lock`, configure ruff/pytest, write `.env.example`, README stub +
   disclaimer.
2. **Data layer** [backend-data]: `data/provider.py` (yfinance wrapper, **adjusted/
   total-return** prices) + `data/cache.py` (parquet cache, "last refreshed"). Handle
   delisted/non-overlapping/holidays. Unit-tested with a fixture/sample.
3. **Core simulation** [quant-ml]: `core/simulation.py` — buy-and-hold with periodic
   rebalancing, **lump-sum and recurring (DCA)** contributions, **look-ahead-safe**.
   `core/metrics.py` — CAGR, annualized volatility, Sharpe, max drawdown, benchmark
   comparison (default SPY). Pure functions, hand-verified test cases.
4. **Storage layer** [backend-data]: SQLAlchemy models (§3) + Alembic initial
   migration + `repository.py` with **user_id-scoped** queries + `portfolio_io.py`
   (portfolio ⇄ JSON export/import).
5. **Auth** [backend-data + frontend-viz]: `app/auth.py` — signup/login, password
   hashed with bcrypt/argon2, current `user_id` in `st.session_state`; every page
   gated by login.
6. **Streamlit pages** [frontend-viz] (thin — call `core/`/`repository`, never embed
   logic):
   - **Portfolio builder:** pick tickers + weights + contribution plan; validate.
   - **Save/Restore:** "Export to file" (download JSON) + "Import from file"; optional
     "Save to my account."
   - **Growth simulation:** Plotly growth chart (portfolio vs benchmark) + metrics table.
   - **Tracking dashboard:** saved portfolios' stored valuation history vs benchmark +
     metrics; a **"Refresh now"** button.
7. **Local refresh job** [backend-data]: `jobs/refresh.py` — idempotent (upsert on
   `(portfolio_id, as_of_date)`), skips closed-market days, writes `daily_valuations`.
   Run via the dashboard button and/or local Task Scheduler/APScheduler. (CI cron is
   Production-phase.)
8. **Disclaimer + polish** [frontend-viz]: "Not financial advice" banner on
   simulation/suggestion views; README run instructions.
9. **(Optional) demo deploy** [devops-qa]: deploy to Streamlit Community Cloud as a
   **live demo**, documenting that server-side accounts are ephemeral there and the
   durable save path is the file export.

**Phase 1 verification (end to end):**
- `pytest`: simulation math vs hand-computed cases; metric formulas; look-ahead guard;
  data-layer adjusted-price + delisting handling; `repository` isolation test (user A
  cannot read user B's rows); export→import round-trip equals original.
- `ruff` clean; CI runs tests+lint on push.
- Manual acceptance: create two users → each builds/saves a portfolio → confirm each
  sees only their own → run a lump-sum and a recurring simulation → export, restart
  app, re-import, get identical results → "Refresh now" writes today's valuation and
  is safe to click twice (no duplicate row).

**Phase 1 DoD / acceptance:** two isolated users can register, build, simulate
(lump-sum + DCA), save both ways (file + account), and view a benchmark-relative
tracking dashboard with CAGR/vol/Sharpe/max-drawdown — locally, with green tests/lint
and a working file-based restore.

---

### Phase 2 — Portfolio optimization (research-first, **unbiased**)

**Goal:** add a long-term (3–5 yr), low-churn optimization suggestion — with the
technique chosen by evidence, not assumption.

**Ordered steps:**
1. **Research** [quant-ml]: run the **`parallel-deep-research`** skill to survey
   candidate optimization techniques for long-term, low-turnover investing. Produce a
   **ranked summary** (pros/cons, fit, data/assumption requirements, turnover behavior)
   saved to `docs/`. **No technique is pre-selected; avoid bias of any kind.**
2. **User selection** [lead + user]: present the ranked summary; **user selects** the
   approach before any implementation.
3. **Baseline first** [quant-ml]: implement the **equal-weight baseline** in
   `core/optimization.py`.
4. **Selected technique** [quant-ml]: implement the chosen method framework-free;
   constraints favor low churn; weights validated (sum to 1, bounds respected).
5. **Comparison view** [frontend-viz]: a Streamlit page comparing selected-vs-baseline
   suggested weights, then feeding suggested weights straight into the Phase 1
   simulation for an apples-to-apples growth/metrics comparison. Disclaimer present.

**Phase 2 verification:** ranked-summary doc + recorded user selection exist; tests
assert weights are valid and the low-churn constraint holds; baseline always shown;
the suggestion is reproducible (seeded, cached data) and flows into the existing
simulation/metrics without special-casing.

**Phase 2 DoD / acceptance:** user picked the technique from an unbiased ranked survey;
the app shows selected-vs-equal-weight suggestions and their simulated growth/metrics;
results are reproducible and caveated as not financial advice.

---

### Final Phase — Production (FastAPI + React + Postgres, hosted)

**Goal:** professional stack with durable hosted multi-user data and automated daily
tracking.

**Ordered steps:**
1. **Backend** [backend-data + devops-qa]: extract a **FastAPI** service that calls the
   **unchanged `core/`**; REST endpoints for auth, portfolios, simulation, tracking,
   suggestions.
2. **Real auth** [backend-data]: token/session auth (e.g. JWT), proper signup/login,
   password reset; still `user_id`-scoped.
3. **DB migration** [backend-data + devops-qa]: stand up **Supabase Postgres**; run the
   **Alembic** migrations against it; verify a SQLite→Postgres data move on a copy.
   Switch the SQLAlchemy URL — no model rewrite.
4. **Scheduled tracking** [devops-qa]: **GitHub Actions cron** runs `jobs/refresh.py`
   against the **reachable Supabase DB** (idempotent upserts; "last refreshed" stored).
   This is the point at which the CI-cron pattern from ARCHITECTURE.md becomes viable.
5. **React frontend** [frontend-viz]: rebuild the UI in React against the FastAPI API;
   Plotly for interactive charts; same disclaimers.
6. **Deploy** [devops-qa]: host API + frontend (Render/Railway) + Supabase; secrets via
   host config; CI gates deploys.

**Final-phase verification:** API contract + auth tests; Alembic migration verified on a
DB copy; cron job proven idempotent (re-run yields no duplicate valuations); deploy
smoke test (register → build → simulate → track in the hosted app); per-user isolation
re-verified over the API.

**Final-phase DoD / acceptance:** hosted React+FastAPI+Postgres app with durable
multi-user accounts, automated daily tracking via CI cron, and all Phase 1/2 features
working against the production DB — each user still sees only their own data.

---

## 5. Team / ownership mapping (for Prompt 2)

| Layer | Owner |
|---|---|
| `data/`, `storage/`, `jobs/`, schema/migrations | **backend-data-engineer** |
| `core/` (simulation, metrics, optimization, any analytics) | **quant-ml-engineer** |
| `app/` + all charts | **frontend-viz-engineer** |
| VC, UV env, pytest, ruff, CI, deploy, reviews | **devops-qa-engineer** |

**Build order:** backend/data first (so `core/` has data) → quant/core → frontend →
devops/QA throughout. All on Opus; each plans before executing (read-only plan mode →
lead approval).

---

## 6. Verification summary (how we know a phase is "done")

Each phase is independently demoable and gated by: green `pytest` (core correctness +
user isolation), clean `ruff`, CI passing on push, an updated `docs/PROGRESS.md`, and
the phase's manual acceptance checklist above. Look-ahead/survivorship guards and the
export→import round-trip are explicit test cases, because credible "how would my money
have grown" numbers are the whole point.
