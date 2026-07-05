"""Repository — the single gateway to the database.

**Per-user isolation lives here:** every portfolio read/write takes a ``user_id``
and filters by it, so a user can only ever touch their own data. The UI never
queries the ORM directly.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.portfolio import PortfolioSpec
from storage.models import (
    Contribution,
    DailyValuation,
    Holding,
    LotRow,
    Portfolio,
    User,
)


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- users ------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.session.add(user)
        self.session.flush()
        return user

    def get_user_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_user(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    # --- portfolios (always scoped by user_id) ----------------------------------

    # Eager-load child collections so callers can read holdings/contributions (and
    # convert via orm_to_spec) after the session closes, without DetachedInstanceError.
    _EAGER = (
        selectinload(Portfolio.holdings),
        selectinload(Portfolio.lots),
        selectinload(Portfolio.contributions),
    )

    def list_portfolios(self, user_id: int) -> list[Portfolio]:
        return list(
            self.session.scalars(
                select(Portfolio)
                .where(Portfolio.user_id == user_id)
                .order_by(Portfolio.name)
                .options(*self._EAGER)
            )
        )

    def get_portfolio(self, user_id: int, portfolio_id: int) -> Portfolio | None:
        """Return the portfolio only if it belongs to ``user_id`` (else None)."""
        return self.session.scalar(
            select(Portfolio)
            .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
            .options(*self._EAGER)
        )

    def save_portfolio(
        self, user_id: int, spec: PortfolioSpec, portfolio_id: int | None = None
    ) -> Portfolio:
        """Create a new portfolio for the user, or replace an existing one they own."""
        if portfolio_id is not None:
            portfolio = self.get_portfolio(user_id, portfolio_id)
            if portfolio is None:
                raise PermissionError("portfolio not found for this user")
        else:
            portfolio = Portfolio(user_id=user_id)
            self.session.add(portfolio)
        # Reassigning the collections below orphans any existing rows (delete-orphan
        # cascade), so an explicit clear() is unnecessary.

        portfolio.name = spec.name
        portfolio.benchmark_symbol = spec.benchmark_symbol
        portfolio.base_currency = spec.base_currency
        portfolio.holdings = [
            Holding(symbol=h.symbol.upper(), target_weight=h.weight) for h in spec.holdings
        ]
        # Dated purchases (lot-based specs); replaced wholesale like holdings.
        portfolio.lots = [
            LotRow(symbol=lot.symbol.upper(), purchase_date=lot.date, amount=lot.amount)
            for lot in spec.lots
        ]
        portfolio.contributions = [
            Contribution(
                kind=c.kind,
                amount=c.amount,
                frequency=c.frequency,
                start_date=c.start_date,
                end_date=c.end_date,
            )
            for c in spec.contributions
        ]
        self.session.flush()
        return portfolio

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> bool:
        portfolio = self.get_portfolio(user_id, portfolio_id)
        if portfolio is None:
            return False
        self.session.delete(portfolio)
        return True

    # --- daily valuations (idempotent upsert) -----------------------------------

    def upsert_valuation(
        self,
        user_id: int,
        portfolio_id: int,
        as_of: date,
        market_value: float,
        benchmark_value: float | None = None,
    ) -> DailyValuation:
        """Insert or update the valuation for (portfolio, date). Idempotent.

        Verifies the portfolio belongs to ``user_id`` first.
        """
        if self.get_portfolio(user_id, portfolio_id) is None:
            raise PermissionError("portfolio not found for this user")

        existing = self.session.scalar(
            select(DailyValuation).where(
                DailyValuation.portfolio_id == portfolio_id,
                DailyValuation.as_of_date == as_of,
            )
        )
        if existing is not None:
            existing.market_value = market_value
            # None means "not provided" -> keep any previously stored benchmark
            # rather than wiping it on a market-value-only refresh.
            if benchmark_value is not None:
                existing.benchmark_value = benchmark_value
            self.session.flush()
            return existing

        valuation = DailyValuation(
            portfolio_id=portfolio_id,
            as_of_date=as_of,
            market_value=market_value,
            benchmark_value=benchmark_value,
        )
        self.session.add(valuation)
        self.session.flush()
        return valuation

    def all_portfolio_refs(self) -> list[tuple[int, int]]:
        """(user_id, portfolio_id) for every portfolio — for the scheduled refresh job.

        Not user-facing: the daily job legitimately spans all users. User-facing reads
        still go through the user_id-scoped methods above.
        """
        rows = self.session.execute(select(Portfolio.user_id, Portfolio.id)).all()
        return [(int(user_id), int(pid)) for user_id, pid in rows]

    def get_valuations(self, user_id: int, portfolio_id: int) -> list[DailyValuation]:
        if self.get_portfolio(user_id, portfolio_id) is None:
            return []
        return list(
            self.session.scalars(
                select(DailyValuation)
                .where(DailyValuation.portfolio_id == portfolio_id)
                .order_by(DailyValuation.as_of_date)
            )
        )
