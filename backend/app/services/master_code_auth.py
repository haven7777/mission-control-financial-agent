"""FastAPI dependency for Master Code authentication.

Reads the code from the X-Master-Code request header only. SSE clients use a
fetch-based EventSource (e.g., @microsoft/fetch-event-source) to set the
header — query-param fallback was removed per the security audit (codes
were leaking into nginx access logs and proxy caches).

Validates against the Supabase `master_codes` table. Results are cached
in-memory for 5 minutes (CACHE_TTL_S) to avoid a Supabase round-trip on
every connection.
"""

from __future__ import annotations

import logging
import threading
import time

from fastapi import Header, HTTPException

from app.services.supabase_client import get_supabase_client

log = logging.getLogger(__name__)

_CACHE_TTL_S: float = 300.0  # 5 minutes
_cache_lock = threading.Lock()
_code_cache: dict[str, tuple[bool, float]] = {}  # code -> (is_valid, expiry_monotonic)


def _validate_code(code: str) -> bool:
    """Return True iff the code exists and is_active in master_codes. Non-fatal."""
    now = time.monotonic()
    with _cache_lock:
        entry = _code_cache.get(code)
        if entry is not None:
            is_valid, expiry = entry
            if now < expiry:
                return is_valid

    try:
        client = get_supabase_client()
        result = (
            client.table("master_codes")
            .select("is_active")
            .eq("code", code)
            .execute()
        )
        is_valid = bool(result.data) and result.data[0]["is_active"] is True
    except Exception:
        log.exception("master_code_auth: Supabase lookup failed")
        return False

    with _cache_lock:
        _code_cache[code] = (is_valid, now + _CACHE_TTL_S)
    return is_valid


def require_master_code(
    x_master_code: str | None = Header(default=None, alias="X-Master-Code"),
) -> None:
    """FastAPI dependency: validates Master Code; raises 401/403 on failure.

    Header-only — accepts code from X-Master-Code request header. Plain def so
    FastAPI runs it in a thread-pool, avoiding event-loop stalls from the
    blocking Supabase call in _validate_code.
    """
    if not x_master_code:
        raise HTTPException(
            status_code=401,
            detail="Deep Research requires a Master Code (X-Master-Code header).",
        )
    if not _validate_code(x_master_code):
        raise HTTPException(
            status_code=403,
            detail="Master Code is invalid or has been deactivated.",
        )
