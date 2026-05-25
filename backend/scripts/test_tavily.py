"""Smoke test for the Tavily news service.

Run from the project root:
    backend/venv/bin/python backend/scripts/test_tavily.py [QUERY]

Default query is "IBM stock news today".
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tavily import (  # noqa: E402
    MissingNewsAPIKey,
    NewsFetchError,
    search,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Tavily auth lives in the request body, but the project-wide convention
# is to keep httpx logs quiet so we never surprise-leak any URL params.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("test_tavily")


def main() -> int:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "IBM stock news today"
    log.info("Querying Tavily: %r", query)
    try:
        result = search(query, max_results=5)
    except MissingNewsAPIKey as exc:
        log.error("Missing key: %s", exc)
        return 2
    except NewsFetchError as exc:
        log.error("Tavily fetch failed: %s: %s", type(exc).__name__, exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error: %s", exc)
        return 3

    print()
    print(f"=== Tavily results for {result.query!r} ({len(result.articles)} articles) ===")
    for i, article in enumerate(result.articles, start=1):
        score = f"{article.score:.2f}" if article.score is not None else "—"
        published = article.published_date.isoformat() if article.published_date else "—"
        print(f"\n[{i}] {article.title}")
        print(f"    score={score}  published={published}")
        print(f"    {article.url}")
        snippet = article.content.strip().replace("\n", " ")
        if len(snippet) > 180:
            snippet = snippet[:177] + "..."
        print(f"    {snippet}")
    return 0 if result.articles else 1


if __name__ == "__main__":
    sys.exit(main())
