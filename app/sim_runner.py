"""Run a portfolio simulation from an already-fetched price frame.

Shared by the Simulation and Compare pages so they stay consistent (single source of
truth for align → simulate → metrics). No Streamlit imports — takes a prices frame +
spec and returns a ``SimResult``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from core.metrics import summarize
from core.portfolio import Lot, PortfolioSpec
from core.simulation import simulate_lots_detailed, simulate_portfolio
from data.provider import common_history


class SimError(ValueError):
    """Raised when a simulation can't run (no holdings data / no overlap)."""


@dataclass
class SimResult:
    sim: pd.DataFrame  # value, invested, twr_index
    benchmark_value: pd.Series | None
    benchmark_index: pd.Series | None
    dropped: list[str]
    benchmark: str
    has_benchmark: bool

    @property
    def final_value(self) -> float:
        return float(self.sim["value"].iloc[-1])

    @property
    def invested(self) -> float:
        return float(self.sim["invested"].iloc[-1])


def run_simulation(
    spec: PortfolioSpec,
    prices: pd.DataFrame,
    benchmark: str | None = None,
    *,
    sim_overrides: dict | None = None,
) -> SimResult:
    """Simulate ``spec`` over ``prices``; benchmark simulated with identical flows.

    Aligns holdings + benchmark to a common window (apples-to-apples). When ``prices``
    is already globally aligned (the Compare page), every portfolio shares one window.
    ``benchmark`` overrides ``spec.benchmark_symbol`` (used by Compare). ``sim_overrides``
    merges extra ``simulate_portfolio`` kwargs (e.g. ``rebalance``, ``escalation_pct``,
    ``annual_fee_pct``) on top of the spec's contribution kwargs. Cash-flow overrides
    (escalation) apply to BOTH lines so flows stay identical; ``annual_fee_pct`` applies
    to the PORTFOLIO only — the benchmark is an unadvised index, and the comparison is
    exactly where the fee's cost should be visible.
    """
    if spec.is_lot_based:
        return _run_lot_simulation(spec, prices, benchmark, sim_overrides)

    benchmark = (benchmark or spec.benchmark_symbol).upper()
    # Duplicate column labels (e.g. a caller passing the benchmark twice) make
    # single-ticker slices 2-D; keep the first occurrence of each column.
    prices = prices.loc[:, ~prices.columns.duplicated()]
    symbols = sorted({h.symbol.upper() for h in spec.holdings})
    available = [s for s in symbols if s in prices.columns]
    dropped = [s for s in symbols if s not in prices.columns]
    if not available:
        raise SimError("None of the holdings returned price data.")

    has_benchmark = benchmark in prices.columns
    # Dedupe: when the benchmark is also a holding, appending it would duplicate the
    # column and make aligned[[benchmark]] two-dimensional.
    cols = list(dict.fromkeys(available + ([benchmark] if has_benchmark else [])))
    aligned = common_history(prices[cols])
    if aligned.empty:
        raise SimError("No overlapping price history across these tickers and the benchmark.")

    weights = {s: w for s, w in spec.weights().items() if s in available}
    kwargs = spec.simulation_kwargs()
    if sim_overrides:
        kwargs.update(sim_overrides)
    sim = simulate_portfolio(aligned[available], weights, **kwargs)

    benchmark_value = benchmark_index = None
    if has_benchmark:
        # Identical cash flows, but no advisory-fee drag on the index line.
        bench_kwargs = {**kwargs, "annual_fee_pct": 0.0}
        bench_sim = simulate_portfolio(aligned[[benchmark]], {benchmark: 1.0}, **bench_kwargs)
        benchmark_value = bench_sim["value"]
        benchmark_index = bench_sim["twr_index"]

    return SimResult(sim, benchmark_value, benchmark_index, dropped, benchmark, has_benchmark)


# Overrides that the weight-based engine understands but the lots engine does not.
# A lot portfolio's cash flows ARE the dated purchases — there is no recurring
# contribution to escalate, no target weights to rebalance to, and the advisory-fee
# decay is unimplemented for the lots path — so any non-trivial value is rejected.
def _reject_lot_overrides(overrides: dict) -> None:
    if overrides.get("rebalance"):
        raise SimError("rebalance is not applicable to dated-purchase portfolios")
    if overrides.get("escalation_pct"):
        raise SimError("escalation_pct is not applicable to dated-purchase portfolios")
    if overrides.get("annual_fee_pct"):
        raise SimError("annual_fee_pct is not applicable to dated-purchase portfolios")


