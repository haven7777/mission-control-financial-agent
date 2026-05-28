"""Filings RAG Agent — fetch, embed, and retrieve SEC 10-K context.

Workflow:
  1. If filing_chunks already has rows for this ticker within 30 days,
     skip EDGAR fetch (cache hit path).
  2. Otherwise: fetch latest 10-K from EDGAR → parse sections → embed
     chunks → store in Supabase.
  3. Embed a fixed analysis query and run semantic search over the stored
     chunks to return the top-5 most relevant excerpts.

Returns an empty FilingsContext (is_empty=True) when:
  - Supabase is not configured
  - EDGAR has no filing for the ticker
  - Any unhandled error (never raises)
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.models.filings import FilingChunk, FilingsContext
from app.services.edgar import FilingFetchError, FilingNotFoundError, get_latest_filing_text
from app.services.embeddings import embed_batch
from app.services.filing_parser import chunk_text, extract_sections
from app.services.filing_store import chunks_exist, search_chunks, store_chunks

log = logging.getLogger(__name__)

_SEARCH_QUERY = (
    "main business risks competitive threats revenue growth drivers "
    "financial performance earnings outlook management guidance"
)


def run_filings_agent(ticker: str) -> FilingsContext:
    """Return the top-5 SEC filing excerpts for ticker.

    Never raises — returns is_empty=True on any failure.
    """
    normalized = ticker.strip().upper()
    settings = get_settings()

    if not settings.supabase_configured or not settings.openai_api_key:
        log.info("filings_agent: skipping %s — Supabase or OpenAI not configured", normalized)
        return FilingsContext(ticker=normalized, form_type="10-K", chunks=[], is_empty=True)

    form_type = "10-K"
    filing_date: str | None = None

    try:
        if not chunks_exist(normalized):
            log.info("filings_agent: no cached chunks for %s — fetching from EDGAR", normalized)
            html, form_type, filing_date = get_latest_filing_text(normalized)
            sections = extract_sections(html)

            for section_name, section_text in sections.items():
                if not section_text:
                    log.info("filings_agent: section %r not found for %s", section_name, normalized)
                    continue
                chunks = chunk_text(section_text)
                if not chunks:
                    continue
                embeddings = embed_batch(chunks)
                store_chunks(
                    ticker=normalized,
                    form_type=form_type,
                    filing_date=filing_date,
                    section=section_name,
                    chunks=chunks,
                    embeddings=embeddings,
                )
                log.info(
                    "filings_agent: stored %d chunks for %s/%s",
                    len(chunks), normalized, section_name,
                )
        else:
            log.info("filings_agent: using cached chunks for %s", normalized)

        query_embedding = embed_batch([_SEARCH_QUERY])[0]
        raw_chunks = search_chunks(normalized, query_embedding, top_k=5)

        if not raw_chunks:
            return FilingsContext(ticker=normalized, form_type=form_type, chunks=[], is_empty=True)

        # Update form_type from stored data (may be 10-Q on cache-hit path)
        form_type = raw_chunks[0].get("form_type", form_type)

        return FilingsContext(
            ticker=normalized,
            form_type=form_type,
            chunks=[
                FilingChunk(
                    section=r["section"],
                    content=r["content"],
                    similarity=max(0.0, min(1.0, float(r["similarity"]))),
                )
                for r in raw_chunks
            ],
        )

    except FilingNotFoundError as exc:
        log.info("filings_agent: no EDGAR filing for %s: %s", normalized, exc)
        return FilingsContext(ticker=normalized, form_type=form_type, chunks=[], is_empty=True)
    except FilingFetchError as exc:
        log.warning("filings_agent: EDGAR fetch failed for %s: %s", normalized, exc)
        return FilingsContext(ticker=normalized, form_type=form_type, chunks=[], is_empty=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("filings_agent: unexpected error for %s: %s", normalized, exc)
        return FilingsContext(ticker=normalized, form_type=form_type, chunks=[], is_empty=True)
