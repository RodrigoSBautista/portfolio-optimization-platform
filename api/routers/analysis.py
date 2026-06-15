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
    OptimizeRequest,
    OptimizeResponse,
    SeriesPoint,
    SimulateRequest,
    SimulateResponse,
)
from app.sim_runner import SimError, format_metrics, run_simulation
from core.optimization import (
    ALLOCATION_METHODS,
    SELECTION_METHODS,
    allocate,
    equal_weight,
    select,
)
from core.portfolio import Holding, PortfolioSpec
from data.prices import PriceService
from data.provider import common_history

router = APIRouter(prefix="/api", tags=["analysis"])


def _spec_from_weights(name: str, weights: dict[str, float], benchmark: str) -> PortfolioSpec:
    """Reuse a simulation's contribution flows; only the holdings/weights differ."""
    return PortfolioSpec(
        name=name,
        holdings=[Holding(sym, w) for sym, w in weights.items()],
        benchmark_symbol=benchmark,
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

    prices = prices_svc.get_adjusted_close(symbols, body.start)
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data for the requested holdings and window",
        )

    try:
        result = run_simulation(spec, prices, benchmark)
    except SimError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    sim = result.sim
    bench = result.benchmark_value
    series: list[SeriesPoint] = []
    for ts, row in sim.iterrows():
        series.append(
            SeriesPoint(
                date=ts.date(),
                value=float(row["value"]),
                invested=float(row["invested"]),
                benchmark=(float(bench.loc[ts]) if bench is not None else None),
            )
        )

    metrics: dict[str, dict[str, str]] = {spec.name: format_metrics(sim["twr_index"])}
    if result.has_benchmark and result.benchmark_index is not None:
        metrics[result.benchmark] = format_metrics(result.benchmark_index)

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
    )


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
