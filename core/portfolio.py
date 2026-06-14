"""Portfolio value objects — framework-free domain data.

A ``PortfolioSpec`` is the plain description of a portfolio (name, benchmark,
holdings, contribution plan) shared by the UI, the simulation, the storage layer,
and the client-side JSON export. It carries no framework or DB dependency, and its
``to_dict`` / ``from_dict`` define the canonical serialized shape (versioned).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import date

SPEC_VERSION = 1
LUMP_SUM = "lump_sum"
RECURRING = "recurring"


@dataclass(frozen=True)
class Holding:
    symbol: str
    weight: float


@dataclass(frozen=True)
class Contribution:
    kind: str  # LUMP_SUM or RECURRING
    amount: float
    frequency: str | None = None  # e.g. "monthly" for RECURRING; None for LUMP_SUM
    start_date: date | None = None
    end_date: date | None = None


@dataclass
class PortfolioSpec:
    name: str
    holdings: list[Holding] = field(default_factory=list)
    benchmark_symbol: str = "SPY"
    base_currency: str = "USD"
    contributions: list[Contribution] = field(default_factory=list)

    def weights(self) -> dict[str, float]:
        """Raw target weights keyed by upper-cased symbol (unnormalized)."""
        return {h.symbol.upper(): h.weight for h in self.holdings}

    def simulation_kwargs(self) -> dict:
        """Translate the contribution plan into ``simulate_portfolio`` arguments."""
        lump = sum(c.amount for c in self.contributions if c.kind == LUMP_SUM)
        recurring = next((c for c in self.contributions if c.kind == RECURRING), None)
        return {
            "lump_sum": float(lump),
            "recurring_amount": recurring.amount if recurring else 0.0,
            "recurring_freq": recurring.frequency if recurring else None,
        }

    def to_dict(self) -> dict:
        return {
            "version": SPEC_VERSION,
            "name": self.name,
            "benchmark_symbol": self.benchmark_symbol,
            "base_currency": self.base_currency,
            "holdings": [{"symbol": h.symbol.upper(), "weight": h.weight} for h in self.holdings],
            "contributions": [_contribution_to_dict(c) for c in self.contributions],
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> PortfolioSpec:
        return cls(
            name=data["name"],
            benchmark_symbol=data.get("benchmark_symbol", "SPY"),
            base_currency=data.get("base_currency", "USD"),
            holdings=[
                Holding(h["symbol"].upper(), float(h["weight"]))
                for h in data.get("holdings", [])
            ],
            contributions=[
                _contribution_from_dict(c) for c in data.get("contributions", [])
            ],
        )


def _contribution_to_dict(c: Contribution) -> dict:
    out = asdict(c)
    out["start_date"] = c.start_date.isoformat() if c.start_date else None
    out["end_date"] = c.end_date.isoformat() if c.end_date else None
    return out


def _contribution_from_dict(data: Mapping) -> Contribution:
    return Contribution(
        kind=data["kind"],
        amount=float(data["amount"]),
        frequency=data.get("frequency"),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
    )


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None
