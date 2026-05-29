"""FastAPI entry point for the Multi-Agent Financial System."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from asgi_correlation_id import CorrelationIdFilter, CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routers import analyze as analyze_router
from app.routers import auth as auth_router
from app.routers import export as export_router
from app.routers import quote as quote_router
from app.services.limiter import limiter
from app.services.tracing import configure_langsmith_tracing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s",
)
# Wire correlation-id filter onto every root handler so %(correlation_id)s
# resolves on every log record (including those emitted from background
# threads, where the contextvar may not be set — default '-' covers that).
for _handler in logging.getLogger().handlers:
    _handler.addFilter(CorrelationIdFilter(uuid_length=12, default_value="-"))
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.WARNING)
log = logging.getLogger("app")

settings = get_settings()
_tracing_enabled = configure_langsmith_tracing()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info(
        "Startup: env=%s market_data=yfinance langsmith_tracing=%s supabase_cache=%s",
        settings.env,
        _tracing_enabled,
        settings.supabase_configured,
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

# Correlation-ID middleware must be registered BEFORE CORS so the request-id
# header survives the CORS preflight / response chain. Middlewares are applied
# in reverse-registration order, so CORS wraps CorrelationId (outer → inner).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(CorrelationIdMiddleware)


class HealthResponse(BaseModel):
    status: str
    env: str
    market_data_source: str
    langsmith_tracing: bool
    supabase_cache: bool


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        env=settings.env,
        market_data_source="yfinance",
        langsmith_tracing=_tracing_enabled,
        supabase_cache=settings.supabase_configured,
    )


app.include_router(quote_router.router)
app.include_router(analyze_router.router)
app.include_router(auth_router.router)
app.include_router(export_router.router)
