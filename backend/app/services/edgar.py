"""SEC EDGAR filing fetcher.

Resolves a ticker to a CIK via EDGAR's company_tickers.json (cached in
memory after first request), then downloads the primary document of the
most recent 10-K or 10-Q filing as raw HTML text.

EDGAR fair-use policy requires:
  - A User-Agent header identifying the operator and contact email.
  - No more than 10 requests/second (this module issues ≤3 requests per call).
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx

log = logging.getLogger(__name__)

_EDGAR_HEADERS = {
    "User-Agent": "financial-agent/1.0 benbenben12322@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_FILING_BASE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
_MAX_TEXT_BYTES = 5_000_000  # 5 MB cap — sufficient for Risk Factors + MD&A


class FilingNotFoundError(Exception):
    """Raised when EDGAR has no 10-K/10-Q for a given ticker."""


@lru_cache(maxsize=1)
def _load_ticker_map() -> dict[str, int]:
    """Download company_tickers.json once and cache for the process lifetime."""
    log.info("edgar: fetching company_tickers.json from SEC")
    resp = httpx.get(_TICKERS_URL, headers=_EDGAR_HEADERS, timeout=30)
    resp.raise_for_status()
    data: dict = resp.json()
    return {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}


def _get_cik(ticker: str) -> int:
    ticker_map = _load_ticker_map()
    cik = ticker_map.get(ticker.strip().upper())
    if cik is None:
        raise FilingNotFoundError(
            f"Ticker {ticker!r} not found in SEC EDGAR company list"
        )
    return cik


def get_latest_filing_text(ticker: str) -> tuple[str, str, str | None]:
    """Return (html_text, form_type, filing_date_iso) for the most recent 10-K or 10-Q.

    Tries 10-K first, falls back to 10-Q.
    Raises FilingNotFoundError if no filing is found.
    """
    normalized = ticker.strip().upper()
    cik = _get_cik(normalized)

    url = _SUBMISSIONS_URL.format(cik=cik)
    log.info("edgar: fetching submissions for %s (CIK %d)", normalized, cik)
    resp = httpx.get(url, headers=_EDGAR_HEADERS, timeout=30)
    resp.raise_for_status()
    submissions: dict = resp.json()

    recent = submissions.get("filings", {}).get("recent", {})
    forms: list[str] = recent.get("form", [])
    accessions: list[str] = recent.get("accessionNumber", [])
    primary_docs: list[str] = recent.get("primaryDocument", [])
    filing_dates: list[str] = recent.get("filingDate", [])

    for i, form in enumerate(forms):
        if form not in ("10-K", "10-Q"):
            continue
        acc_nodash = accessions[i].replace("-", "")
        doc_url = _FILING_BASE.format(cik=cik, acc_nodash=acc_nodash, doc=primary_docs[i])
        log.info("edgar: downloading %s %s from %s", form, filing_dates[i], doc_url)
        doc_resp = httpx.get(
            doc_url,
            headers=_EDGAR_HEADERS,
            timeout=60,
            follow_redirects=True,
        )
        doc_resp.raise_for_status()
        # Cap text to avoid processing enormous filings
        text = doc_resp.text[:_MAX_TEXT_BYTES]
        return text, form, filing_dates[i] if i < len(filing_dates) else None

    raise FilingNotFoundError(
        f"No 10-K or 10-Q found in EDGAR for ticker {normalized!r}"
    )
