"""Persistent report cache backed by Supabase.

store_report()      — persists a FinalReport as JSONB in the `reports` table.
get_cached_report() — returns a FinalReport from cache if within TTL, else None.

All errors are non-fatal. If Supabase is unreachable or not configured,
these functions return / no-op so the pipeline degrades to an uncached run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.models.manager import FinalReport
from app.services.supabase_client import get_supabase_client

log = logging.getLogger(__name__)


def store_report(report: FinalReport) -> None:
    """Persist a FinalReport to Supabase. Non-fatal on any error."""
    settings = get_settings()
    if not settings.supabase_configured:
        return
    try:
        client = get_supabase_client()
        client.table("reports").insert(
            {
                "ticker": report.ticker,
                "report_json": report.model_dump(mode="json"),
                "generated_at": report.generated_at.isoformat(),
            }
        ).execute()
        log.info("report_cache: stored report for %s", report.ticker)
    except Exception as exc:  # noqa: BLE001
        log.warning("report_cache: store failed for %s: %s", report.ticker, exc)


def get_cached_report(ticker: str) -> FinalReport | None:
    """Return a cached FinalReport within the configured TTL, or None.

    Returns None when:
    - Supabase is not configured
    - No report exists within the TTL window
    - Any network or deserialization error occurs
    """
    settings = get_settings()
    if not settings.supabase_configured:
        return None
    try:
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=settings.report_cache_ttl_hours)
        ).isoformat()
        client = get_supabase_client()
        result = (
            client.table("reports")
            .select("report_json", "generated_at")
            .eq("ticker", ticker.upper())
            .gte("generated_at", cutoff)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return FinalReport.model_validate(result.data[0]["report_json"])
    except Exception as exc:  # noqa: BLE001
        log.warning("report_cache: get failed for %s: %s", ticker, exc)
        return None
