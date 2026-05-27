"""Supabase client singleton.

Call get_supabase_client() wherever a Client instance is needed.
Always guard the call with settings.supabase_configured — this function
raises RuntimeError if the credentials are absent.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return the process-wide Supabase client (created once on first call)."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "Supabase is not configured. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
