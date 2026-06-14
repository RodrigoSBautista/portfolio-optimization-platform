# Phase 2 — Portfolio Optimization (research-first, unbiased)

> Project reference for the Phase 2 build. The defining rule (from
> [ARCHITECTURE.md](ARCHITECTURE.md) §3C and [PLAN.md](PLAN.md) §4 Phase 2): the
> optimization technique is **chosen by evidence, not assumption** — research and
> rank candidates first, the **user selects**, and only then implement. An
> **equal-weight baseline is always implemented** for comparison. This doc names **no**
> technique on purpose; it fixes the *process*, constraints, and integration.

## Confirmed decisions (2026-06-14)

- **Both optimizer modes:**
  1. **Allocate** — suggest weights for a ticker set the user chooses.
  2. **Select** — also pick *which* tickers from a candidate universe, plus weights.

  Both are always compared against an equal-weight baseline.
- **Research via the `parallel-deep-research` skill** (thorough, multi-source, ranked).
- **Solo build + an independent `/code-review`** on each feature branch (Phase 1
  workflow). Full agent team not required — the research skill already parallelizes.
- **Constraints** (defaults; refined after the technique is selected): long-only,
  weights sum to 1, optional max-weight cap, low-churn/turnover aware,
  look-ahead-safe (only the chosen lookback window), reproducible (seeded).

## Stage 2A — Unbiased technique research ▶ first, and a hard gate

- Run `parallel-deep-research` to survey portfolio-construction techniques suited to
  **long-term (3–5 yr), low-turnover, long-only retail** investing, covering **both**
  sub-problems: **allocation** (weighting a fixed set) and **selection** (choosing
  assets from a universe).
- Deliverable: **`docs/OPTIMIZATION_RESEARCH.md`** — a **ranked** summary; per
  candidate: how it works (plain language), pros/cons, data/assumption needs,
  **turnover/churn behavior**, complexity, allocation vs selection fit, and data-layer
  needs. Ranking criteria stated transparently; **no pre-favored method**.
- **GATE:** present the ranked summary; the **user selects** the technique(s) before
  any code is written. Record the choice in [PROGRESS.md](PROGRESS.md).

## Stage 2B — Core optimization (`feat/optimization-core`, after selection)

- `core/optimization.py` — framework-free (pandas/numpy; scipy/scikit-learn only if
  needed); no Streamlit/DB imports.
  - `equal_weight(tickers)` — always-present baseline.
  - `optimize_allocation(returns, *, max_weight=None, …)` — selected allocation method.
  - `select_portfolio(returns_universe, *, k=None, …)` — selected selection method
    (subset ≤ k + weights).
  - Inputs are returns/price DataFrames from `data/`; reuse `core/metrics.py`;
    look-ahead-safe; seeded.
- Tests: valid/long-only/capped weights, baseline correctness, selection size ≤ k,
  determinism, and a stability/low-churn check appropriate to the chosen method.

## Stage 2C — Optimize page + integration (`feat/optimize-ui`)

- `app/views/optimize.py` with an **Allocate / Select** toggle.
  - Pick tickers via the existing `data.tickers` searchable multiselect; choose a
    lookback window + constraints (max weight, k).
  - Show **suggested weights vs equal-weight** (table + a weights bar chart).
  - Build `PortfolioSpec`s and run suggested + equal-weight through the existing
    `app/sim_runner.run_simulation` to compare vs the benchmark on one growth chart +
    metrics table (reuse `app/charts.py` + `format_metrics`).
  - "Use these weights" → `st.session_state['current_spec']`; "Save as portfolio" →
    `Repository.save_portfolio`.
- Add a `weights_bar(...)` helper to `app/charts.py`; add "🧮 Optimize" to the sidebar
  nav in `app/streamlit_app.py`. Disclaimer on the page.

## Cross-cutting

- **Unbiased:** no technique named in code/UI until selected; equal-weight baseline
  always shown alongside any suggestion.
- Framework-free core preserved; `app/` stays thin glue. No DB/schema migration
  (suggested portfolios persist as weights via the existing schema). Reproducible,
  look-ahead-safe, "not financial advice".

## Verification

- 2A: ranked `docs/OPTIMIZATION_RESEARCH.md` + recorded user selection.
- 2B: `uv run pytest` (valid/capped weights, baseline, selection ≤ k, determinism,
  stability) + `uv run ruff check` clean.
- 2C: app boot smoke green; launch `uv run streamlit run app/streamlit_app.py` and
  screenshot the Optimize page (both modes) showing suggested vs equal-weight vs
  benchmark.
- Independent `/code-review` on each feature branch before merge; update
  `docs/PROGRESS.md` per stage.
