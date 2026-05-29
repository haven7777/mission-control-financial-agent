"""Financial Modeling Prep (FMP) earnings call transcript fetcher.

Fetches the most recent earnings call transcript for a ticker via the FMP
REST API. Returns a RawTranscript dict with the full content and a helper
to extract the Q&A section (capped at 12 000 chars for LLM cost control).

FMP free tier: 250 API calls/day.
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

_FMP_BASE = "https://financialmodelingprep.com/api/v3"
_TIMEOUT = 30
_MAX_QA_CHARS = 12_000

# Patterns that mark the start of the Q&A section in a transcript
_QA_MARKERS = [
    r"questions?\s+and\s+answers?(?:\s+session)?",
    r"q\s*&\s*a(?:\s+session)?",
    r"question[\-\s]+and[\-\s]+answer(?:\s+session)?",
    r"we\s+will\s+now\s+(?:open|begin|take)\s+(?:for\s+)?(?:the\s+)?(?:floor\s+for\s+)?questions?",
    r"operator:\s+(?:.*?\s+)?(?:first|your\s+first)\s+question",
    r"turn\s+(?:it\s+)?(?:back\s+)?(?:over\s+)?(?:to\s+the\s+)?(?:for\s+)?questions?",
]


class TranscriptNotFoundError(Exception):
    """Raised when FMP has no transcript for the given ticker."""


class TranscriptFetchError(Exception):
    """Raised on network or HTTP errors when calling FMP."""


class RawTranscript(TypedDict):
    ticker: str
    quarter: int
    year: int
    date: str | None
    content: str


def get_latest_transcript(ticker: str) -> RawTranscript:
    """Fetch the most recent earnings call transcript for ticker from FMP.

    Raises TranscriptNotFoundError if FMP has no transcript for the ticker.
    Raises TranscriptFetchError on network / HTTP failures.
    """
    settings = get_settings()
    normalized = ticker.strip().upper()

    api_key = settings.fmp_api_key

    if not api_key:
        raise TranscriptNotFoundError(
            f"FMP_API_KEY not configured — cannot fetch transcript for {normalized!r}"
        )

    url = f"{_FMP_BASE}/earning_call_transcript/{normalized}"
    log.info("transcript_fetcher: fetching transcript for %s", normalized)

    try:
        resp = httpx.get(
            url,
            params={"apikey": api_key},
            headers={"User-Agent": "financial-agent/1.0"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TranscriptFetchError(
            f"HTTP {exc.response.status_code} from FMP for {normalized}"
        ) from exc
    except httpx.RequestError as exc:
        raise TranscriptFetchError(
            f"Network error fetching FMP transcript for {normalized}: {type(exc).__name__}"
        ) from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise TranscriptFetchError(
            f"FMP returned non-JSON response for {normalized}"
        ) from exc

    # FMP returns [] for unknown tickers, or a dict with "Error Message" on auth failures
    if isinstance(data, dict):
        msg = data.get("Error Message") or data.get("message") or str(data)
        raise TranscriptNotFoundError(f"FMP error for {normalized!r}: {msg}")

    if not data:
        raise TranscriptNotFoundError(f"No transcript found for {normalized!r}")

    entry = data[0]  # Most recent transcript (FMP returns newest first)
    if not isinstance(entry, dict):
        raise TranscriptNotFoundError(f"Unexpected FMP response format for {normalized!r}")
    content = entry.get("content", "")
    if not content:
        raise TranscriptNotFoundError(f"Empty transcript content for {normalized!r}")

    return RawTranscript(
        ticker=normalized,
        quarter=int(entry.get("quarter", 0)),
        year=int(entry.get("year", 0)),
        date=str(entry.get("date", "")).strip() or None,
        content=content,
    )


def extract_qa_section(content: str) -> str:
    """Extract and return the Q&A portion of a transcript, capped at _MAX_QA_CHARS.

    Searches for common Q&A section headers. Falls back to the last 40% of
    the transcript if no marker is found (Q&A is always at the end).
    """
    content_lower = content.lower()

    for pattern in _QA_MARKERS:
        m = re.search(pattern, content_lower)
        if m:
            qa_text = content[m.start():]
            return qa_text[:_MAX_QA_CHARS]

    # Fallback: last 40% of transcript — Q&A always appears after prepared remarks
    start = max(0, int(len(content) * 0.6))
    return content[start : start + _MAX_QA_CHARS]
