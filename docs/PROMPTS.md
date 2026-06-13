# Project Prompts

Two ready-to-use prompts for building the investment portfolio simulation &
optimization platform. Both say **"no code yet"** so you stay in control of when
building starts. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full tooling and
phase rationale behind them.

**Run order:** do **Prompt 1 (plan the project)** first, then **Prompt 2 (build
the team)**. Running the plan first lets Claude shape — and improve — the agent
role descriptions based on the real work breakdown, instead of a guessed split.

**Confirmed decisions behind the wording:**
- Agents created as **reusable subagents** in `.claude/agents/` (not an ephemeral team).
- Team of 4: **Quant & ML Engineer · Backend/Data Engineer · Frontend/Viz Engineer · DevOps/QA Engineer** (quant + ML merged).
- **Phase 1 auth:** username + securely hashed password in SQLite; portfolios scoped by `user_id` so each user sees only their own.
- **Phase 2 optimization:** the responsible agent first runs **parallel deep research**, ranks techniques, and presents a summary for you to select before implementing.
- **Phase 1 scope:** historical growth simulation **+** ongoing daily tracking.
- **Stack:** Python, UV, matplotlib (Plotly when interactive), SQLite→PostgreSQL, Streamlit→React.
- **Models:** team **lead and all four teammates on Opus** (max quality); every teammate **plans before executing** (read-only plan mode → lead approval). See [AGENT_MODELS.md](AGENT_MODELS.md) for how model selection works.
- **Version control:** git from day one with a **GitHub remote**; commit small and often; never commit secrets/`.db`/data caches (see `.gitignore`).
- **Resumable workflow:** a standing convention in [../CLAUDE.md](../CLAUDE.md) / [WORKFLOW.md](WORKFLOW.md) — commit often + keep `docs/PROGRESS.md` current + small atomic tasks + the agent-team shared task list — so work survives token/usage interruptions.

---

## Prompt 1 — Plan the whole project across phases

> Paste this to Claude in the project directory **first**.

