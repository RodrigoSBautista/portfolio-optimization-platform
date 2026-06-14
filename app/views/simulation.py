"""Simulation page: 'how would my money have grown' — Plotly chart + metrics."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.charts import growth_chart
from app.services import fetch_prices
from app.sim_runner import SimError, format_metrics, run_simulation
from core.constants import NOT_FINANCIAL_ADVICE


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

    try:
        result = run_simulation(spec, prices)
    except SimError as exc:
        st.error(str(exc))
        return

    if result.dropped:
        st.warning(f"No data for: {', '.join(result.dropped)} — excluded from the simulation.")
    if not result.has_benchmark:
        st.warning(f"Benchmark {benchmark} unavailable — showing the portfolio only.")

    gain_pct = (result.final_value / result.invested - 1) * 100 if result.invested else 0.0
    k1, k2, k3 = st.columns(3)
    k1.metric("Final value", f"${result.final_value:,.0f}")
    k2.metric("Total invested", f"${result.invested:,.0f}")
    k3.metric("Gain", f"${result.final_value - result.invested:,.0f}", f"{gain_pct:,.1f}%")

    st.plotly_chart(
        growth_chart(result.sim, result.benchmark_value, currency=spec.base_currency),
        use_container_width=True,
    )

    st.subheader("Performance metrics")
    cols = {"Portfolio": format_metrics(result.sim["twr_index"])}
    if result.benchmark_index is not None:
        cols[result.benchmark] = format_metrics(result.benchmark_index)
    st.dataframe(pd.DataFrame(cols), use_container_width=True)

    st.caption(NOT_FINANCIAL_ADVICE)
