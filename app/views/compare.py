"""Compare page: 2–3 saved portfolios side by side vs a shared benchmark."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.auth import current_user_id
from app.charts import comparison_chart
from app.services import fetch_prices, get_session_factory
from app.sim_runner import SimError, format_metrics, run_simulation
from core.constants import NOT_FINANCIAL_ADVICE
from data.provider import common_history
from data.tickers import COMMON_BENCHMARKS
from storage.db import session_scope
from storage.portfolio_io import orm_to_spec
from storage.repository import Repository


def compare_page() -> None:
    st.header("⚖️ Compare portfolios")
    factory = get_session_factory()
    user_id = current_user_id()

    with session_scope(factory) as session:
        saved = [(p.id, p.name) for p in Repository(session).list_portfolios(user_id)]
    if len(saved) < 2:
        st.info("Save at least two portfolios on the **Build a portfolio** page to compare them.")
        return

    labels = {f"{name}  (#{pid})": pid for pid, name in saved}
    chosen = st.multiselect("Pick 2–3 saved portfolios", list(labels), max_selections=3)

    col1, col2, col3 = st.columns([2, 1, 1])
    start = col1.date_input(
        "Invest starting from",
        value=date(2018, 1, 1),
        min_value=date(1990, 1, 1),
        max_value=date.today(),
    )
    benchmark = col2.selectbox("Benchmark", COMMON_BENCHMARKS).upper()
    run = col3.button("▶️ Compare", use_container_width=True, type="primary")
    if not run:
        st.caption("Pick portfolios and a benchmark, then compare.")
        return
    if not 2 <= len(chosen) <= 3:
        st.warning("Select two or three portfolios.")
        return

    with session_scope(factory) as session:
        repo = Repository(session)
        specs = {c: orm_to_spec(repo.get_portfolio(user_id, labels[c])) for c in chosen}

    # Fetch every ticker once, then align all portfolios + benchmark to ONE window so
    # total invested and contribution dates match across portfolios (apples-to-apples).
    all_tickers = {benchmark}
    for spec in specs.values():
        all_tickers |= {h.symbol.upper() for h in spec.holdings}
    prices = fetch_prices(tuple(sorted(all_tickers)), start, None)
    if prices.empty:
        st.error("No price data returned for these tickers.")
        return
    present = [t for t in sorted(all_tickers) if t in prices.columns]
    aligned = common_history(prices[present])
    if aligned.empty:
        st.error("No overlapping price window across all selected portfolios + benchmark.")
        return

    results = {}
    for name, spec in specs.items():
        try:
            results[name] = run_simulation(spec, aligned, benchmark=benchmark)
        except SimError as exc:
            st.warning(f"{name}: {exc}")
    if not results:
        return

    # KPIs — a column per portfolio.
    kpi_cols = st.columns(len(results))
    for col, (name, res) in zip(kpi_cols, results.items(), strict=False):
        gain = (res.final_value / res.invested - 1) * 100 if res.invested else 0.0
        col.markdown(f"**{name}**")
        col.metric("Final value", f"${res.final_value:,.0f}")
        col.metric("Total invested", f"${res.invested:,.0f}")
        col.metric("Gain", f"${res.final_value - res.invested:,.0f}", f"{gain:,.1f}%")

    first = next(iter(results.values()))
    st.plotly_chart(
        comparison_chart(
            {name: res.sim["value"] for name, res in results.items()}, first.benchmark_value
        ),
        use_container_width=True,
    )

    st.subheader("Performance metrics")
    table = {name: format_metrics(res.sim["twr_index"]) for name, res in results.items()}
    if first.benchmark_index is not None:
        table[benchmark] = format_metrics(first.benchmark_index)
    st.dataframe(pd.DataFrame(table), use_container_width=True)

    st.caption(NOT_FINANCIAL_ADVICE)
