"""Session-scoped fixtures for the E2E suite.

Both the FastAPI backend and the Next.js frontend are started once per
pytest session and torn down automatically.  If a server is already running
on the expected port (e.g. during local development), it is reused rather
than restarted.
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Iterator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[3]          # project root
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_UVICORN = BACKEND_DIR / "venv" / "bin" / "uvicorn"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_serving(url: str, timeout: float = 2.0) -> bool:
    """Return True if the URL responds with HTTP 2xx."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 300
    except Exception:
        return False


def _wait_for(url: str, retries: int = 40, interval: float = 1.5) -> None:
    """Block until the URL is serving or raise TimeoutError."""
    for _ in range(retries):
        if _is_serving(url):
            return
        time.sleep(interval)
    raise TimeoutError(f"Server at {url} did not become ready in time")


# ── Server fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def backend_server() -> Iterator[str]:
    if _is_serving(f"{BACKEND_URL}/health"):
        yield BACKEND_URL
        return

    proc = subprocess.Popen(
        [str(VENV_UVICORN), "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for(f"{BACKEND_URL}/health")
        yield BACKEND_URL
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def frontend_server(backend_server: str) -> Iterator[str]:
    if _is_serving(FRONTEND_URL):
        yield FRONTEND_URL
        return

    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for(FRONTEND_URL, retries=60, interval=2.0)
        yield FRONTEND_URL
    finally:
        proc.terminate()
        proc.wait(timeout=10)


# ── Playwright fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Iterator[Browser]:
    b = playwright_instance.chromium.launch(headless=True)
    yield b
    b.close()


@pytest.fixture
def context(browser: Browser) -> Iterator[BrowserContext]:
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext, frontend_server: str) -> Iterator[Page]:
    p = context.new_page()
    p.goto(frontend_server, wait_until="domcontentloaded", timeout=30_000)
    p.wait_for_load_state("networkidle", timeout=30_000)
    yield p
    p.close()
