"""Builder page: define holdings + contributions, save to account, export/import."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.auth import current_user_id
from app.services import get_session_factory
from core.portfolio import LUMP_SUM, RECURRING, Contribution, Holding, PortfolioSpec
from storage.db import session_scope
from storage.portfolio_io import export_json, import_json
from storage.repository import Repository

_FREQS = ["none", "monthly", "weekly", "quarterly", "annually"]
_DEFAULT_HOLDINGS = pd.DataFrame(
    {"symbol": ["AAPL", "MSFT", "GOOGL"], "weight": [0.4, 0.4, 0.2]}
)


def _init_state() -> None:
    st.session_state.setdefault("b_name", "My Portfolio")
    st.session_state.setdefault("b_bench", "SPY")
    st.session_state.setdefault("b_lump", 1000.0)
    st.session_state.setdefault("b_rec", 0.0)
    st.session_state.setdefault("b_freq", "none")
    st.session_state.setdefault("b_holdings", _DEFAULT_HOLDINGS.copy())


def _apply_spec(spec: PortfolioSpec) -> None:
    st.session_state["b_name"] = spec.name
    st.session_state["b_bench"] = spec.benchmark_symbol
    rows = [{"symbol": h.symbol, "weight": h.weight} for h in spec.holdings]
    st.session_state["b_holdings"] = pd.DataFrame(rows or _DEFAULT_HOLDINGS)
    kwargs = spec.simulation_kwargs()
    st.session_state["b_lump"] = float(kwargs["lump_sum"])
    st.session_state["b_rec"] = float(kwargs["recurring_amount"])
    st.session_state["b_freq"] = kwargs["recurring_freq"] or "none"


def _build_spec(holdings_df: pd.DataFrame) -> PortfolioSpec:
    holdings: list[Holding] = []
    for _, row in holdings_df.iterrows():
        symbol = str(row.get("symbol") or "").strip().upper()
        weight = row.get("weight")
        if symbol and weight is not None and float(weight) > 0:
            holdings.append(Holding(symbol, float(weight)))

    contributions: list[Contribution] = []
    if st.session_state["b_lump"] > 0:
        contributions.append(Contribution(LUMP_SUM, float(st.session_state["b_lump"])))
    if st.session_state["b_rec"] > 0 and st.session_state["b_freq"] != "none":
        contributions.append(
            Contribution(
                RECURRING, float(st.session_state["b_rec"]), frequency=st.session_state["b_freq"]
            )
        )

    return PortfolioSpec(
        name=st.session_state["b_name"].strip() or "My Portfolio",
        holdings=holdings,
        benchmark_symbol=(st.session_state["b_bench"].strip().upper() or "SPY"),
        contributions=contributions,
    )


def builder_page() -> None:
    _init_state()
    st.header("🧱 Build a portfolio")
    st.write("Pick US stocks/ETFs and target weights, set a contribution plan, then save it.")

    uploaded = st.file_uploader("Restore a portfolio from a file (.json)", type="json")
    if uploaded is not None and st.button("Load this file"):
        try:
            _apply_spec(import_json(uploaded.getvalue().decode("utf-8")))
            st.success("Portfolio loaded.")
            st.rerun()
        except (ValueError, KeyError):
            st.error("That doesn't look like a valid portfolio file.")

    st.text_input("Portfolio name", key="b_name")
    st.text_input("Benchmark symbol", key="b_bench", help="e.g. SPY")

    st.subheader("Holdings")
    holdings_df = st.data_editor(
        st.session_state["b_holdings"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "symbol": st.column_config.TextColumn("Ticker"),
            "weight": st.column_config.NumberColumn("Weight", min_value=0.0, step=0.05),
        },
        key="b_holdings_editor",
    )

    st.subheader("Contributions")
    col1, col2, col3 = st.columns(3)
    col1.number_input("Lump sum ($)", min_value=0.0, step=100.0, key="b_lump")
    col2.number_input("Recurring amount ($)", min_value=0.0, step=50.0, key="b_rec")
    col3.selectbox("Recurring frequency", _FREQS, key="b_freq")

    spec = _build_spec(holdings_df)
    st.session_state["current_spec"] = spec  # hand off to the Simulation page

    total_weight = sum(h.weight for h in spec.holdings)
    if spec.holdings:
        st.caption(
            f"{len(spec.holdings)} holding(s); weights sum to {total_weight:.2f} "
            "(rescaled to 100% at simulation time)."
        )
    else:
        st.warning("Add at least one holding with a positive weight.")

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
