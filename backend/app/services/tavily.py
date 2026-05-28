"""Tavily news-search service.

Posts to the Tavily REST API (api.tavily.com/search) via httpx. The API
key travels in the JSON body (not the URL), so it doesn't appear in
httpx URL logs even at INFO level — but the project-wide httpx logger
suppression in `app/main.py` is still in effect as defence-in-depth.

Returns Pydantic-validated `NewsSearchResult` on success; raises a typed
`NewsFetchError` subclass otherwise.

Tavily's free tier is documented at ~1,000 searches/month with no
per-second limit. We still apply a defensive 0.25s throttle to keep
bursty test loops well-behaved.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.models.news import NewsArticle, NewsSearchResult
from app.services.rate_limiter import MinIntervalRateLimiter

TAVILY_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_S = 15.0  # search calls are slower than quote fetches
MIN_REQUEST_INTERVAL_S = 0.25  # defensive; Tavily has no documented per-second cap

_rate_limiter = MinIntervalRateLimiter(MIN_REQUEST_INTERVAL_S)
log = logging.getLogger(__name__)


# --- Exception hierarchy -----------------------------------------------------

class NewsFetchError(Exception):
    """Base class for Tavily search failures."""


class NewsTimeoutError(NewsFetchError):
    """Upstream request exceeded the timeout budget."""


class NewsHTTPError(NewsFetchError):
    """Non-2xx HTTP response from Tavily."""

    def __init__(self, status_code: int, body_preview: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {body_preview!r}")


class NewsRateLimitedError(NewsFetchError):
    """Tavily indicated a quota / rate-limit response."""


class MalformedNewsResponseError(NewsFetchError):
    """Response was not valid JSON or failed Pydantic validation."""


class MissingNewsAPIKey(NewsFetchError):
    """No `TAVILY_API_KEY` is configured."""


# --- Public API --------------------------------------------------------------

def search(
    query: str,
    *,
    max_results: int = 5,
    search_depth: str = "basic",
    days: int | None = None,
) -> NewsSearchResult:
    """Run a Tavily search.

    `search_depth` is either "basic" (cheaper) or "advanced". `max_results`
    is clamped 1..20. `days` limits results to the last N days (None = no filter).
    """
    api_key = get_settings().tavily_api_key
    if not api_key:
        raise MissingNewsAPIKey("TAVILY_API_KEY is not set in backend/.env")

    if not query.strip():
        raise ValueError("query must be non-empty")
    bounded_max = max(1, min(20, int(max_results)))

    body = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": bounded_max,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }

    if days is not None:
        body["days"] = max(1, int(days))

    _rate_limiter.wait()
    payload = _post(body)

    raw_results = payload.get("results") or []
    if not isinstance(raw_results, list):
        raise MalformedNewsResponseError(
            f"Expected 'results' to be a list, got {type(raw_results).__name__}"
        )

    articles: list[NewsArticle] = []
    for raw in raw_results:
        try:
            articles.append(NewsArticle.model_validate(raw))
        except ValidationError as exc:
            log.warning("Dropping malformed news article: %s", exc)
            continue

    return NewsSearchResult(query=query, articles=articles)


# --- Internals ---------------------------------------------------------------

def _post(body: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(TAVILY_URL, json=body, timeout=REQUEST_TIMEOUT_S)
    except httpx.TimeoutException as exc:
        raise NewsTimeoutError(
            f"Tavily timed out after {REQUEST_TIMEOUT_S}s"
        ) from exc
    except httpx.RequestError as exc:
        raise NewsFetchError(f"Network error contacting Tavily: {exc}") from exc

    if response.status_code == 429:
        raise NewsRateLimitedError(response.text[:200])
    if response.status_code >= 400:
        raise NewsHTTPError(response.status_code, response.text[:200])

    try:
        payload = response.json()
    except ValueError as exc:
        raise MalformedNewsResponseError(f"Non-JSON response: {exc}") from exc

    if not isinstance(payload, dict):
        raise MalformedNewsResponseError(
            f"Expected JSON object, got {type(payload).__name__}"
        )
    return payload