def _placed_lots(spec_lots: list[Lot], dropped: list[Lot]) -> list[Lot]:
    """The lots that were actually placed = spec lots minus the dropped ones.

    ``dropped`` carries cleaned lots (upper-cased symbol, float amount); match on that
    canonical key as a multiset so duplicate lots are removed one-for-one, and preserve
    the ORIGINAL spec order so mirror flows line up date-for-date.
    """
    remaining = Counter((lot.symbol.upper(), lot.date, float(lot.amount)) for lot in dropped)
    placed: list[Lot] = []
    for lot in spec_lots:
        key = (lot.symbol.upper(), lot.date, float(lot.amount))
        if remaining.get(key, 0) > 0:
            remaining[key] -= 1
        else:
            placed.append(lot)
    return placed


def _run_lot_simulation(
    spec: PortfolioSpec,
    prices: pd.DataFrame,
    benchmark: str | None,
    sim_overrides: dict | None,
) -> SimResult:
    """Simulate a lot-based spec; benchmark uses MIRROR lots (same dollars/dates).

    The benchmark line invests each PLACED lot's dollars into the benchmark on the same
    date, so the two lines are apples-to-apples (identical cash flows, identical timing).
    Dropped lots are excluded from the mirror so flows match exactly. If the benchmark
    listed AFTER an early lot, that mirror buy is clamped to the benchmark's first
    trading day (the dollars still go in — on the earliest day the benchmark existed)
    rather than being silently dropped, which would leave the two lines investing
    unequal dollars and fake an outperformance. ``prices`` must reach back to
    ``min(lot.date)`` (the API fetches from there per the core contract).
    """
    benchmark = (benchmark or spec.benchmark_symbol).upper()
    prices = prices.loc[:, ~prices.columns.duplicated()]
    if sim_overrides:
        _reject_lot_overrides(sim_overrides)

    try:
        sim, dropped_lots = simulate_lots_detailed(prices, spec.lots)
    except ValueError as exc:
        raise SimError(str(exc)) from exc

    dropped = sorted({lot.symbol.upper() for lot in dropped_lots})
    placed = _placed_lots(spec.lots, dropped_lots)

    benchmark_value = benchmark_index = None
    has_benchmark = benchmark in prices.columns and bool(placed)
    if has_benchmark:
        # Clamp each mirror buy to the benchmark's first trading day so a benchmark
        # that listed after an early lot still receives every dollar (invested parity),
        # instead of that mirror lot being dropped for lack of a price at its date.
        bench_first = prices[benchmark].first_valid_index()
        bench_start = bench_first.date() if bench_first is not None else None
        mirror = [
            Lot(benchmark, max(lot.date, bench_start) if bench_start else lot.date, lot.amount)
            for lot in placed
        ]
        bench_sim, _ = simulate_lots_detailed(prices, mirror)
        benchmark_value = bench_sim["value"]
        benchmark_index = bench_sim["twr_index"]

    return SimResult(sim, benchmark_value, benchmark_index, dropped, benchmark, has_benchmark)


def format_metrics(
    index: pd.Series,
    *,
    risk_free_rate: float = 0.04,
    benchmark_index: pd.Series | None = None,
) -> dict[str, str]:
    """Human-readable metric bundle for a TWR return-index series.

    The original five rows are unchanged. The risk-adjusted extras (Sortino, Calmar,
    Best/Worst calendar year) are always appended; Beta and annualized Alpha are added
    only when a ``benchmark_index`` is supplied. ``risk_free_rate`` is an annual
    fraction (e.g. 0.04 = 4%/yr) passed straight to ``summarize``.

    Best/Worst year are **calendar-year** total returns — the first and last year may be
    partial (they base on the series' opening/closing value).
    """
    m = summarize(index, risk_free_rate=risk_free_rate, benchmark_index=benchmark_index)
    out = {
        "Total return": f"{m['total_return'] * 100:,.1f}%",
        "CAGR": f"{m['cagr'] * 100:,.1f}%",
        "Volatility (ann.)": f"{m['volatility'] * 100:,.1f}%",
        "Sharpe": f"{m['sharpe']:,.2f}",
        "Max drawdown": f"{m['max_drawdown'] * 100:,.1f}%",
        "Sortino": f"{m['sortino']:,.2f}",
        "Calmar": f"{m['calmar']:,.2f}",
        "Best year": f"{m['best_year'] * 100:,.1f}%",
        "Worst year": f"{m['worst_year'] * 100:,.1f}%",
    }
    if benchmark_index is not None:
        out["Beta"] = f"{m['beta']:,.2f}"
        out["Alpha (ann.)"] = f"{m['alpha'] * 100:,.1f}%"
    return out
