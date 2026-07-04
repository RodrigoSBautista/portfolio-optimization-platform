"""Simulation + optimization endpoints.

Pure HTTP orchestration: fetch prices via ``data.prices.PriceService``, then delegate
all finance math to the framework-free ``app.sim_runner`` and ``core.optimization``.
No math is implemented here.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_price_service
from api.schemas import (
    ComparisonPoint,
    DrawdownPoint,
    OptimizeRequest,
    OptimizeResponse,
    RollingPoint,
    SeriesPoint,
    SimulateRequest,
    SimulateResponse,
)
from app.sim_runner import SimError, format_metrics, run_simulation
from core.metrics import deflate
from core.optimization import (
    ALLOCATION_METHODS,
    SELECTION_METHODS,
    allocate,
    equal_weight,
    select,
)
from core.portfolio import LUMP_SUM, Contribution, Holding, PortfolioSpec
from data.prices import PriceService
from data.provider import common_history

router = APIRouter(prefix="/api", tags=["analysis"])

# Rebalance cadences the API contract exposes (subset of core's supported vocabulary).
_REBALANCE_CADENCES = {"monthly", "quarterly", "annually"}
_ROLLING_WINDOW = 252  # trading days for the 1-year rolling stats


def _safe_float(value: float) -> float | None:
    """None for NaN/inf so the response serializes to valid JSON (browser-parseable)."""
    import math

    return None if value is None or not math.isfinite(value) else float(value)


# Nominal lump sum for the optimize growth comparison (mirrors the Streamlit page).
# Without cash the simulation holds $0 forever: flat series and all-zero metrics.
_COMPARISON_LUMP = 10_000.0


def _spec_from_weights(name: str, weights: dict[str, float], benchmark: str) -> PortfolioSpec:
    """Build a comparable spec: given weights, a shared nominal lump sum, no DCA."""
    return PortfolioSpec(
        name=name,
        holdings=[Holding(sym, w) for sym, w in weights.items()],
        benchmark_symbol=benchmark,
        contributions=[Contribution(LUMP_SUM, _COMPARISON_LUMP)],
    )


@router.post("/simulate", response_model=SimulateResponse)
def simulate(
    body: SimulateRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> SimulateResponse:
    spec = body.spec.to_spec()
    benchmark = (body.benchmark or spec.benchmark_symbol).upper()
    symbols = sorted({h.symbol.upper() for h in spec.holdings} | {benchmark})
    if not spec.holdings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Portfolio has no holdings"
        )
    if body.rebalance is not None and body.rebalance not in _REBALANCE_CADENCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"rebalance must be one of {sorted(_REBALANCE_CADENCES)} or null",
        )

    prices = prices_svc.get_adjusted_close(symbols, body.start, body.end)
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data for the requested holdings and window",
        )

    # Extra simulate kwargs: rebalance/escalation/fee (percent inputs go straight to
    # simulate_portfolio, which interprets them as percents).
    sim_overrides = {
        "rebalance": body.rebalance,
        "escalation_pct": body.escalation_pct,
        "annual_fee_pct": body.annual_fee_pct,
    }
    try:
        result = run_simulation(spec, prices, benchmark, sim_overrides=sim_overrides)
    except (SimError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    sim = result.sim
    bench = result.benchmark_value

    # Real (inflation-adjusted) value series when inflation_pct is set. deflate() takes
    # a PERCENT annual rate.
    real_series = None
    real_final_value = None
    if body.inflation_pct is not None:
        real_series = deflate(sim["value"], annual_inflation_pct=body.inflation_pct)
        real_final_value = _safe_float(float(real_series.iloc[-1]))

    series: list[SeriesPoint] = []
    for ts, row in sim.iterrows():
        series.append(
            SeriesPoint(
                date=ts.date(),
                value=float(row["value"]),
                invested=float(row["invested"]),
                benchmark=(float(bench.loc[ts]) if bench is not None else None),
                real_value=(
                    _safe_float(float(real_series.loc[ts])) if real_series is not None else None
                ),
            )
        )

    # Portfolio metrics get beta/alpha when a benchmark is present; the benchmark's own
    # metrics never carry beta/alpha (it would be beta-vs-itself).
    metrics: dict[str, dict[str, str]] = {
        spec.name: format_metrics(
            sim["twr_index"],
            risk_free_rate=body.risk_free_rate,
            benchmark_index=(result.benchmark_index if result.has_benchmark else None),
        )
    }
    if result.has_benchmark and result.benchmark_index is not None:
        metrics[result.benchmark] = format_metrics(
            result.benchmark_index, risk_free_rate=body.risk_free_rate
        )

    drawdown = rolling = None
    if body.include_analytics:
        drawdown, rolling = _build_analytics(sim["twr_index"])

    invested = result.invested
    gain_pct = (result.final_value / invested - 1.0) * 100.0 if invested else 0.0
    return SimulateResponse(
        series=series,
        metrics=metrics,
        final_value=result.final_value,
        invested=invested,
        gain_pct=gain_pct,
        dropped=result.dropped,
        benchmark=result.benchmark,
        real_final_value=real_final_value,
        drawdown=drawdown,
        rolling=rolling,
    )


def _build_analytics(twr_index) -> tuple[list[DrawdownPoint], list[RollingPoint]]:
    """Drawdown curve + 252-day rolling return/vol from a TWR return-index series."""
    dd = twr_index / twr_index.cummax() - 1.0
    drawdown = [DrawdownPoint(date=ts.date(), pct=float(v)) for ts, v in dd.items()]

    rets = twr_index.pct_change()
    roll_ret = (1.0 + rets).rolling(_ROLLING_WINDOW).apply(lambda x: x.prod(), raw=True) - 1.0
    roll_vol = rets.rolling(_ROLLING_WINDOW).std(ddof=1) * (_ROLLING_WINDOW ** 0.5)
    rolling = [
        RollingPoint(
            date=ts.date(),
            ret_1y=_safe_float(float(roll_ret.loc[ts])),
            vol_1y=_safe_float(float(roll_vol.loc[ts])),
        )
        for ts in twr_index.index
    ]
    return drawdown, rolling


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(
    body: OptimizeRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> OptimizeResponse:
    benchmark = body.benchmark.upper()
    candidate_set = body.candidates if body.mode == "select" else body.tickers
    candidates = sorted({t.upper() for t in candidate_set})
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No candidate tickers provided"
        )

    start = date(date.today().year - max(body.lookback_years, 1), date.today().month, 1)
    fetch = sorted(set(candidates) | {benchmark})
    prices = prices_svc.get_adjusted_close(fetch, start)
    aligned = common_history(prices)
    if aligned.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No overlapping price history for the candidate set",
        )

    available = [c for c in candidates if c in aligned.columns]
    if not available:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="None of the candidates returned price data",
        )
    candidate_prices = aligned[available]

    # `method` is always the allocation method; `selection_method` (select mode) picks
    # which tickers to keep. Validate names up front so a typo is a 400, not a 500.
    if body.method not in ALLOCATION_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown allocation method '{body.method}'",
        )
    if body.mode == "select":
        sel_method = body.selection_method or "Low volatility"
        if sel_method not in SELECTION_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown selection method '{sel_method}'",
            )
        k = body.k or len(available)
        selected = [s for s in select(sel_method, candidate_prices, k) if s in available]
    else:
        selected = available

    alloc_prices = candidate_prices[selected]
    suggested = allocate(body.method, alloc_prices, max_weight=body.max_weight)
    baseline = equal_weight(selected)

    sug_spec = _spec_from_weights("Suggested", suggested, benchmark)
    base_spec = _spec_from_weights("Equal weight", baseline, benchmark)
    try:
        sug_res = run_simulation(sug_spec, aligned, benchmark)
        base_res = run_simulation(base_spec, aligned, benchmark)
    except SimError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    sug_val = sug_res.sim["value"]
    base_val = base_res.sim["value"]
    bench_val = sug_res.benchmark_value
    comparison: list[ComparisonPoint] = []
    for ts in sug_val.index:
        comparison.append(
            ComparisonPoint(
                date=ts.date(),
                suggested=float(sug_val.loc[ts]),
                equal_weight=(float(base_val.loc[ts]) if ts in base_val.index else None),
                benchmark=(
                    float(bench_val.loc[ts])
                    if bench_val is not None and ts in bench_val.index
                    else None
                ),
            )
        )

    metrics: dict[str, dict[str, str]] = {
        body.method: format_metrics(sug_res.sim["twr_index"]),
        "Equal weight": format_metrics(base_res.sim["twr_index"]),
    }
    if sug_res.has_benchmark and sug_res.benchmark_index is not None:
        metrics[benchmark] = format_metrics(sug_res.benchmark_index)

    return OptimizeResponse(
        selected=selected,
        suggested=suggested,
        baseline=baseline,
        comparison_series=comparison,
        metrics=metrics,
    )
