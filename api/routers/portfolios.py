"""Portfolio CRUD + the ticker universe — all scoped to the token's user.

Per-user isolation is enforced by ``Repository`` (every call passes ``user.id``); the
router never queries the ORM directly, so user A can never see/modify user B's data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_repository
from api.schemas import PortfolioOut, PortfolioSpecDTO, TickerOut
from data import tickers
from storage.models import User
from storage.portfolio_io import orm_to_spec
from storage.repository import Repository

router = APIRouter(prefix="/api", tags=["portfolios"])


@router.get("/tickers", response_model=list[TickerOut])
def list_tickers() -> list[TickerOut]:
    universe = tickers.load_universe()
    return [TickerOut(symbol=sym, name=name) for sym, name in universe.items()]


@router.get("/portfolios", response_model=list[PortfolioOut])
def list_portfolios(
    user: User = Depends(get_current_user), repo: Repository = Depends(get_repository)
) -> list[PortfolioOut]:
    out: list[PortfolioOut] = []
    for orm in repo.list_portfolios(user.id):
        dto = PortfolioSpecDTO.from_spec(orm_to_spec(orm))
        out.append(PortfolioOut(id=orm.id, **dto.model_dump()))
    return out


@router.post("/portfolios", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    body: PortfolioSpecDTO,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> PortfolioOut:
    orm = repo.save_portfolio(user.id, body.to_spec())
    repo.session.flush()
    dto = PortfolioSpecDTO.from_spec(orm_to_spec(orm))
    return PortfolioOut(id=orm.id, **dto.model_dump())


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(
    portfolio_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> PortfolioOut:
    orm = repo.get_portfolio(user.id, portfolio_id)
    if orm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    dto = PortfolioSpecDTO.from_spec(orm_to_spec(orm))
    return PortfolioOut(id=orm.id, **dto.model_dump())


@router.delete("/portfolios/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_repository),
) -> None:
    if not repo.delete_portfolio(user.id, portfolio_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
