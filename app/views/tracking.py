"""Tracking page: stored daily valuations of saved portfolios vs benchmark."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.auth import current_user_id
from app.services import get_price_service, get_session_factory
from core.constants import NOT_FINANCIAL_ADVICE
from core.metrics import cagr, max_drawdown, return_index
from jobs.refresh import refresh_portfolio
from storage.db import session_scope
from storage.portfolio_io import orm_to_spec
from storage.repository import Repository


def tracking_page() -> None:
    st.header("📊 Tracking dashboard")
    factory = get_session_factory()
    user_id = current_user_id()

    with session_scope(factory) as session:
        portfolios = [(p.id, p.name) for p in Repository(session).list_portfolios(user_id)]
    if not portfolios:
        st.info("Save a portfolio on the **Build a portfolio** page first.")
        return

    labels = {f"{name}  (#{pid})": pid for pid, name in portfolios}
    choice = st.selectbox("Portfolio", list(labels))
    portfolio_id = labels[choice]

    col1, col2 = st.columns([2, 1])
    start = col1.date_input("Track since", value=date(date.today().year - 3, 1, 1))
    if col2.button("🔄 Refresh now", use_container_width=True, type="primary"):
        with session_scope(factory) as session:
            repo = Repository(session)
            spec = orm_to_spec(repo.get_portfolio(user_id, portfolio_id))
            written = refresh_portfolio(
                repo, get_price_service(), user_id, portfolio_id, spec, start
            )
        st.success(f"Stored {written} daily valuations.")

    with session_scope(factory) as session:
        rows = [
            (v.as_of_date, v.market_value, v.benchmark_value)
            for v in Repository(session).get_valuations(user_id, portfolio_id)
        ]
    if not rows:
        st.info("No tracked history yet — click **Refresh now** to build it.")
        return

    df = pd.DataFrame(rows, columns=["date", "portfolio", "benchmark"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["portfolio"], name="Portfolio", line={"width": 2.5}))
    if df["benchmark"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["benchmark"], name="Benchmark", line={"width": 2, "dash": "dash"}
            )
        )
    fig.update_layout(
        title="Tracked value vs benchmark",
        xaxis_title="Date",
        yaxis_title="Value (USD)",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True)

    port_index = return_index(df["portfolio"])
    k1, k2, k3 = st.columns(3)
    k1.metric("Latest value", f"${df['portfolio'].iloc[-1]:,.0f}")
    k2.metric("CAGR", f"{cagr(port_index) * 100:,.1f}%")
    k3.metric("Max drawdown", f"{max_drawdown(port_index) * 100:,.1f}%")

    st.caption(NOT_FINANCIAL_ADVICE)