```text
Produce a detailed, phased IMPLEMENTATION PLAN (no code yet) for an investment
portfolio platform. Research where useful, then give me a plan I can execute
phase by phase. Ask me only the clarifying questions that would materially change
the plan. Where a stated constraint is suboptimal or conflicts with reality, say
so and recommend the pragmatic alternative — don't silently change my constraints.

GOAL
A platform that (a) simulates how money would have grown if invested in chosen US
stocks/ETFs from a chosen past date, (b) lets multiple users save and track their
own portfolios daily vs a benchmark — each user sees only their own — and (c)
eventually suggests optimized long-term portfolios.

TECHNICAL CONSTRAINTS
- Python for all analysis and ML.
- UV as the package manager.
- Visualization: matplotlib by default, Plotly where interactivity is clearly
  better.
- Database: SQLite in Phase 1.
- Auth: username + securely hashed password stored in SQLite; portfolios scoped
  by user_id so users can only ever see their own.
- UI/hosting: Streamlit in Phase 1.
- Keep all finance/ML logic framework-free in a core/ layer so the UI can be
  swapped later without rewriting logic.

PHASES
- Phase 0 (foundations): git repo + a GitHub remote, a .gitignore (exclude
  secrets/.env, the SQLite *.db, and parquet data caches), and the UV-managed
  Python environment. No features yet.
- Phase 1 (local): Streamlit + SQLite. Multi-user login. Users build/save
  portfolios of US stocks. Deliver BOTH: a historical growth simulation ("how
  would my money have grown" from a chosen start date, supporting lump-sum and
  recurring contributions) AND ongoing daily tracking of saved portfolios vs a
  benchmark (e.g. SPY), with metrics (CAGR, volatility, Sharpe, max drawdown).
  Host on Streamlit.
- Phase 2 (optimization): Add a portfolio optimization technique aimed at
  long-term (3-5 yr), low-churn investing. FIRST use the parallel-deep-research
  skill to survey candidate techniques, then present me a RANKED summary (pros/cons and
  fit for long-term investing) so I can SELECT the approach before it is
  implemented. Always include an equal-weight baseline for comparison.
- Final Phase (production): Replace Streamlit with a professional React frontend
  and a Python (FastAPI) backend, migrate SQLite -> PostgreSQL, add real
  multi-user auth, and deploy to a cloud host.

KEY GOTCHAS THE PLAN MUST ADDRESS (see docs/ARCHITECTURE.md sections 6 and 6.5)
- Streamlit Community Cloud has an EPHEMERAL filesystem: a runtime SQLite .db
  (user accounts, saved portfolios) is NOT durable when hosted there. Decide
  consciously: keep Phase 1 multi-user data local, or bring in a hosted Postgres
  (e.g. Supabase) once you want hosted persistence.
- Streamlit can't run a background scheduler. The daily tracking refresh must be
  driven externally (GitHub Actions cron) writing to the same database.
- Streamlit's multi-user/auth model: one process serves all users, per-user state
  lives in st.session_state, SQLite has limited concurrent writes. Hash passwords
  with bcrypt or argon2; scope everything by user_id.
- Secrets: commit a .env.example (no real values); real secrets in .env
  (gitignored) / Streamlit secrets. Never commit credentials.
- Use Alembic for schema migrations (and the SQLite -> PostgreSQL move).
- Backtest integrity: avoid look-ahead and survivorship bias so the historical
  "growth" numbers are credible.

DELIVER IN THE PLAN
1. A recommended project structure (layered data/core/storage/app/jobs/tests).
2. A phase-by-phase breakdown with concrete, ordered steps and the milestone/
   deliverable for each phase.
3. Key technical decisions per phase: libraries, a schema that migrates SQLite ->
   PostgreSQL cleanly, how auth + per-user isolation work, how daily tracking is
   scheduled.
4. How each phase is verified/tested end to end.
5. Cross-cutting concerns: dividend-adjusted prices, data robustness, a "not
   financial advice" disclaimer, and reproducibility.
6. Version control: how the repo + GitHub remote, .gitignore, and a small/frequent
   commit + feature-branch discipline are set up and used throughout.
7. A resumable workflow so the build survives token/context/usage interruptions:
   commit after each meaningful unit, keep docs/PROGRESS.md current
   (Done/In-progress/Next), break work into small atomic tasks, and (in agent
   teams) use the shared task list to persist state across sessions. These are
   standing conventions already recorded in CLAUDE.md and docs/WORKFLOW.md — align
   the plan with them.
8. A clear definition of done / acceptance criteria for each phase, so we know
   when a phase is complete and demoable.

Do not write application code — just the plan. Save the plan to docs/PLAN.md so
the agent-creation step can read it.
```

---

## Prompt 2 — Build the 4-engineer team (reusable subagents)

> Paste this to Claude **after** the plan exists.

