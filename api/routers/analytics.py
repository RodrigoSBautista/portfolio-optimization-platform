"""Forward-looking + multi-asset analytics endpoints.

Pure HTTP orchestration: fetch prices via ``data.prices.PriceService``, then delegate
all finance math to the framework-free ``app.analytics`` / ``core.projection``. No math
is implemented here. Auth-gated like every other router; bad market data -> 422 (never a
500), and floats are NaN-sanitized so the JSON always parses in the browser.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_price_service
from api.schemas import (
    ContributedPoint,
    DiversificationRequest,
    DiversificationResponse,
    FrontierRequest,
    FrontierResponse,
    ProjectBandPoint,
    ProjectRequest,
    ProjectResponse,
    RetirementRequest,
    RetirementResponse,
    TerminalPercentiles,
)
from app.analytics import (
    AnalyticsError,
    diversification,
    efficient_frontier,
    monthly_contribution_from_spec,
    portfolio_daily_returns,
)
from core.projection import project_monte_carlo, simulate_withdrawals
from data.prices import PriceService

router = APIRouter(prefix="/api", tags=["analytics"])


def _lookback_start(lookback_years: int) -> date:
    """Jan-1-ish window start ``lookback_years`` before today (mirrors /optimize)."""
    today = date.today()
    return date(today.year - max(lookback_years, 1), today.month, 1)


def _month_labels(n: int) -> list[str]:
    """``n`` consecutive ``"YYYY-MM"`` labels starting at the current month."""
    base = pd.Timestamp(date.today()).to_period("M")
    return [str(base + m) for m in range(n)]


def _safe(value: float) -> float:
    """Replace NaN/inf with 0.0 for percentile bands (keeps JSON valid + charts sane)."""
    return 0.0 if value is None or not math.isfinite(value) else float(value)


def _band_points(bands: pd.DataFrame) -> list[ProjectBandPoint]:
    labels = _month_labels(len(bands))
    return [
        ProjectBandPoint(
            date=labels[i],
            p5=_safe(row["p5"]),
            p25=_safe(row["p25"]),
            p50=_safe(row["p50"]),
            p75=_safe(row["p75"]),
            p95=_safe(row["p95"]),
        )
        for i, (_, row) in enumerate(bands.iterrows())
    ]


def _percentiles(d: dict[str, float]) -> TerminalPercentiles:
    return TerminalPercentiles(
        p5=_safe(d["p5"]),
        p25=_safe(d["p25"]),
        p50=_safe(d["p50"]),
        p75=_safe(d["p75"]),
        p95=_safe(d["p95"]),
    )


def _portfolio_returns(spec, prices_svc: PriceService, lookback_years: int) -> pd.Series:
    """Fetch the spec's holdings over the lookback and derive TWR daily returns (422)."""
    symbols = sorted({h.symbol.upper() for h in spec.holdings})
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Portfolio has no holdings",
        )
    prices = prices_svc.get_adjusted_close(symbols, _lookback_start(lookback_years))
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data for the requested holdings and window",
        )
    try:
        return portfolio_daily_returns(spec, prices)
    except AnalyticsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.post("/project", response_model=ProjectResponse)
def project(
    body: ProjectRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> ProjectResponse:
    """Block-bootstrap Monte Carlo projection of the spec's portfolio value forward."""
    spec = body.spec.to_spec()
    returns = _portfolio_returns(spec, prices_svc, body.lookback_years)
    monthly, escalation = monthly_contribution_from_spec(spec)

    try:
        result = project_monte_carlo(
            returns,
            years=body.years,
            n_paths=body.n_paths,
            seed=body.seed,
            start_value=body.start_value,
            monthly_contribution=monthly,
            escalation_pct=escalation,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    contrib_labels = _month_labels(len(result.contributed))
    contributed = [
        ContributedPoint(date=contrib_labels[i], value=_safe(float(v)))
        for i, v in enumerate(result.contributed.to_numpy())
    ]
    goal_prob = None
    if body.goal is not None:
        gp = result.goal_probability(body.goal)
        goal_prob = None if not math.isfinite(gp) else float(gp)

    return ProjectResponse(
        bands=_band_points(result.bands),
        terminal=_percentiles(result.terminal_percentiles),
        contributed=contributed,
        goal_probability=goal_prob,
        caveat=result.caveat,
    )


@router.post("/retirement", response_model=RetirementResponse)
def retirement(
    body: RetirementRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> RetirementResponse:
    """Monte Carlo withdrawal (sustainable-spending) analysis of the spec's portfolio."""
    wd = body.withdrawal
    if wd.kind == "fixed":
        if wd.amount is None or wd.amount < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="withdrawal.amount (monthly $) is required for kind='fixed'",
            )
        withdrawal, is_rate = float(wd.amount), False
    elif wd.kind == "rate":
        if wd.rate is None or wd.rate < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="withdrawal.rate (annual fraction, e.g. 0.04) is required "
                "for kind='rate'",
            )
        # Wire contract: `rate` is an annual FRACTION (0.04 = 4%-rule); the core
        # engine expects an annual PERCENT. Convert exactly once, here.
        withdrawal, is_rate = float(wd.rate) * 100.0, True
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="withdrawal.kind must be 'fixed' or 'rate'",
        )

    spec = body.spec.to_spec()
    returns = _portfolio_returns(spec, prices_svc, body.lookback_years)

    try:
        result = simulate_withdrawals(
            returns,
            start_balance=body.start_balance,
            years=body.years,
            withdrawal=withdrawal,
            withdrawal_is_rate=is_rate,
            inflation_pct=body.inflation_pct,
            n_paths=body.n_paths,
            seed=body.seed,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return RetirementResponse(
        success_rate=_safe(result.success_rate),
        bands=_band_points(result.bands),
        years_lasted=_percentiles(result.years_lasted_percentiles),
        caveat=result.caveat,
    )


@router.post("/frontier", response_model=FrontierResponse)
def frontier(
    body: FrontierRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> FrontierResponse:
    """Random-portfolio risk/return cloud + Pareto frontier + comparison markers."""
    tickers = sorted({t.upper() for t in body.tickers})
    prices = prices_svc.get_adjusted_close(tickers, _lookback_start(body.lookback_years))
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data for the requested tickers and window",
        )
    try:
        out = efficient_frontier(
            prices,
            n_samples=body.n_samples,
            seed=body.seed,
            extra_points=[p.model_dump() for p in body.extra_points],
        )
    except AnalyticsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return FrontierResponse(**out)


@router.post("/diversification", response_model=DiversificationResponse)
def diversification_route(
    body: DiversificationRequest,
    _=Depends(get_current_user),
    prices_svc: PriceService = Depends(get_price_service),
) -> DiversificationResponse:
    """Correlation matrix, hierarchical clusters, and risk contributions for a set."""
    tickers = sorted({t.upper() for t in body.tickers})
    prices = prices_svc.get_adjusted_close(tickers, _lookback_start(body.lookback_years))
    if prices.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No price data for the requested tickers and window",
        )
    try:
        out = diversification(prices, weights=body.weights)
    except AnalyticsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return DiversificationResponse(**out)
