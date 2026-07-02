"""Pydantic v2 DTOs for the API + DTO<->PortfolioSpec conversion.

The portfolio DTO mirrors ``core.portfolio.PortfolioSpec`` exactly; conversion reuses
the canonical ``to_dict``/``from_dict`` so the serialized shape stays single-sourced.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from core.portfolio import PortfolioSpec

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


class SeriesPoint(BaseModel):
    date: date
    value: float
    invested: float
    benchmark: float | None = None


class SimulateResponse(BaseModel):
    series: list[SeriesPoint]
    metrics: dict[str, dict[str, str]]
    final_value: float
    invested: float
    gain_pct: float
    dropped: list[str]
    benchmark: str


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
