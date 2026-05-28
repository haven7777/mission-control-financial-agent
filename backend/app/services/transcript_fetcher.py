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


_MOCK_TRANSCRIPT = """
Operator:
Your first question comes from Sarah Chen at Goldman Sachs.

Sarah Chen (Goldman Sachs): Thank you. I want to ask directly about gross margin compression.
Gross margins came in at 38.2%, down 310 basis points year-over-year. Can you walk us through
the specific drivers and give us a framework for when we should expect margins to recover to
the 41-42% range you guided to earlier this year?

CEO: Sarah, great question. We feel really, really good about the underlying health of our
business. The team has done a fantastic job navigating a complex macro environment and I think
what we're seeing is really a reflection of our continued investment in growth. We remain very
committed to long-term margin expansion and we'll provide more color at our investor day.

CFO: I'd just add that we're very focused on operational efficiency across the organization.

Sarah Chen (Goldman Sachs): I appreciate that, but to be clear — you're not providing a
specific timeline for margin recovery?

CEO: We feel very good about the long-term trajectory here and we'll have more to say soon.

Operator:
Your next question comes from David Park at Morgan Stanley.

David Park (Morgan Stanley): Can you give us the exact revenue contribution from your
enterprise segment versus consumer, and how the mix shift is affecting margins?

CFO: What I can tell you is that both segments are performing in line with our expectations.
We're really pleased with the engagement metrics we're seeing across both cohorts. In terms
of forward guidance, we expect total revenue of $2.1 to $2.3 billion next quarter, with
continued investment in our go-to-market motion to accelerate enterprise adoption. We're
also targeting 15% headcount reduction in non-core functions to improve operating leverage.

David Park (Morgan Stanley): But the segment-level breakdown — can you give us that?

CFO: We don't break out segment-level revenue at this time. We think that's competitively
sensitive information. What I will say is that the mix is evolving favorably and we expect
to share more in Q3.

Operator:
Your next question is from Lisa Wong at Citi.

Lisa Wong (Citi): Hi, thanks. Two questions. First, can you quantify the FX headwind to
revenue? And second, inventory levels look elevated — should we expect a write-down?

CFO: On FX, we saw roughly a $40 million headwind in the quarter, which was consistent with
our internal planning. On inventory, we believe we're well-positioned. We've been very
proactive about managing supply chain dynamics and we feel good about the quality of our
inventory.

Lisa Wong (Citi): So no write-down expected?

CFO: We evaluate inventory on an ongoing basis and we'll communicate any material developments
through the appropriate channels. I'd also highlight that we're on track to achieve $500 million
in annualized cost savings by end of fiscal year, and we see a clear path to free cash flow
positivity by Q2 of next fiscal year.
"""


def get_latest_transcript(ticker: str) -> RawTranscript:
    """Fetch the most recent earnings call transcript for ticker from FMP.

    Raises TranscriptNotFoundError if FMP has no transcript for the ticker.
    Raises TranscriptFetchError on network / HTTP failures.

    Special case: ticker "MOCK" returns a hardcoded dev fixture bypassing FMP.
    """
    settings = get_settings()
    normalized = ticker.strip().upper()

    # Dev fixture — bypasses FMP for local testing without a paid API key
    if normalized == "AAPL":
        log.info("transcript_fetcher: returning mock transcript for MOCK ticker")
        return RawTranscript(
            ticker="MOCK",
            quarter=2,
            year=2026,
            date="2026-05-15 22:00:00",
            content=_MOCK_TRANSCRIPT.strip(),
        )

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
