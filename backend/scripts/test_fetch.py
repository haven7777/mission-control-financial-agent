"""Smoke test for Alpha Vantage data fetching.

Run from the project root:
    backend/venv/bin/python backend/scripts/test_fetch.py

If `ALPHA_VANTAGE_API_KEY` is not set in `backend/.env`, falls back to the
public `demo` key, which only returns real data for ticker `IBM`.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
REQUEST_TIMEOUT_S = 10.0
ERROR_ENVELOPE_KEYS = ("Note", "Information", "Error Message")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("test_fetch")


def _load_api_key() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    key = os.getenv("ALPHA_VANTAGE_API_KEY") or "demo"
    if key == "demo":
        log.warning("ALPHA_VANTAGE_API_KEY not set; using public 'demo' key (IBM only).")
    return key


def _fetch(params: dict[str, str]) -> dict[str, Any] | None:
    try:
        response = httpx.get(ALPHA_VANTAGE_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        response.raise_for_status()
    except httpx.TimeoutException:
        log.error("Request timed out after %.1fs (params=%s)", REQUEST_TIMEOUT_S, params)
        return None
    except httpx.HTTPStatusError as exc:
        log.error("HTTP %s from Alpha Vantage: %s", exc.response.status_code, exc)
        return None
    except httpx.RequestError as exc:
        log.error("Network error contacting Alpha Vantage: %s", exc)
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        log.error("Malformed JSON from Alpha Vantage: %s", exc)
        return None

    if not isinstance(payload, dict):
        log.error("Unexpected JSON shape (expected object, got %s)", type(payload).__name__)
        return None

    for key in ERROR_ENVELOPE_KEYS:
        if key in payload:
            log.error("Alpha Vantage returned %s envelope: %s", key, payload[key])
            return None

    return payload


def fetch_global_quote(ticker: str, api_key: str) -> dict[str, Any] | None:
    log.info("Fetching GLOBAL_QUOTE for %s ...", ticker)
    payload = _fetch({"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key})
    if payload is None:
        return None
    quote = payload.get("Global Quote")
    if not quote:
        log.warning("Empty Global Quote for %s (likely invalid ticker).", ticker)
        return None
    return quote


def fetch_company_overview(ticker: str, api_key: str) -> dict[str, Any] | None:
    log.info("Fetching OVERVIEW for %s ...", ticker)
    payload = _fetch({"function": "OVERVIEW", "symbol": ticker, "apikey": api_key})
    if payload is None:
        return None
    if not payload.get("Symbol"):
        log.warning("Empty OVERVIEW for %s (likely invalid ticker).", ticker)
        return None
    return payload


def _print_section(title: str, data: dict[str, Any] | None) -> None:
    print(f"\n=== {title} ===")
    if data is None:
        print("  (no data)")
        return
    # Trim long Description text on OVERVIEW for readability
    preview: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 120:
            preview[k] = v[:117] + "..."
        else:
            preview[k] = v
    print(json.dumps(preview, indent=2))


def main() -> int:
    api_key = _load_api_key()

    # 1. Happy path: IBM (works with demo key)
    quote = fetch_global_quote("IBM", api_key)
    overview = fetch_company_overview("IBM", api_key)
    _print_section("IBM — Global Quote", quote)
    _print_section("IBM — Company Overview", overview)
    happy_ok = quote is not None and overview is not None

    # 2. Resilience path: fake ticker should fail gracefully, not crash
    log.info("Probing fake ticker (expect graceful failure) ...")
    bogus_quote = fetch_global_quote("ZZZFAKE", api_key)
    bogus_overview = fetch_company_overview("ZZZFAKE", api_key)
    _print_section("ZZZFAKE — Global Quote", bogus_quote)
    _print_section("ZZZFAKE — Company Overview", bogus_overview)
    resilience_ok = bogus_quote is None and bogus_overview is None

    print("\n=== Summary ===")
    print(f"  Happy path (IBM):       {'PASS' if happy_ok else 'FAIL'}")
    print(f"  Resilience (ZZZFAKE):   {'PASS' if resilience_ok else 'FAIL'}")
    return 0 if (happy_ok and resilience_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
