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

SPEC_VERSION = 2
LUMP_SUM = "lump_sum"
RECURRING = "recurring"


@dataclass(frozen=True)
class Holding:
    symbol: str
    weight: float


@dataclass(frozen=True)
class Lot:
    """A single dated purchase: ``amount`` dollars of ``symbol`` bought on ``date``.

    Real portfolios are built over time — each position has its own purchase date
    and dollar amount, and entry timing drives actual performance. A lot-based spec
    is a list of these, consumed by ``core.simulation.simulate_lots``.
    """

    symbol: str
    date: date
    amount: float


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
    lots: list[Lot] = field(default_factory=list)

    @property
    def is_lot_based(self) -> bool:
        """True when this spec describes dated purchases rather than target weights."""
        return bool(self.lots)

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
            "lots": [_lot_to_dict(lot) for lot in self.lots],
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
            # Backward compatible: v1 payloads have no "lots" key -> empty list.
            lots=[_lot_from_dict(lot) for lot in data.get("lots", [])],
        )


def weights_from_amounts(amounts: Mapping[str, float]) -> tuple[dict[str, float], float]:
    """Convert per-ticker dollar amounts into normalized weights + the total.

    Ignores non-positive amounts. Returns ``({}, 0.0)`` when nothing positive is given.
    """
    cleaned = {k.upper(): float(v) for k, v in amounts.items() if float(v) > 0}
    total = sum(cleaned.values())
    if total <= 0:
        return {}, 0.0
    return {k: v / total for k, v in cleaned.items()}, total


def _contribution_to_dict(c: Contribution) -> dict:
    out = asdict(c)
    out["start_date"] = c.start_date.isoformat() if c.start_date else None
    out["end_date"] = c.end_date.isoformat() if c.end_date else None
    return out


def _lot_to_dict(lot: Lot) -> dict:
    return {
        "symbol": lot.symbol.upper(),
        "date": lot.date.isoformat(),
        "amount": float(lot.amount),
    }


def _lot_from_dict(data: Mapping) -> Lot:
    return Lot(
        symbol=data["symbol"].upper(),
        date=date.fromisoformat(data["date"]),
        amount=float(data["amount"]),
    )


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
