"""Simulation page: 'how would my money have grown' — Plotly chart + metrics."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.charts import growth_chart
from app.services import fetch_prices
from core.constants import NOT_FINANCIAL_ADVICE
from core.metrics import summarize
from core.simulation import simulate_portfolio
from data.provider import common_history


def _format_metrics(index: pd.Series) -> dict[str, str]:
    m = summarize(index)
    return {
        "Total return": f"{m['total_return'] * 100:,.1f}%",
        "CAGR": f"{m['cagr'] * 100:,.1f}%",
        "Volatility (ann.)": f"{m['volatility'] * 100:,.1f}%",
        "Sharpe": f"{m['sharpe']:,.2f}",
        "Max drawdown": f"{m['max_drawdown'] * 100:,.1f}%",
    }


def simulation_page() -> None:
    st.header("📈 Growth simulation")
    spec = st.session_state.get("current_spec")
    if spec is None or not spec.holdings:
        st.info("Head to **Build a portfolio** first to choose holdings.")
        return

    st.write(f"**{spec.name}** — benchmark **{spec.benchmark_symbol}**")
    col1, col2 = st.columns([2, 1])
    start = col1.date_input(
        "Invest starting from",
        value=date(2018, 1, 1),
        min_value=date(1990, 1, 1),
        max_value=date.today(),
    )
    run = col2.button("▶️ Run simulation", use_container_width=True, type="primary")
    if not run:
        st.caption("Choose a start date and run the simulation.")
        return

    symbols = sorted({h.symbol.upper() for h in spec.holdings})
    benchmark = spec.benchmark_symbol.upper()
    prices = fetch_prices(tuple(sorted(set(symbols) | {benchmark})), start, None)
    if prices.empty:
        st.error("No price data returned for these tickers. Check the symbols.")
        return

    available = [s for s in symbols if s in prices.columns]
    dropped = [s for s in symbols if s not in prices.columns]
    if dropped:
        st.warning(f"No data for: {', '.join(dropped)} — excluded from the simulation.")
    if not available:
        st.error("None of the holdings returned price data.")
        return

    # Align holdings AND benchmark to one common window so the benchmark line uses an
    # identical date range and contribution schedule (apples-to-apples comparison).
    has_benchmark = benchmark in prices.columns
    cols = available + ([benchmark] if has_benchmark else [])
    aligned = common_history(prices[cols])
    if aligned.empty:
        st.error("No overlapping price history across these tickers and the benchmark.")
        return

    weights = {s: w for s, w in spec.weights().items() if s in available}
    kwargs = spec.simulation_kwargs()
    sim = simulate_portfolio(aligned[available], weights, **kwargs)

    bench_value = None
    bench_index = None
    if has_benchmark:
        bench_sim = simulate_portfolio(aligned[[benchmark]], {benchmark: 1.0}, **kwargs)
        bench_value = bench_sim["value"]
        bench_index = bench_sim["twr_index"]
    else:
        st.warning(f"Benchmark {benchmark} unavailable — showing the portfolio only.")

    final = float(sim["value"].iloc[-1])
    invested = float(sim["invested"].iloc[-1])
    gain_pct = (final / invested - 1) * 100 if invested else 0.0
    k1, k2, k3 = st.columns(3)
    k1.metric("Final value", f"${final:,.0f}")
    k2.metric("Total invested", f"${invested:,.0f}")
    k3.metric("Gain", f"${final - invested:,.0f}", f"{gain_pct:,.1f}%")

    st.plotly_chart(
        growth_chart(sim, bench_value, currency=spec.base_currency),
        use_container_width=True,
    )

    st.subheader("Performance metrics")
    cols = {"Portfolio": _format_metrics(sim["twr_index"])}
    if bench_index is not None:
        cols[spec.benchmark_symbol] = _format_metrics(bench_index)
    st.dataframe(pd.DataFrame(cols), use_container_width=True)

    st.caption(NOT_FINANCIAL_ADVICE)
