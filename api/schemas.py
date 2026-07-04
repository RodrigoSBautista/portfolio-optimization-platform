"""Pydantic v2 DTOs for the API + DTO<->PortfolioSpec conversion.

The portfolio DTO mirrors ``core.portfolio.PortfolioSpec`` exactly; conversion reuses
the canonical ``to_dict``/``from_dict`` so the serialized shape stays single-sourced.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

from core.portfolio import PortfolioSpec


def _validate_long_only(weights: dict[str, float] | None) -> dict[str, float] | None:
    """Reject negative weights — this is a long-only project (matches core)."""
    if weights is not None and any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative (long-only)")
    return weights

# --- auth -----------------------------------------------------------------------


class Credentials(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str


# --- tickers --------------------------------------------------------------------


class TickerOut(BaseModel):
    symbol: str
    name: str


# --- portfolio spec -------------------------------------------------------------


class HoldingDTO(BaseModel):
    symbol: str
    weight: float


class ContributionDTO(BaseModel):
    kind: str  # "lump_sum" | "recurring"
    amount: float
    frequency: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class PortfolioSpecDTO(BaseModel):
    name: str
    benchmark_symbol: str = "SPY"
    base_currency: str = "USD"
    holdings: list[HoldingDTO] = Field(default_factory=list)
    contributions: list[ContributionDTO] = Field(default_factory=list)

    def to_spec(self) -> PortfolioSpec:
        return PortfolioSpec.from_dict(self.model_dump(mode="json"))

    @classmethod
    def from_spec(cls, spec: PortfolioSpec) -> PortfolioSpecDTO:
        data = spec.to_dict()
        data.pop("version", None)
        return cls.model_validate(data)


class PortfolioOut(PortfolioSpecDTO):
    id: int


# --- simulate -------------------------------------------------------------------


class SimulateRequest(BaseModel):
    spec: PortfolioSpecDTO
    start: date
    benchmark: str | None = None
    # New optional analytics fields (all backward-compatible defaults).
    end: date | None = None  # window end (YYYY-MM-DD) so crisis windows work
    rebalance: str | None = None  # "monthly" | "quarterly" | "annually" | None
    risk_free_rate: float = 0.04  # FRACTION (0.04 = 4%/yr) for Sharpe/Sortino
    inflation_pct: float | None = None  # PERCENT (2.5 = 2.5%/yr); enables real values
    escalation_pct: float = 0.0  # PERCENT annual growth of the recurring contribution
    annual_fee_pct: float = 0.0  # PERCENT advisory-fee drag
    include_analytics: bool = False  # attach drawdown + rolling series


class SeriesPoint(BaseModel):
    date: date
    value: float
    invested: float
    benchmark: float | None = None
    real_value: float | None = None  # inflation-adjusted value (null unless requested)


class DrawdownPoint(BaseModel):
    date: date
    pct: float  # twr_index/cummax - 1 (<= 0)


class RollingPoint(BaseModel):
    date: date
    ret_1y: float | None = None  # 252-day compounded return (null until window fills)
    vol_1y: float | None = None  # annualized vol of 252-day daily returns


class SimulateResponse(BaseModel):
    series: list[SeriesPoint]
    metrics: dict[str, dict[str, str]]
    final_value: float
    invested: float
    gain_pct: float
    dropped: list[str]
    benchmark: str
    real_final_value: float | None = None  # null unless inflation_pct set
    drawdown: list[DrawdownPoint] | None = None  # null unless include_analytics
    rolling: list[RollingPoint] | None = None  # null unless include_analytics


# --- optimize -------------------------------------------------------------------


class OptimizeRequest(BaseModel):
    mode: str  # "allocate" | "select"
    method: str  # ALWAYS the allocation method (e.g. "Risk parity")
    tickers: list[str] = Field(default_factory=list)  # allocate mode
    candidates: list[str] = Field(default_factory=list)  # select mode
    k: int | None = None  # select mode: number of holdings to keep
    selection_method: str | None = None  # select mode: the selection method
    lookback_years: int = 5
    max_weight: float | None = None
    benchmark: str = "SPY"


class ComparisonPoint(BaseModel):
    date: date
    suggested: float
    equal_weight: float | None = None  # null when a date is missing (not NaN)
    benchmark: float | None = None


class OptimizeResponse(BaseModel):
    selected: list[str]
    suggested: dict[str, float]
    baseline: dict[str, float]
    comparison_series: list[ComparisonPoint]
    metrics: dict[str, dict[str, str]]


# --- compare --------------------------------------------------------------------


class CompareRequest(BaseModel):
    portfolio_ids: list[int] = Field(min_length=2, max_length=3)
    start: date
    benchmark: str = "SPY"


class ValueSeriesPoint(BaseModel):
    date: date
    value: float


class CompareResult(BaseModel):
    id: int
    name: str
    series: list[ValueSeriesPoint]
    final_value: float
    invested: float
    metrics: dict[str, str]
    # Holdings that returned no price data in the shared window (parity with
    # SimulateResponse.dropped); e.g. a delisted ticker silently drops out.
    dropped: list[str] = Field(default_factory=list)


class CompareResponse(BaseModel):
    results: list[CompareResult]
    benchmark_series: list[ValueSeriesPoint] | None = None
    benchmark_metrics: dict[str, str] | None = None


# --- tracking (valuations + refresh) --------------------------------------------


class ValuationPoint(BaseModel):
    date: date
    market_value: float
    benchmark_value: float | None = None


class ValuationsResponse(BaseModel):
    valuations: list[ValuationPoint]


class RefreshRequest(BaseModel):
    start: date | None = None


class RefreshResponse(BaseModel):
    written: int


# --- project (Monte Carlo accumulation) -----------------------------------------


class ProjectRequest(BaseModel):
    spec: PortfolioSpecDTO
    years: int = Field(ge=1, le=50)
    n_paths: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    goal: float | None = None
    start_value: float = Field(gt=0)
    lookback_years: int = Field(default=10, ge=1, le=50)


class ProjectBandPoint(BaseModel):
    date: str  # "YYYY-MM"
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class TerminalPercentiles(BaseModel):
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class ContributedPoint(BaseModel):
    date: str  # "YYYY-MM"
    value: float  # cumulative money in, including the starting balance


class ProjectResponse(BaseModel):
    bands: list[ProjectBandPoint]
    terminal: TerminalPercentiles
    contributed: list[ContributedPoint]
    goal_probability: float | None = None
    caveat: str


# --- retirement (withdrawal / drawdown) -----------------------------------------


class WithdrawalDTO(BaseModel):
    kind: str  # "fixed" | "rate"
    amount: float | None = None  # monthly $ when kind="fixed"
    # Annual FRACTION when kind="rate" (0.04 = the 4% rule). The route converts to
    # the percent units the core engine expects — the wire contract is fractional.
    rate: float | None = None


class RetirementRequest(BaseModel):
    spec: PortfolioSpecDTO
    start_balance: float = Field(gt=0)
    years: int = Field(ge=1, le=60)
    withdrawal: WithdrawalDTO
    inflation_pct: float = 2.5
    n_paths: int = Field(default=1000, ge=1, le=5000)
    seed: int = 42
    lookback_years: int = Field(default=10, ge=1, le=50)


class RetirementResponse(BaseModel):
    success_rate: float
    bands: list[ProjectBandPoint]
    years_lasted: TerminalPercentiles
    caveat: str


# --- frontier (efficient frontier cloud) ----------------------------------------


class ExtraPoint(BaseModel):
    label: str
    weights: dict[str, float]

    _long_only = field_validator("weights")(_validate_long_only)


class FrontierRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=30)
    lookback_years: int = Field(default=3, ge=1, le=50)
    n_samples: int = Field(default=2000, ge=1, le=5000)
    seed: int = 42
    risk_free_rate: float = 0.04
    extra_points: list[ExtraPoint] = Field(default_factory=list)


class RiskReturnPoint(BaseModel):
    vol: float
    ret: float


class FrontierMarker(BaseModel):
    label: str
    vol: float
    ret: float


class FrontierResponse(BaseModel):
    cloud: list[RiskReturnPoint]
    frontier: list[RiskReturnPoint]
    markers: list[FrontierMarker]


# --- diversification (correlation / clusters / risk) ----------------------------


class DiversificationRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=30)
    lookback_years: int = Field(default=3, ge=1, le=50)
    weights: dict[str, float] | None = None

    _long_only = field_validator("weights")(_validate_long_only)


class CorrelationMatrix(BaseModel):
    tickers: list[str]
    values: list[list[float]]


class ClusterOut(BaseModel):
    label: str
    members: list[str]


class RiskContribution(BaseModel):
    ticker: str
    pct: float


class DiversificationResponse(BaseModel):
    matrix: CorrelationMatrix
    clusters: list[ClusterOut]
    risk_contributions: list[RiskContribution]
