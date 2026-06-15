"""Auth endpoints: signup, login, and the current-user lookup.

Reuses ``storage.auth_service.AuthService`` for hashing/verification — the API only
turns its results into JWTs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, get_repository
from api.schemas import Credentials, Token, UserOut
from api.security import create_access_token
from storage.auth_service import AuthError, AuthService
from storage.models import User
from storage.repository import Repository

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=Token)
def signup(body: Credentials, repo: Repository = Depends(get_repository)) -> Token:
    service = AuthService(repo)
    try:
        user = service.sign_up(body.username, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    repo.session.flush()
    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
def login(body: Credentials, repo: Repository = Depends(get_repository)) -> Token:
    user = AuthService(repo).authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, username=user.username)