```text
I'm building an investment portfolio simulation & optimization platform in Python.
Create FOUR reusable custom subagents as `.claude/agents/*.md` files in this
project. Do NOT write any application code — only the four agent definition files.

FIRST, read docs/ARCHITECTURE.md and the project plan (docs/PLAN.md) in this repo.
Use them to refine the role definitions below: if the plan reveals a better
division of ownership or responsibilities, adjust the agents accordingly and
briefly explain what you changed and why. The four roles below are the starting
point, not a rigid spec.

PROJECT CONTEXT
- The platform: simulate how money would have grown if invested in chosen US
  stocks/ETFs from a past date, let multiple users save and track their own
  portfolios daily vs a benchmark (each user sees only their own), and later
  suggest optimized long-term portfolios.
- Layered, framework-free architecture so the UI can be swapped later without
  rewriting logic:
    data/    yfinance wrapper + parquet cache
    core/    PURE finance/ML logic (simulation, optimization, metrics, montecarlo)
    storage/ SQLAlchemy models (SQLite -> PostgreSQL)
    app/     Streamlit now, React later
    jobs/    scheduled daily refresh
    tests/   pytest
- Tech constraints: Python 3.11+, UV package manager, matplotlib (Plotly when
  interactivity clearly helps), SQLite (Phase 1) -> PostgreSQL (later),
  Streamlit (Phase 1) -> FastAPI + React (later).
- Phases: (1) local Streamlit + SQLite, multi-user login with private portfolios,
  historical growth sim + daily tracking; (2) a portfolio optimization technique;
  (3) a professional React + PostgreSQL web app.

THE 4 AGENTS (starting point — each owns a distinct layer so they rarely touch
the same files):

1. quant-ml-engineer — Quantitative & ML Engineer.
   Owns core/. Historical simulation (lump-sum & recurring contributions),
   metrics (CAGR, volatility, Sharpe, max drawdown, benchmark comparison),
   portfolio optimization, Monte Carlo projections, PCA/correlation-clustering
   diversification, and any forecasting (with honest caveats — never overclaim
   price prediction). For Phase 2 it must use the `parallel-deep-research` skill
   to survey and RANK optimization techniques and present a summary for me to
   choose before implementing. All logic stays framework-free (no Streamlit/React
   imports) so both Streamlit and the future API can reuse it.

2. backend-data-engineer — Backend & Data Engineer.
   Owns data/, storage/, jobs/. yfinance wrapper with parquet caching;
   dividend-adjusted prices; handles delisted/non-overlapping tickers and market
   holidays. SQLAlchemy schema: users (securely hashed passwords), portfolios,
   holdings, daily_valuations — everything scoped by user_id for per-user
   isolation. Idempotent daily refresh job. Schema designed to migrate cleanly
   SQLite -> PostgreSQL.

3. frontend-viz-engineer — Frontend & Visualization Engineer.
   Owns app/ and all charts. Streamlit pages now (login/signup, portfolio
   builder, growth chart, tracking dashboard), React later. matplotlib by
   default, Plotly when interactive. Always calls core/ — never embeds business
   logic in the UI.

4. devops-qa-engineer — DevOps & QA Engineer.
   Owns VERSION CONTROL (git repo, the GitHub remote, .gitignore, branch + commit
   conventions), the UV environment/dependencies, the pytest suite (especially
   core/ finance correctness), ruff linting, GitHub Actions CI, and deployment
   (Streamlit Community Cloud now; Render/Railway + PostgreSQL later). Reviews the
   other agents' output for correctness and reproducibility.

FOR EACH AGENT FILE
- Valid frontmatter: name, a clear description (when to use it), the minimal tools
  it needs (Read, Write, Edit, Bash; add WebSearch for quant-ml-engineer), and the
  model assigned below.
- A detailed system-prompt body: responsibilities, the files/layers it owns, the
  tech constraints above, its boundaries with the other agents, and its quality
  bar.
- Set the frontmatter `model:` field to `opus` for ALL FOUR agents (do NOT use
  "opusplan" — it is not valid for teammates).
- In EVERY agent's system prompt, require it to ALWAYS produce a short plan/
  approach FIRST and wait for the lead's approval before implementing (work in
  read-only plan mode until approved). Plan first, then execute.
- In EVERY agent's system prompt, also require it to follow the standing
  conventions in CLAUDE.md, docs/WORKFLOW.md, and docs/TOOLING.md: read CLAUDE.md
  at the start of a session; commit small and often with clear messages (never
  committing secrets/.db/data caches); update docs/PROGRESS.md (Done/In-progress/
  Next) after each meaningful unit; keep work in small atomic tasks so a token/
  usage interruption loses at most one task; and when reusable domain knowledge or
  a workflow starts repeating, create a Skill for it rather than bloating prompts
  or CLAUDE.md.

Show me all four files (and any role changes you made based on the plan) for
review before finalizing. Write no application code yet.
```

---

## How to use these

1. Run **Prompt 1** to get the executable plan; answer its clarifying questions.
   It saves the plan to `docs/PLAN.md`.
2. Run **Prompt 2** to scaffold the four agents — it reads the plan first and may
   refine the role descriptions to fit it. Review the files, then keep them in
   `.claude/agents/` for the whole project.
3. With plan and agents in place, have each agent build its layer:
   **Backend/Data first** (so `core/` has data to work with), then
   **Quant & ML**, then **Frontend**, with **DevOps/QA** throughout.

Both prompts say "no code yet," so building only starts when you decide.
