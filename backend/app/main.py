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
from app.services.tracing import configure_langsmith_tracing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.WARNING)
log = logging.getLogger("app")

settings = get_settings()
_tracing_enabled = configure_langsmith_tracing()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info(
        "Startup: env=%s market_data=yfinance langsmith_tracing=%s",
        settings.env,
        _tracing_enabled,
    )
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
    market_data_source: str
    langsmith_tracing: bool


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        env=settings.env,
        market_data_source="yfinance",
        langsmith_tracing=_tracing_enabled,
    )


app.include_router(quote_router.router)
app.include_router(analyze_router.router)
