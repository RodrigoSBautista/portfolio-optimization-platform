"""Storage tests — in-memory SQLite. Focus: per-user isolation + upsert idempotency."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine

from core.portfolio import Contribution, Holding, Lot, PortfolioSpec
from storage.db import make_session_factory, session_scope
from storage.models import Base
from storage.portfolio_io import export_json, import_json, orm_to_spec
from storage.repository import Repository


@pytest.fixture
def session():
    engine = create_engine("sqlite://", future=True)  # in-memory
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    sess = factory()
    yield sess
    sess.close()


@pytest.fixture
def repo(session):
    return Repository(session)


def _spec(name="My Portfolio"):
    return PortfolioSpec(
        name=name,
        holdings=[Holding("AAPL", 0.6), Holding("MSFT", 0.4)],
        benchmark_symbol="SPY",
        contributions=[Contribution(kind="lump_sum", amount=1000.0)],
    )


def _lot_spec(name="Lot Portfolio"):
    return PortfolioSpec(
        name=name,
        benchmark_symbol="SPY",
        lots=[
            Lot("AAPL", date(2021, 1, 4), 1000.0),
            Lot("MSFT", date(2021, 6, 1), 500.0),
        ],
    )


# --- users ----------------------------------------------------------------------

def test_create_and_fetch_user(repo):
    user = repo.create_user("alice", "hash")
    assert user.id is not None
    assert repo.get_user_by_username("alice").id == user.id


# --- save/list/get portfolios ---------------------------------------------------

def test_save_and_reload_portfolio(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _spec())
    reloaded = repo.get_portfolio(user.id, p.id)
    assert reloaded.name == "My Portfolio"
    assert {h.symbol for h in reloaded.holdings} == {"AAPL", "MSFT"}
    assert reloaded.contributions[0].amount == 1000.0


def test_save_with_id_replaces_holdings(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _spec())
    new_spec = PortfolioSpec(name="Renamed", holdings=[Holding("VOO", 1.0)])
    repo.save_portfolio(user.id, new_spec, portfolio_id=p.id)
    reloaded = repo.get_portfolio(user.id, p.id)
    assert reloaded.name == "Renamed"
    assert [h.symbol for h in reloaded.holdings] == ["VOO"]


# --- lot-based portfolios -------------------------------------------------------

def test_save_and_reload_lot_portfolio(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _lot_spec())
    reloaded = repo.get_portfolio(user.id, p.id)
    assert reloaded.holdings == []  # lot-based: no weight holdings
    assert {(lot.symbol, lot.purchase_date, lot.amount) for lot in reloaded.lots} == {
        ("AAPL", date(2021, 1, 4), 1000.0),
        ("MSFT", date(2021, 6, 1), 500.0),
    }


def test_orm_to_spec_round_trip_lots(repo):
    user = repo.create_user("alice", "h")
    spec = _lot_spec()
    p = repo.save_portfolio(user.id, spec)
    restored = orm_to_spec(p)
    assert restored.is_lot_based
    assert restored.to_dict() == spec.to_dict()


def test_save_replaces_lots_on_update(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _lot_spec())
    new_spec = PortfolioSpec(name="Reworked", lots=[Lot("VOO", date(2022, 3, 1), 250.0)])
    repo.save_portfolio(user.id, new_spec, portfolio_id=p.id)
    reloaded = repo.get_portfolio(user.id, p.id)
    assert [(lot.symbol, lot.amount) for lot in reloaded.lots] == [("VOO", 250.0)]


def test_lot_json_round_trip():
    spec = _lot_spec()
    restored = import_json(export_json(spec))
    assert restored.to_dict() == spec.to_dict()
    assert [(lot.symbol, lot.date, lot.amount) for lot in restored.lots] == [
        ("AAPL", date(2021, 1, 4), 1000.0),
        ("MSFT", date(2021, 6, 1), 500.0),
    ]


def test_user_cannot_read_another_users_lot_portfolio(repo):
    alice = repo.create_user("alice", "h")
    bob = repo.create_user("bob", "h")
    p = repo.save_portfolio(alice.id, _lot_spec("Alice lots"))
    assert repo.get_portfolio(bob.id, p.id) is None
    assert repo.list_portfolios(bob.id) == []


# --- per-user isolation (the critical guarantee) --------------------------------

def test_user_cannot_read_another_users_portfolio(repo):
    alice = repo.create_user("alice", "h")
    bob = repo.create_user("bob", "h")
    p = repo.save_portfolio(alice.id, _spec("Alice fund"))

    # Bob cannot see Alice's portfolio by id...
    assert repo.get_portfolio(bob.id, p.id) is None
    # ...nor does it appear in his list...
    assert repo.list_portfolios(bob.id) == []
    # ...and Alice still sees exactly her own.
    assert [x.id for x in repo.list_portfolios(alice.id)] == [p.id]


def test_user_cannot_overwrite_another_users_portfolio(repo):
    alice = repo.create_user("alice", "h")
    bob = repo.create_user("bob", "h")
    p = repo.save_portfolio(alice.id, _spec())
    with pytest.raises(PermissionError):
        repo.save_portfolio(bob.id, _spec("hijack"), portfolio_id=p.id)


def test_delete_only_affects_owner(repo):
    alice = repo.create_user("alice", "h")
    bob = repo.create_user("bob", "h")
    p = repo.save_portfolio(alice.id, _spec())
    assert repo.delete_portfolio(bob.id, p.id) is False  # not bob's
    assert repo.delete_portfolio(alice.id, p.id) is True


# --- valuations: idempotent upsert ---------------------------------------------

def test_upsert_valuation_is_idempotent(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _spec())
    day = date(2024, 1, 2)

    repo.upsert_valuation(user.id, p.id, day, 1000.0, 999.0)
    repo.upsert_valuation(user.id, p.id, day, 1010.0, 1001.0)  # same date -> update

    vals = repo.get_valuations(user.id, p.id)
    assert len(vals) == 1  # no duplicate row
    assert vals[0].market_value == 1010.0


def test_upsert_valuation_rejects_foreign_portfolio(repo):
    alice = repo.create_user("alice", "h")
    bob = repo.create_user("bob", "h")
    p = repo.save_portfolio(alice.id, _spec())
    with pytest.raises(PermissionError):
        repo.upsert_valuation(bob.id, p.id, date(2024, 1, 2), 1.0)


def test_upsert_preserves_benchmark_on_partial_update(repo):
    user = repo.create_user("alice", "h")
    p = repo.save_portfolio(user.id, _spec())
    day = date(2024, 1, 2)
    repo.upsert_valuation(user.id, p.id, day, 1000.0, 999.0)
    repo.upsert_valuation(user.id, p.id, day, 1010.0)  # benchmark omitted

    vals = repo.get_valuations(user.id, p.id)
    assert vals[0].market_value == 1010.0
    assert vals[0].benchmark_value == 999.0  # preserved, not wiped to NULL


def test_orm_to_spec_safe_after_session_closes():
    # Reproduces the detached-instance trap: fetch in a session_scope, then read
    # holdings/contributions AFTER it closes. Eager loading must prevent a raise.
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    with session_scope(factory) as s:
        user = Repository(s).create_user("alice", "h")
        Repository(s).save_portfolio(user.id, _spec())
        uid = user.id

    with session_scope(factory) as s:
        portfolio = Repository(s).list_portfolios(uid)[0]

    spec = orm_to_spec(portfolio)  # session already closed
    assert {h.symbol for h in spec.holdings} == {"AAPL", "MSFT"}
    assert spec.contributions[0].amount == 1000.0


# --- JSON export/import round-trip ----------------------------------------------

def test_json_round_trip_preserves_spec():
    spec = _spec()
    restored = import_json(export_json(spec))
    assert restored.to_dict() == spec.to_dict()


def test_import_rejects_garbage():
    with pytest.raises(ValueError, match="valid portfolio"):
        import_json('{"foo": 1}')


def test_orm_to_spec_round_trip(repo):
    user = repo.create_user("alice", "h")
    spec = _spec()
    p = repo.save_portfolio(user.id, spec)
    assert orm_to_spec(p).to_dict() == spec.to_dict()
