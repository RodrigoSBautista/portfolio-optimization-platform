"""FastAPI application entrypoint.

Run with: ``uv run uvicorn api.main:app --port 8000``. CORS is open to the Vite dev
server (``http://localhost:5173``). Tables are created on startup for dev convenience;
Alembic owns real migrations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_session_factory
from api.routers import analysis, analytics, auth, compare_tracking, portfolios

ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Build the engine + create tables (dev convenience) before serving requests.
    get_session_factory()
    yield


app = FastAPI(title="Portfolio Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Auth is via Authorization: Bearer headers, not cookies — no credentials needed.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(portfolios.router)
app.include_router(analysis.router)
app.include_router(analytics.router)
app.include_router(compare_tracking.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Friendly pointer for anyone opening the API base URL in a browser."""
    return {
        "service": "Portfolio Platform API",
        "hint": "This is the backend. The web app runs on the Vite dev server "
        "(http://localhost:5173 — start it with `cd web && npm run dev`).",
        "docs": "/docs",
        "health": "/api/health",
    }
