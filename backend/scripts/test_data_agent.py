"""Smoke test for the LangGraph Data Agent.

Run from the project root:
    backend/venv/bin/python backend/scripts/test_data_agent.py

Uses whichever `ALPHA_VANTAGE_API_KEY` is in `backend/.env` (or the public
`demo` key for IBM only). Repeated runs within a minute hit the cache.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.data_agent import run_data_agent  # noqa: E402
from app.services.alpha_vantage import DataFetchError  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Prevent the Alpha Vantage API key from leaking into stdout via httpx's
# default INFO-level URL logging (the key sits in the query string).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("test_data_agent")


def main() -> int:
    ticker = sys.argv[1] if len(sys.argv) > 1 else "IBM"
    log.info("Running Data Agent for %s ...", ticker)
    try:
        report = run_data_agent(ticker)
    except DataFetchError as exc:
        log.error("Data Agent failed: %s: %s", type(exc).__name__, exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error in Data Agent: %s", exc)
        return 2

    print()
    print(f"=== Data Agent report for {report.ticker} ===")
    print(f"  Name:         {report.overview.name}")
    print(f"  Sector:       {report.overview.sector} / {report.overview.industry}")
    print(f"  Price:        ${report.quote.price} "
          f"(change {report.quote.change_percent}% on {report.quote.latest_trading_day})")
    print(f"  Market cap:   {report.market_cap_billions}B")
    print(f"  52-week band: {report.overview.week_52_low} – {report.overview.week_52_high}")
    print(f"  In band?      {report.is_within_52_week_band}")
    print(f"  Fetched at:   {report.fetched_at.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
