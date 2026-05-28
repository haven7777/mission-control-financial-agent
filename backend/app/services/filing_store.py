"""Supabase pgvector store for SEC filing chunks.

chunks_exist()  — True if this ticker has fresh chunks (< 30 days old).
store_chunks()  — Upsert text chunks + embeddings for one section.
search_chunks() — Semantic similarity search via match_filing_chunks RPC.

All functions are no-ops / return empty when Supabase is not configured.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.services.supabase_client import get_supabase_client

log = logging.getLogger(__name__)

_CACHE_TTL_DAYS = 30


def chunks_exist(ticker: str) -> bool:
    """True if the filing_chunks table has rows for ticker within the TTL."""
    settings = get_settings()
    if not settings.supabase_configured:
        return False
    try:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=_CACHE_TTL_DAYS)
        ).isoformat()
        result = (
            get_supabase_client()
            .table("filing_chunks")
            .select("id")
            .eq("ticker", ticker.upper())
            .gte("fetched_at", cutoff)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as exc:  # noqa: BLE001
        log.warning("filing_store: chunks_exist check failed for %s: %s", ticker, exc)
        return False


def store_chunks(
    ticker: str,
    form_type: str,
    filing_date: str | None,
    section: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    """Insert text chunks + embeddings into filing_chunks. Non-fatal on error."""
    settings = get_settings()
    if not settings.supabase_configured or not chunks:
        return
    if len(chunks) != len(embeddings):
        log.warning("filing_store: chunks/embeddings length mismatch for %s/%s (%d vs %d), skipping", ticker, section, len(chunks), len(embeddings))
        return
    try:
        rows = [
            {
                "ticker": ticker.upper(),
                "form_type": form_type,
                "section": section,
                "chunk_index": i,
                "content": chunk,
                "embedding": emb,
                "filing_date": filing_date,
            }
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
        ]
        get_supabase_client().table("filing_chunks").insert(rows).execute()
        log.info(
            "filing_store: stored %d chunks (%s/%s) for %s",
            len(rows), form_type, section, ticker,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("filing_store: store_chunks failed for %s/%s: %s", ticker, section, exc)


def search_chunks(
    ticker: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Return top-k chunks by cosine similarity via the match_filing_chunks RPC.

    Each row is {'section': str, 'content': str, 'form_type': str, 'filing_date': str, 'similarity': float}.
    Returns [] when Supabase is unconfigured or on any error.
    """
    settings = get_settings()
    if not settings.supabase_configured:
        return []
    try:
        result = get_supabase_client().rpc(
            "match_filing_chunks",
            {
                "p_ticker": ticker.upper(),
                "p_embedding": query_embedding,
                "p_top_k": top_k,
            },
        ).execute()
        return result.data or []
    except Exception as exc:  # noqa: BLE001
        log.warning("filing_store: search_chunks failed for %s: %s", ticker, exc)
        return []
