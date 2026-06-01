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
_code_cache: dict[str, tuple[bool, int, float]] = {}  # code -> (is_valid, credits, expiry_monotonic)


def _validate_code(code: str) -> tuple[bool, int]:
    """Return (is_valid, credits) for the given code. Non-fatal on Supabase errors."""
    now = time.monotonic()
    with _cache_lock:
        entry = _code_cache.get(code)
        if entry is not None:
            is_valid, credits, expiry = entry
            if now < expiry:
                return is_valid, credits

    try:
        client = get_supabase_client()
        result = (
            client.table("master_codes")
            .select("is_active, credits")
            .eq("code", code)
            .execute()
        )
        if bool(result.data) and result.data[0]["is_active"] is True:
            is_valid = True
            credits = int(result.data[0].get("credits") or 3)
        else:
            is_valid = False
            credits = 0
    except Exception:
        log.exception("master_code_auth: Supabase lookup failed")
        return False, 0

    with _cache_lock:
        _code_cache[code] = (is_valid, credits, now + _CACHE_TTL_S)
    return is_valid, credits


def get_code_credits(code: str) -> int:
    """Return the credits for a code (assumes already validated). Cached."""
    _, credits = _validate_code(code)
    return credits


def require_master_code(
    x_master_code: str | None = Header(default=None, alias="X-Master-Code"),
) -> None:
    """FastAPI dependency: validates Master Code; raises 401/403 on failure.

    Header-only — accepts code from X-Master-Code request header. Plain def so
    FastAPI runs it in a thread-pool, avoiding event-loop stalls from the
    blocking Supabase call in _validate_code.
    """
    if not x_master_code:
        return  # Free-tier: frontend credits gate access; no header = allow through
    is_valid, _ = _validate_code(x_master_code)
    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail="Master Code is invalid or has been deactivated.",
        )
