"""FastAPI entry point for the Multi-Agent Financial System."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.routers import quote as quote_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("Startup: env=%s alpha_vantage_configured=%s",
             settings.env, settings.alpha_vantage_configured)
    yield
    log.info("Shutdown.")


app = FastAPI(
    title="Multi-Agent Financial System",
    version="0.1.0",
    lifespan=lifespan,
)

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
