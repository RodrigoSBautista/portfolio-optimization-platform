"""SQLAlchemy ORM models (SQLite now -> PostgreSQL later, no rewrite).

Portability rules: integer surrogate PKs; UTC timezone-aware timestamps; portable
column types only. Per-user isolation is enforced in ``repository.py``, which always
filters by ``user_id``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    portfolios: Mapped[list[Portfolio]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    benchmark_symbol: Mapped[str] = mapped_column(String(16), default="SPY")
    base_currency: Mapped[str] = mapped_column(String(8), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="portfolios")
    holdings: Mapped[list[Holding]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    lots: Mapped[list[LotRow]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    contributions: Mapped[list[Contribution]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    valuations: Mapped[list[DailyValuation]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(16))
    target_weight: Mapped[float] = mapped_column(Float)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")


class LotRow(Base):
    """A single dated purchase (``amount`` dollars of ``symbol`` on ``purchase_date``).

    The persisted form of ``core.portfolio.Lot``. Mirrors ``Holding``: a child of a
    portfolio, replaced wholesale on save (delete-orphan cascade). A portfolio is
    either weight-based (holdings) or lot-based (lots) — the spec decides via
    ``is_lot_based``; the schema simply stores whichever is present.
    """

    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(16))
    purchase_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)

    portfolio: Mapped[Portfolio] = relationship(back_populates="lots")


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # "lump_sum" | "recurring"
    amount: Mapped[float] = mapped_column(Float)
    frequency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="contributions")


class DailyValuation(Base):
    __tablename__ = "daily_valuations"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "as_of_date", name="uq_valuation_portfolio_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    as_of_date: Mapped[date] = mapped_column(Date)
    market_value: Mapped[float] = mapped_column(Float)
    benchmark_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="valuations")
