"""Optimize page: suggest an allocation (always vs the equal-weight baseline).

Two modes — **Allocate** (weight a chosen set) and **Select** (pick tickers from a
candidate set, then weight). Finance logic lives in ``core/optimization.py``; this page
is thin glue that fetches prices, calls the optimizer, and reuses the simulation
machinery to compare suggested vs equal-weight vs benchmark.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.auth import current_user_id
from app.charts import comparison_chart, weights_bar
from app.services import fetch_prices, get_session_factory
from app.sim_runner import SimError, format_metrics, run_simulation
from core.constants import NOT_FINANCIAL_ADVICE
from core.optimization import ALLOCATION_METHODS, SELECTION_METHODS, allocate, equal_weight, select
from core.portfolio import LUMP_SUM, Contribution, Holding, PortfolioSpec
from data.provider import common_history
from data.tickers import COMMON_BENCHMARKS, label, symbols
from storage.db import session_scope
from storage.repository import Repository

_LUMP = 10_000.0  # fixed lump sum used for the growth comparison
_ALLOCATORS = [m for m in ALLOCATION_METHODS if m != "Equal weight"]


def _spec(name: str, weights: dict[str, float], benchmark: str) -> PortfolioSpec:
    return PortfolioSpec(
        name=name,
        holdings=[Holding(s, w) for s, w in weights.items()],
        benchmark_symbol=benchmark,
        contributions=[Contribution(LUMP_SUM, _LUMP)],
    )


def optimize_page() -> None:
    st.header("🧮 Optimize")
    st.write(
        "Get a suggested allocation — **always shown next to the equal-weight baseline** "
        "(which is famously hard to beat). Suggestions are educational, not advice."
    )

    mode = st.radio(
        "Mode", ["Allocate my tickers", "Select from a candidate set"], horizontal=True
    )
    c1, c2, c3 = st.columns(3)
    method = c1.selectbox("Allocation method", _ALLOCATORS)
    lookback = c2.slider("Lookback (years)", 1, 10, 3)
    benchmark = c3.selectbox("Benchmark", COMMON_BENCHMARKS).upper()
    cap_pct = st.slider("Max weight per asset (%)", 10, 100, 100, step=5)
    max_weight = None if cap_pct == 100 else cap_pct / 100.0

    if mode == "Allocate my tickers":
        picked = st.multiselect(
            "Tickers",
            options=symbols(),
            format_func=label,
            default=["AAPL", "MSFT", "GOOGL", "JNJ"],
        )
        candidates, k, sel_method = picked, None, None
    else:
        candidates = st.multiselect(
            "Candidate universe",
            options=symbols(),
            format_func=label,
            default=["AAPL", "MSFT", "GOOGL", "JNJ", "JPM", "XOM", "PG", "KO", "NVDA", "VZ"],
        )
        cc1, cc2 = st.columns(2)
        upper_k = max(2, len(candidates))
        k = cc1.slider("Number of holdings", 2, upper_k, min(5, upper_k))
        sel_method = cc2.selectbox("Selection method", list(SELECTION_METHODS))

    if not st.button("⚙️ Optimize", type="primary"):
        st.caption("Choose your tickers and method, then optimize.")
        return
    if len(candidates) < 2:
        st.warning("Pick at least two tickers.")
        return

    start = date(date.today().year - lookback, date.today().month, date.today().day)
    prices = fetch_prices(tuple(sorted({*[t.upper() for t in candidates], benchmark})), start, None)
    if prices.empty:
        st.error("No price data returned for these tickers.")
        return
    aligned = common_history(prices)
    if aligned.empty:
        st.error("No overlapping price window across these tickers + benchmark.")
        return

    # Selection mode narrows the candidate set first.
    universe = [t.upper() for t in candidates if t.upper() in aligned.columns]
    if sel_method is not None:
        chosen = select(sel_method, aligned[universe], k)
    else:
        chosen = universe
    if len(chosen) < 1:
        st.error("Selection returned no tickers.")
        return

    suggested = allocate(method, aligned[chosen], max_weight=max_weight)
    baseline = equal_weight(list(suggested))
    st.session_state["opt_suggested"] = suggested  # for save/use buttons below

    st.subheader("Suggested allocation")
    st.plotly_chart(
        weights_bar({method: suggested, "Equal weight": baseline}, title="Weights (%)"),
        use_container_width=True,
    )

    # Compare growth: suggested vs equal-weight vs benchmark (same window + lump sum).
    try:
        opt_spec = _spec(method, suggested, benchmark)
        eq_spec = _spec("Equal weight", baseline, benchmark)
        res_opt = run_simulation(opt_spec, aligned, benchmark=benchmark)
        res_eq = run_simulation(eq_spec, aligned, benchmark=benchmark)
    except SimError as exc:
        st.error(str(exc))
        return

    k1, k2 = st.columns(2)
    k1.metric(f"{method} — final value", f"${res_opt.final_value:,.0f}")
    k2.metric("Equal weight — final value", f"${res_eq.final_value:,.0f}")

    st.plotly_chart(
        comparison_chart(
            {method: res_opt.sim["value"], "Equal weight": res_eq.sim["value"]},
            res_opt.benchmark_value,
        ),
        use_container_width=True,
    )

    st.subheader("Performance metrics")
    table = {
        method: format_metrics(res_opt.sim["twr_index"]),
        "Equal weight": format_metrics(res_eq.sim["twr_index"]),
    }
    if res_opt.benchmark_index is not None:
        table[benchmark] = format_metrics(res_opt.benchmark_index)
    st.dataframe(pd.DataFrame(table), use_container_width=True)

    st.divider()
    left, right = st.columns(2)
    with left:
        if st.button("➡️ Use these weights in the Builder", use_container_width=True):
            st.session_state["current_spec"] = _spec(f"Optimized ({method})", suggested, benchmark)
            st.success("Loaded into the Builder / Growth simulation pages.")
    with right:
        name = st.text_input("Name", value=f"Optimized ({method})")
        if st.button("💾 Save as portfolio", use_container_width=True):
            with session_scope(get_session_factory()) as session:
                Repository(session).save_portfolio(
                    current_user_id(), _spec(name, suggested, benchmark)
                )
            st.success(f"Saved '{name}' to your account.")

    st.caption(NOT_FINANCIAL_ADVICE)
