"""FastAPI entry point for the Multi-Agent Financial System."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routers import analyze as analyze_router
from app.routers import quote as quote_router
from app.services.limiter import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# httpx logs full request URLs (incl. query params) at INFO, which would leak
# `apikey=...` for Alpha Vantage. Silence it; we surface upstream errors via
# our own typed exceptions / structured logs instead.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("Startup: env=%s alpha_vantage_configured=%s",
             settings.env, settings.alpha_vantage_configured)
    yield
    log.info("Shutdown.")


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded — {exc.detail}. Please wait before retrying."},
        headers={"Retry-After": "60"},
    )


app = FastAPI(
    title="Multi-Agent Financial System",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    env: str
    alpha_vantage_configured: bool


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        env=settings.env,
        alpha_vantage_configured=settings.alpha_vantage_configured,
    )


app.include_router(quote_router.router)
app.include_router(analyze_router.router)
