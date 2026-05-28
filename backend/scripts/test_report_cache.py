"""Smoke test for the Supabase reports table.

Inserts a dummy row, retrieves it, verifies the data, then deletes it.
Does NOT require running the full pipeline.

Run: cd /path/to/project && backend/venv/bin/python backend/scripts/test_report_cache.py
"""
import logging
import sys
from datetime import datetime, timezone

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    from app.config import get_settings
    from app.services.supabase_client import get_supabase_client

    settings = get_settings()
    if not settings.supabase_configured:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
        sys.exit(1)

    client = get_supabase_client()
    test_ticker = "_SMOKE_TEST_"
    now = datetime.now(timezone.utc).isoformat()

    # Cleanup any leftover rows from previous failed runs
    client.table("reports").delete().eq("ticker", test_ticker).execute()

    # Insert
    client.table("reports").insert({
        "ticker": test_ticker,
        "report_json": {"smoke": True, "ts": now},
        "generated_at": now,
    }).execute()
    log.info("INSERT ok")

    # Retrieve
    result = (
        client.table("reports")
        .select("report_json", "generated_at")
        .eq("ticker", test_ticker)
        .execute()
    )
    assert len(result.data) == 1, f"Expected 1 row, got {len(result.data)}"
    assert result.data[0]["report_json"]["smoke"] is True, "report_json mismatch"
    log.info("SELECT ok — report_json validated")

    # Cleanup
    client.table("reports").delete().eq("ticker", test_ticker).execute()
    log.info("DELETE ok")

    log.info("✓ reports table: INSERT + SELECT + DELETE PASS")


if __name__ == "__main__":
    main()
