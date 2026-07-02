"""Compare + tracking endpoints — all scoped to the token's user.

Pure HTTP orchestration: fetch prices via ``data.prices.PriceService``, then delegate
all finance math to the framework-free ``app.sim_runner`` and ``jobs.refresh``. No math
is implemented here. Per-user isolation is enforced by ``Repository`` (every call passes
``user.id``), so a user can never touch another user's portfolios or valuations.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_price_service, get_repository
from api.schemas import (
    CompareRequest,
    CompareResponse,
    CompareResult,
    RefreshRequest,
    RefreshResponse,
    ValuationPoint,
    ValuationsResponse,
    ValueSeriesPoint,
)
from app.sim_runner import SimError, format_metrics, run_simulation
from core.portfolio import PortfolioSpec
from data.prices import PriceService
from data.provider import common_history
from jobs.refresh import refresh_portfolio
from storage.models import User
from storage.portfolio_io import orm_to_spec
from storage.repository import Repository

router = APIRouter(prefix="/api", tags=["compare", "tracking"])


@router.post("/compare", response_model=CompareResponse)
def compare(
    body: CompareRequest,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
    prices_svc: PriceService = Depends(get_price_service),
) -> CompareResponse:
    """Compare 2–3 saved portfolios over one shared window vs a shared benchmark.

    Fairness: every ticker (all holdings of every selected portfolio + the benchmark)
    is fetched in one call and aligned to a single common window, so every portfolio is
    simulated over the *same date range*. Each portfolio still uses its own saved
    contribution schedule, so ``invested`` matches only across portfolios whose schedules
    coincide. ``benchmark_series`` is simulated with the FIRST portfolio's schedule, so
    its dollar line lines up only with portfolios sharing that schedule (the benchmark's
    return metrics are schedule-independent). Mirrors the logic in ``app/views/compare.py``.
    """
    benchmark = body.benchmark.upper()

    # Reject duplicate ids: [5, 5] is not a real 2-way comparison.
    if len(set(body.portfolio_ids)) != len(body.portfolio_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="portfolio_ids must be distinct",
        )

    # Load each portfolio (404 on any id the caller doesn't own).
    ordered: list[tuple[int, PortfolioSpec]] = []
    for pid in body.portfolio_ids:
        orm = repo.get_portfolio(user.id, pid)
        if orm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio {pid} not found"
            )
        ordered.append((pid, orm_to_spec(orm)))

    # Fetch every ticker once, then align all portfolios + benchmark to ONE window.
    all_tickers = {benchmark}
    for _pid, spec in ordered:
        all_tickers |= {h.symbol.upper() for h in spec.holdings}
    prices = prices_svc.get_adjusted_close(sorted(all_tickers), body.start)
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data returned for these tickers.",
        )
    present = [t for t in sorted(all_tickers) if t in prices.columns]
    aligned = common_history(prices[present])
    if aligned.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No overlapping price window across all portfolios + benchmark.",
        )

    results: list[CompareResult] = []
    benchmark_series: list[ValueSeriesPoint] | None = None
    benchmark_metrics: dict[str, str] | None = None
    for pid, spec in ordered:
        try:
            res = run_simulation(spec, aligned, benchmark=benchmark)
        except SimError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{spec.name}: {exc}"
            ) from exc

        series = [
            ValueSeriesPoint(date=ts.date(), value=float(val))
            for ts, val in res.sim["value"].items()
        ]
        results.append(
            CompareResult(
                id=pid,
                name=spec.name,
                series=series,
                final_value=res.final_value,
                invested=res.invested,
                metrics=format_metrics(res.sim["twr_index"]),
                dropped=res.dropped,
            )
        )
        # The benchmark is identical across portfolios (shared window/flows): build once.
        if benchmark_series is None and res.benchmark_value is not None:
            benchmark_series = [
                ValueSeriesPoint(date=ts.date(), value=float(val))
                for ts, val in res.benchmark_value.items()
            ]
            if res.benchmark_index is not None:
                benchmark_metrics = format_metrics(res.benchmark_index)

    return CompareResponse(
        results=results,
        benchmark_series=benchmark_series,
        benchmark_metrics=benchmark_metrics,
    )


@router.get("/portfolios/{portfolio_id}/valuations", response_model=ValuationsResponse)
def get_valuations(
    portfolio_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> ValuationsResponse:
    if repo.get_portfolio(user.id, portfolio_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    valuations = [
        ValuationPoint(
            date=v.as_of_date,
            market_value=float(v.market_value),
            benchmark_value=(None if v.benchmark_value is None else float(v.benchmark_value)),
        )
        for v in repo.get_valuations(user.id, portfolio_id)
    ]
    return ValuationsResponse(valuations=valuations)


@router.post("/portfolios/{portfolio_id}/refresh", response_model=RefreshResponse)
def refresh(
    portfolio_id: int,
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
    prices_svc: PriceService = Depends(get_price_service),
) -> RefreshResponse:
    orm = repo.get_portfolio(user.id, portfolio_id)
    if orm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    # Default window matches the Streamlit tracking default: Jan 1 three years ago.
    start = (body.start if body and body.start else None) or date(date.today().year - 3, 1, 1)
    try:
        written = refresh_portfolio(
            repo, prices_svc, user.id, portfolio_id, orm_to_spec(orm), start
        )
    except ValueError as exc:
        # Belt: the source now filters price-less holdings, but any residual simulation
        # error (e.g. degenerate window) is a 422, not an unhandled 500.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return RefreshResponse(written=written)
