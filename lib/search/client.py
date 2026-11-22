import logging
import os
from pathlib import Path

import httpx
import yaml

from lib.schemas import SearchResult
from lib.search.google_cse import search_google_cse
from lib.search.serpapi import search_serpapi
from lib.search.tavily import search_tavily

PROVIDERS = {
    "tavily": search_tavily,
    "serpapi": search_serpapi,
    "google_cse": search_google_cse,
}

DEFAULT_FALLBACK_ORDER = ["tavily", "serpapi", "google_cse"]

log = logging.getLogger(__name__)


def get_fallback_order() -> list[str]:
    raw = os.getenv("SEARCH_FALLBACK_ORDER", ",".join(DEFAULT_FALLBACK_ORDER))
    return [p.strip() for p in raw.split(",") if p.strip()]


def search(
    query: str,
    provider: str | None = None,
    max_results: int = 5,
    exclude_domains: list[str] | None = None,
    time_range: str | None = None,
) -> list[SearchResult]:
    if provider:
        fn = PROVIDERS.get(provider)
        if fn is None:
            raise ValueError(f"Unknown search provider: {provider}")
        return fn(query, max_results=max_results, exclude_domains=exclude_domains, time_range=time_range)

    # Fallback chain: a provider that errors (rate limit, outage, bad key) or
    # returns nothing hands off to the next one instead of failing the whole
    # agent run — previously one HTTP 429 from Tavily aborted the nightly scan.
    for name in get_fallback_order():
        fn = PROVIDERS.get(name)
        if fn is None:
            log.warning("unknown search provider in SEARCH_FALLBACK_ORDER", extra={"provider": name})
            continue
        try:
            results = fn(
                query, max_results=max_results, exclude_domains=exclude_domains, time_range=time_range
            )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning(
                "search provider failed; falling back",
                extra={"provider": name, "error": type(exc).__name__, "query": query[:80]},
            )
            continue
        if results:
            return results
    return []


def load_queries(path: Path, merge_path: Path | None = None) -> list[str]:
    if not path.exists():
        queries: list[str] = []
    else:
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        queries = data.get("queries", [])

    if merge_path is not None and merge_path.exists():
        with merge_path.open() as f:
            extra = yaml.safe_load(f) or {}
        queries.extend(extra.get("queries", []))
    return queries
