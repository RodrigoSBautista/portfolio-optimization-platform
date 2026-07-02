"""Daily valuation refresh — idempotent.

Computes a saved portfolio's value (and its benchmark's value, with identical
contributions for an apples-to-apples line) over a tracking window and upserts one
row per trading day into ``daily_valuations``. Re-running is safe: the upsert keys on
(portfolio_id, as_of_date), so days are updated in place rather than duplicated, and
market-closed days simply don't appear in the price data.

Phase 1: invoked locally by the tracking dashboard's "Refresh now" button and by the
``main()`` CLI below. Production: a GitHub Actions cron runs the same CLI against the
hosted database.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from core.portfolio import PortfolioSpec
from core.simulation import simulate_portfolio
from data.prices import PriceService
from data.provider import common_history
from storage.db import create_db_engine, make_session_factory, session_scope
from storage.portfolio_io import orm_to_spec
from storage.repository import Repository


def build_valuations(
    spec: PortfolioSpec, port_prices: pd.DataFrame, bench_prices: pd.DataFrame
) -> pd.DataFrame:
    """Return a [date x (market_value, benchmark_value)] frame for the spec.

    Only the tickers present in ``port_prices`` are weighted: a holding that returned
    no price data (delisted/invalid) is dropped so ``simulate_portfolio`` never sees a
    weight without a matching column. Mirrors ``app.sim_runner.run_simulation``.
    """
    kwargs = spec.simulation_kwargs()
    weights = {s: w for s, w in spec.weights().items() if s in port_prices.columns}
    portfolio = simulate_portfolio(port_prices, weights, **kwargs)
    benchmark = simulate_portfolio(bench_prices, {spec.benchmark_symbol.upper(): 1.0}, **kwargs)
    frame = pd.DataFrame(
        {"market_value": portfolio["value"], "benchmark_value": benchmark["value"]}
    )
    return frame.dropna()


def refresh_portfolio(
    repo: Repository,
    prices: PriceService,
    user_id: int,
    portfolio_id: int,
    spec: PortfolioSpec,
    start: date,
    end: date | None = None,
) -> int:
    """Compute and upsert daily valuations for one portfolio. Returns rows written."""
    symbols = sorted({h.symbol.upper() for h in spec.holdings})
    benchmark = spec.benchmark_symbol.upper()
    # Dedupe the request (the benchmark may also be a holding) and drop any duplicated
    # columns the provider returns — duplicate labels make single-ticker slices 2-D.
    tickers = list(dict.fromkeys([*symbols, benchmark]))
    frame = prices.get_adjusted_close(tickers, start, end)
    if frame.empty:
        return 0
    frame = frame.loc[:, ~frame.columns.duplicated()]

    available = [s for s in symbols if s in frame.columns]
    if benchmark not in frame.columns or not available:
        return 0

    # Align holdings + benchmark to one common window so both simulations share the
    # same dates and contribution schedule (apples-to-apples). Dedupe columns: when a
    # portfolio HOLDS its own benchmark (e.g. SPY vs SPY), [*available, benchmark]
    # repeats the ticker and aligned[[benchmark]] would come back 2-D.
    cols = list(dict.fromkeys([*available, benchmark]))
    aligned = common_history(frame[cols])
    if aligned.empty:
        return 0

    valuations = build_valuations(spec, aligned[available], aligned[[benchmark]])
    for ts, row in valuations.iterrows():
        repo.upsert_valuation(
            user_id,
            portfolio_id,
            ts.date(),
            float(row["market_value"]),
            float(row["benchmark_value"]),
        )
    return len(valuations)


def main(start: date | None = None) -> None:
    """Refresh every saved portfolio (CLI / cron entry point)."""
    start = start or date(date.today().year - 5, 1, 1)
    factory = make_session_factory(create_db_engine())
    prices = PriceService()
    with session_scope(factory) as session:
        repo = Repository(session)
        refs = repo.all_portfolio_refs()
        total = 0
        for user_id, portfolio_id in refs:
            portfolio = repo.get_portfolio(user_id, portfolio_id)
            if portfolio is None:
                continue
            total += refresh_portfolio(
                repo, prices, user_id, portfolio_id, orm_to_spec(portfolio), start
            )
    print(f"Refreshed {len(refs)} portfolio(s); wrote {total} valuation rows.")


if __name__ == "__main__":
    main()
