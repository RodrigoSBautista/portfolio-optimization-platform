"""Builder page: choose holdings (by weight or $), save to account, export/import.

Tickers and the benchmark are picked from a searchable curated universe
(`data/tickers.py`), with a free-text fallback for anything not on the list.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.auth import current_user_id
from app.services import get_session_factory
from core.portfolio import (
    LUMP_SUM,
    RECURRING,
    Contribution,
    Holding,
    PortfolioSpec,
    weights_from_amounts,
)
from data.tickers import COMMON_BENCHMARKS, label, symbols
from storage.db import session_scope
from storage.portfolio_io import export_json, import_json
from storage.repository import Repository

_FREQS = ["none", "monthly", "weekly", "quarterly", "annually"]
_OTHER = "Other…"
_DEFAULT_HOLDINGS = pd.DataFrame(
    {"symbol": ["AAPL", "MSFT", "GOOGL"], "value": [0.4, 0.4, 0.2]}
)


def _init_state() -> None:
    st.session_state.setdefault("b_name", "My Portfolio")
    st.session_state.setdefault("b_bench_choice", "SPY")
    st.session_state.setdefault("b_bench_other", "SPY")
    st.session_state.setdefault("b_mode", "Weight")
    st.session_state.setdefault("b_lump", 1000.0)
    st.session_state.setdefault("b_rec", 0.0)
    st.session_state.setdefault("b_freq", "none")
    if "b_holdings" not in st.session_state:
        st.session_state["b_holdings"] = _DEFAULT_HOLDINGS.copy()


def _apply_spec(spec: PortfolioSpec) -> None:
    st.session_state["b_name"] = spec.name
    if spec.benchmark_symbol in COMMON_BENCHMARKS:
        st.session_state["b_bench_choice"] = spec.benchmark_symbol
    else:
        st.session_state["b_bench_choice"] = _OTHER
        st.session_state["b_bench_other"] = spec.benchmark_symbol
    st.session_state["b_mode"] = "Weight"  # holdings persist as weights
    rows = [{"symbol": h.symbol, "value": h.weight} for h in spec.holdings]
    st.session_state["b_holdings"] = pd.DataFrame(rows, columns=["symbol", "value"])
    kwargs = spec.simulation_kwargs()
    st.session_state["b_lump"] = float(kwargs["lump_sum"])
    st.session_state["b_rec"] = float(kwargs["recurring_amount"])
    freq = kwargs["recurring_freq"] or "none"
    st.session_state["b_freq"] = freq if freq in _FREQS else "none"


def _current_benchmark() -> str:
    if st.session_state["b_bench_choice"] == _OTHER:
        return st.session_state["b_bench_other"].strip().upper() or "SPY"
    return st.session_state["b_bench_choice"]


def _build_spec(holdings_df: pd.DataFrame, mode: str) -> PortfolioSpec:
    pairs: list[tuple[str, float]] = []
    for _, row in holdings_df.iterrows():
        symbol_raw = row.get("symbol")
        value = row.get("value")
        # Skip blank rows; an empty data_editor cell comes back as NaN.
        if symbol_raw is None or pd.isna(symbol_raw) or value is None or pd.isna(value):
            continue
        symbol = str(symbol_raw).strip().upper()
        if symbol and float(value) > 0:
            pairs.append((symbol, float(value)))

    if mode == "Dollar amount":
        weights, total = weights_from_amounts(dict(pairs))
        holdings = [Holding(s, weights[s]) for s in weights]
        lump_sum = total
    else:
        holdings = [Holding(s, v) for s, v in pairs]  # raw weights, normalized at sim time
        lump_sum = float(st.session_state["b_lump"])

    contributions: list[Contribution] = []
    if lump_sum > 0:
        contributions.append(Contribution(LUMP_SUM, lump_sum))
    if st.session_state["b_rec"] > 0 and st.session_state["b_freq"] != "none":
        contributions.append(
            Contribution(
                RECURRING, float(st.session_state["b_rec"]), frequency=st.session_state["b_freq"]
            )
        )

    return PortfolioSpec(
        name=st.session_state["b_name"].strip() or "My Portfolio",
        holdings=holdings,
        benchmark_symbol=_current_benchmark(),
        contributions=contributions,
    )


def builder_page() -> None:
    _init_state()
    st.header("🧱 Build a portfolio")
    st.write("Pick US stocks/ETFs and a contribution plan, then save it.")

    uploaded = st.file_uploader("Restore a portfolio from a file (.json)", type="json")
    if uploaded is not None and st.button("Load this file"):
        try:
            _apply_spec(import_json(uploaded.getvalue().decode("utf-8")))
            st.success("Portfolio loaded.")
            st.rerun()
        except (ValueError, KeyError):
            st.error("That doesn't look like a valid portfolio file.")

    st.text_input("Portfolio name", key="b_name")

    # Benchmark: searchable curated list + free-text fallback.
    st.selectbox("Benchmark", COMMON_BENCHMARKS + [_OTHER], key="b_bench_choice")
    if st.session_state["b_bench_choice"] == _OTHER:
        st.text_input("Benchmark ticker", key="b_bench_other")

    st.subheader("Holdings")
    picks = st.multiselect(
        "Add tickers (type to search)", options=symbols(), format_func=label, key="b_pick"
    )
    if st.button("➕ Add selected") and picks:
        existing = {str(s).upper() for s in st.session_state["b_holdings"]["symbol"]}
        new = [{"symbol": s, "value": 0.0} for s in picks if s.upper() not in existing]
        if new:
            st.session_state["b_holdings"] = pd.concat(
                [st.session_state["b_holdings"], pd.DataFrame(new)], ignore_index=True
            )
            st.rerun()

    mode = st.radio("Enter holdings by", ["Weight", "Dollar amount"], key="b_mode", horizontal=True)
    value_label = "Amount ($)" if mode == "Dollar amount" else "Weight"
    step = 100.0 if mode == "Dollar amount" else 0.05
    holdings_df = st.data_editor(
        st.session_state["b_holdings"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "symbol": st.column_config.TextColumn("Ticker"),
            "value": st.column_config.NumberColumn(value_label, min_value=0.0, step=step),
        },
    )
    st.session_state["b_holdings"] = holdings_df  # persist edits

    st.subheader("Contributions")
    if mode == "Weight":
        col1, col2, col3 = st.columns(3)
        col1.number_input("Lump sum ($)", min_value=0.0, step=100.0, key="b_lump")
        col2.number_input("Recurring amount ($)", min_value=0.0, step=50.0, key="b_rec")
        col3.selectbox("Recurring frequency", _FREQS, key="b_freq")
    else:
        col2, col3 = st.columns(2)
        col2.number_input("Recurring amount ($)", min_value=0.0, step=50.0, key="b_rec")
        col3.selectbox("Recurring frequency", _FREQS, key="b_freq")

    spec = _build_spec(holdings_df, mode)
    st.session_state["current_spec"] = spec  # hand off to the Simulation page

    if spec.holdings:
        if mode == "Dollar amount":
            total = sum(c.amount for c in spec.contributions if c.kind == LUMP_SUM)
            implied = ", ".join(f"{h.symbol} {h.weight * 100:.0f}%" for h in spec.holdings)
            st.caption(f"Total initial investment: ${total:,.0f} · implied weights: {implied}")
        else:
            st.caption(
                f"{len(spec.holdings)} holding(s); weights sum to "
                f"{sum(h.weight for h in spec.holdings):.2f} (rescaled to 100% at simulation time)."
            )
    else:
        st.warning("Add at least one holding with a positive value.")

    st.divider()
    left, right = st.columns(2)
    with left:
        if st.button("💾 Save to my account", use_container_width=True, disabled=not spec.holdings):
            with session_scope(get_session_factory()) as session:
                Repository(session).save_portfolio(current_user_id(), spec)
            st.success(f"Saved '{spec.name}' to your account.")
    with right:
        st.download_button(
            "⬇️ Export to file (save on your computer)",
            data=export_json(spec),
            file_name=f"{spec.name.replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not spec.holdings,
        )
