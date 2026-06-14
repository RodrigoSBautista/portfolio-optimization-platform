"""Plotly chart helpers for the app (interactive growth/tracking charts)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def growth_chart(
    sim: pd.DataFrame,
    benchmark_value: pd.Series | None,
    *,
    currency: str = "USD",
    title: str = "Portfolio growth",
) -> go.Figure:
    """Interactive growth chart: portfolio value, contributions, and benchmark.

    ``sim`` has ``value`` and ``invested`` columns (from ``simulate_portfolio``);
    ``benchmark_value`` is a comparable value series (same contributions, 100% bench).
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=sim.index, y=sim["value"], name="Portfolio", line={"width": 2.5})
    )
    if benchmark_value is not None and not benchmark_value.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_value.index,
                y=benchmark_value,
                name="Benchmark",
                line={"width": 2, "dash": "dash"},
            )
        )
    fig.add_trace(
        go.Scatter(
            x=sim.index,
            y=sim["invested"],
            name="Invested (cost basis)",
            line={"width": 1.5, "dash": "dot", "color": "gray"},
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=f"Value ({currency})",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
    )
    return fig
