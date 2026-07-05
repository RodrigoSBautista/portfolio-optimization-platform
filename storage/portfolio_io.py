"""Portfolio JSON export/import + ORM<->spec mapping.

The JSON export is the **client-side "save on your computer"** path (see
``docs/PLAN.md``): a user downloads their portfolio as JSON and re-imports it later
to restore it — durable even though Streamlit Cloud's filesystem is ephemeral, and
no account is required. ``orm_to_spec`` / round-tripping bridges the DB and the spec.
"""

from __future__ import annotations

import json

from core.portfolio import Contribution, Holding, Lot, PortfolioSpec
from storage.models import Portfolio


def export_json(spec: PortfolioSpec, *, indent: int = 2) -> str:
    """Serialize a portfolio spec to a JSON string for download."""
    return json.dumps(spec.to_dict(), indent=indent)


def import_json(text: str) -> PortfolioSpec:
    """Parse a previously exported JSON string back into a portfolio spec."""
    data = json.loads(text)
    if not isinstance(data, dict) or "name" not in data:
        raise ValueError("not a valid portfolio file")
    return PortfolioSpec.from_dict(data)


def orm_to_spec(portfolio: Portfolio) -> PortfolioSpec:
    """Map a stored ORM portfolio to the framework-free spec."""
    return PortfolioSpec(
        name=portfolio.name,
        benchmark_symbol=portfolio.benchmark_symbol,
        base_currency=portfolio.base_currency,
        holdings=[Holding(h.symbol.upper(), h.target_weight) for h in portfolio.holdings],
        lots=[Lot(lot.symbol.upper(), lot.purchase_date, lot.amount) for lot in portfolio.lots],
        contributions=[
            Contribution(
                kind=c.kind,
                amount=c.amount,
                frequency=c.frequency,
                start_date=c.start_date,
                end_date=c.end_date,
            )
            for c in portfolio.contributions
        ],
    )
