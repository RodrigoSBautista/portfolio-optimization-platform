---
name: finance-conventions
description: >-
  Single source of truth for this project's finance math conventions — metric
  definitions (TWR, Sharpe/Sortino/Calmar, annualization, risk-free rate),
  simulation rules (look-ahead safety, common-window alignment, contribution
  schedules), and known gotchas (benchmark-as-holding dedupe, NaN handling,
  expense ratios embedded in adjusted prices). Read before writing or reviewing
  any code that computes returns, risk, or projections.
---

# Finance Conventions (project-wide)

## Prices & returns
- All growth math uses **dividend-adjusted (total-return) closes** from `data/`.
  **Fund expense ratios are already embedded in these prices** — never add them again;
  only an explicit user "advisory fee %/yr" input adds drag.
- Daily simple returns: `prices.pct_change()`; **annualization factor = 252** trading
  days (vol: `daily_std * sqrt(252)`; returns compound, never multiply by 252).
- Clean inputs like `core/optimization._returns`: ffill internal gaps (look-ahead-safe),
  trim to the common window, drop all-NaN and zero-variance columns.

## Alignment rules (bugs we actually shipped, then fixed)
- **Common window:** portfolio and benchmark must be simulated over ONE globally
  aligned window (`data/provider.common_history`) so dates and contribution schedules
  match. Never align each side separately.
- **Dedupe the benchmark:** when the benchmark is also a holding (SPY portfolio vs SPY),
  dedupe the ticker request AND the frame columns (`dict.fromkeys`,
  `frame.loc[:, ~frame.columns.duplicated()]`) — duplicate labels make single-ticker
  slices 2-D ("Data must be 1-dimensional").
- **Drop price-less holdings** from the weight dict before simulating
  (`{s: w for s, w in weights.items() if s in frame.columns}`) and surface them to the
  caller as `dropped` — never crash, never silently pretend.

## Return measurement
- **TWR (time-weighted return)** for all performance percentages/metrics — contributions
  must never be mistaken for gains. `simulate_portfolio` returns `twr_index` for this.
- `value` and `invested` are **dollar, cost-basis** series (money in / money out) —
  label them as such in UIs; never present `final/invested - 1` as "return %" next to
  TWR numbers (they answer different questions and WILL contradict under DCA).

## Metrics
- **Sharpe** = `(annualized_return − risk_free_rate) / annualized_vol`. The risk-free
  rate is a parameter (project default: 4.0%/yr unless the caller overrides) — rf=0 is
  NOT acceptable as a silent default in new code.
- **Sortino**: like Sharpe but denominator = downside deviation (std of negative daily
  returns only, annualized √252).
- **Calmar** = annualized return / |max drawdown|.
- **Beta/alpha**: OLS of portfolio daily excess returns on benchmark daily excess
  returns; alpha reported annualized.
- **Max drawdown** on the TWR index, min of `index/cummax − 1`.
- **Real (inflation-adjusted)**: deflate a nominal series by `(1+i)^(t_years)` with a
  user-set annual rate (default 2.5%); label clearly as "in today's dollars".

## Simulation rules
- **Look-ahead safe**: every buy/rebalance uses that day's price; loops run strictly
  forward; contribution/rebalance dates snap FORWARD to the next trading day
  (`core/simulation._contribution_dates`).
- Recurring cadences supported: weekly, monthly, every 2 months, quarterly,
  every 6 months, annually (DateOffset-based; supports N-month steps).
- Weights are validated long-only and renormalized to sum to 1
  (`core/simulation.normalize_weights`).

## Projections (Monte Carlo / withdrawals)
- **Block bootstrap** of historical daily returns (block ≈ 21 trading days) — preserves
  fat tails and short-run autocorrelation; never assume i.i.d. normal.
- **Seed all randomness** (`numpy.random.default_rng(seed)`); deterministic tests.
- Output **percentile bands (e.g. 5/25/50/75/95) and distributions — never a single
  predicted path**. Always attach the caveat: projections resample the past; the future
  can differ; not financial advice.

## Testing bar
- Metric formulas verified against **hand-computed values** on tiny fixtures.
- Explicit tests for look-ahead safety, isolation (user A ≠ user B), NaN/flat/
  non-overlapping inputs, benchmark-as-holding, and seeded-projection determinism.
