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
import os
from functools import lru_cache

import httpx

log = logging.getLogger(__name__)

_EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT", "financial-agent/1.0 benbenben12322@gmail.com"
)
_EDGAR_HEADERS = {
    "User-Agent": _EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_FILING_BASE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"
_MAX_TEXT_CHARS = 5_000_000  # 5 M char cap — sufficient for Risk Factors + MD&A


class FilingNotFoundError(Exception):
    """Raised when EDGAR has no 10-K/10-Q for a given ticker."""


class FilingFetchError(Exception):
    """Raised when an EDGAR HTTP fetch fails (timeout, bad status, etc.)."""


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
    """Return (raw_text, form_type, filing_date) for the most recently filed 10-K or 10-Q.

    Raises FilingNotFoundError if the ticker is unknown or has no 10-K/10-Q.
    Raises FilingFetchError on network/HTTP errors when downloading the document.
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

    for form, acc, doc, date_ in zip(forms, accessions, primary_docs, filing_dates):
        if form not in ("10-K", "10-Q"):
            continue
        acc_nodash = acc.replace("-", "")
        doc_url = _FILING_BASE.format(cik=cik, acc_nodash=acc_nodash, doc=doc)
        log.info("edgar: downloading %s %s from %s", form, date_, doc_url)
        try:
            doc_resp = httpx.get(doc_url, headers=_EDGAR_HEADERS, timeout=60, follow_redirects=True)
            doc_resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FilingFetchError(f"Timeout fetching {doc_url}") from exc
        except httpx.HTTPStatusError as exc:
            raise FilingFetchError(
                f"HTTP {exc.response.status_code} fetching {doc_url}"
            ) from exc
        text = doc_resp.text[:_MAX_TEXT_CHARS]
        return text, form, date_

    raise FilingNotFoundError(
        f"No 10-K or 10-Q found in EDGAR for ticker {normalized!r}"
    )
