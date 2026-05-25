"""Smoke-test caller for the Alpha Vantage service.

Run from the project root:
    backend/venv/bin/python backend/scripts/test_fetch.py

Without `ALPHA_VANTAGE_API_KEY` in `backend/.env` the service falls back
to the public `demo` key (IBM only).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable

# Make `backend/` importable when this file is executed as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.alpha_vantage import (  # noqa: E402
    DataFetchError,
    fetch_company_overview,
    fetch_global_quote,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Prevent the Alpha Vantage API key from leaking into stdout via httpx's
# default INFO-level URL logging (the key sits in the query string).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("test_fetch")


def _try(label: str, fn: Callable[..., Any], *args: Any) -> Any | None:
    try:
        result = fn(*args)
    except DataFetchError as exc:
        log.error("[%s] %s: %s", label, type(exc).__name__, exc)
        return None
    log.info("[%s] ok", label)
    return result


def main() -> int:
    # Happy path: IBM works with both real and demo keys.
    ibm_quote = _try("IBM quote", fetch_global_quote, "IBM")
    ibm_overview = _try("IBM overview", fetch_company_overview, "IBM")
    if ibm_quote is not None:
        print(
            f"\nIBM price: {ibm_quote.price} "
            f"(change {ibm_quote.change_percent}%) on {ibm_quote.latest_trading_day}"
        )
    if ibm_overview is not None:
        print(
            f"IBM: {ibm_overview.name} — {ibm_overview.sector} / {ibm_overview.industry}\n"
            f"  Market cap: {ibm_overview.market_capitalization}, P/E: {ibm_overview.pe_ratio}"
        )
    happy_ok = ibm_quote is not None and ibm_overview is not None

    # Resilience path: a fake ticker must fail typed-and-graceful, not crash.
    log.info("Probing fake ticker ZZZFAKE (expect graceful failure)...")
    bogus_quote = _try("ZZZFAKE quote", fetch_global_quote, "ZZZFAKE")
    bogus_overview = _try("ZZZFAKE overview", fetch_company_overview, "ZZZFAKE")
    resilience_ok = bogus_quote is None and bogus_overview is None

    print("\n=== Summary ===")
    print(f"  Happy path (IBM):       {'PASS' if happy_ok else 'FAIL'}")
    print(f"  Resilience (ZZZFAKE):   {'PASS' if resilience_ok else 'FAIL'}")
    return 0 if (happy_ok and resilience_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
