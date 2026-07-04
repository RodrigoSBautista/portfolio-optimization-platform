"""Run a portfolio simulation from an already-fetched price frame.

Shared by the Simulation and Compare pages so they stay consistent (single source of
truth for align → simulate → metrics). No Streamlit imports — takes a prices frame +
spec and returns a ``SimResult``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.metrics import summarize
from core.portfolio import PortfolioSpec
from core.simulation import simulate_portfolio
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
    ``annual_fee_pct``) on top of the spec's contribution kwargs — applied to both the
    portfolio and the benchmark so they stay on identical flows.
    """
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
        bench_sim = simulate_portfolio(aligned[[benchmark]], {benchmark: 1.0}, **kwargs)
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
